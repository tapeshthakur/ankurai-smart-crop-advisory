from __future__ import annotations

import logging
from typing import Any, Dict

import pandas as pd
from database.db import insert_prediction
from config import settings
from models import model_loader
from utils.preprocessor import (
    PreprocessingError,
    enforce_feature_order,
    validate_and_cast_types,
    validate_ranges,
)


classifier_model = model_loader.load_latest_classifier()
regressor_model = model_loader.load_latest_regressor()
logger = logging.getLogger(__name__)


def _to_dataframe(input_data: Dict[str, Any]) -> pd.DataFrame:
    """Convert dictionary input into a one-row DataFrame."""
    if not isinstance(input_data, dict):
        raise TypeError("input_data must be a dictionary")
    if not input_data:
        raise ValueError("input_data cannot be empty")
    return pd.DataFrame([input_data])


def _align_features(df: pd.DataFrame, model: Any) -> pd.DataFrame:
    """Align features to model training order when available."""
    feature_names = getattr(model, "feature_names_in_", None)
    if feature_names is None:
        return df

    missing = [name for name in feature_names if name not in df.columns]
    if missing:
        raise ValueError(f"Missing required features: {missing}")

    return df[list(feature_names)]


def predict_crop(input_data: Dict[str, Any], user_id: int | None = None) -> Dict[str, Any]:
    """
    Predict crop class and confidence.
    Confidence is the highest class probability from predict_proba.
    """
    try:
        cleaned_input = _preprocess_input(input_data)
    except PreprocessingError as exc:
        return {"error": {"type": "validation_error", **exc.to_dict()}}

    df = _to_dataframe(cleaned_input)
    df = _align_features(df, classifier_model)

    predicted_class = classifier_model.predict(df)[0]
    probabilities = classifier_model.predict_proba(df)[0]
    classes = getattr(classifier_model, "classes_", [])

    best_index = int(probabilities.argmax())
    confidence = float(probabilities[best_index])
    top_indices = probabilities.argsort()[-5:][::-1]

    top_crops = [
        {
            "crop": str(classes[index]) if len(classes) > index else str(index),
            "confidence": float(probabilities[index]),
        }
        for index in top_indices
    ]

    is_low_confidence = confidence < settings.crop_confidence_threshold

    result = {
        "predicted_crop": predicted_class,
        "confidence": confidence,
        "confidence_threshold": settings.crop_confidence_threshold,
        "is_low_confidence": is_low_confidence,
        "confidence_note": (
            "Low-confidence recommendation. Review the top alternatives before making a decision."
            if is_low_confidence
            else "Recommendation confidence is above the configured threshold."
        ),
        "top_crops": top_crops,
    }
    _safe_log_prediction(
        input_payload=cleaned_input,
        crop_prediction=str(predicted_class),
        crop_confidence=confidence,
        irrigation_prediction=None,
        user_id=user_id,
    )
    return result


def predict_irrigation(input_data: Dict[str, Any], user_id: int | None = None) -> Dict[str, Any]:
    """Predict irrigation requirement using the regression model."""
    try:
        cleaned_input = _preprocess_input(input_data)
    except PreprocessingError as exc:
        return {"error": {"type": "validation_error", **exc.to_dict()}}

    df = _to_dataframe(cleaned_input)
    df = _align_features(df, regressor_model)

    prediction = float(regressor_model.predict(df)[0])
    result = {"predicted_irrigation_requirement": prediction}
    _safe_log_prediction(
        input_payload=cleaned_input,
        crop_prediction=None,
        crop_confidence=None,
        irrigation_prediction=prediction,
        user_id=user_id,
    )
    return result


def _safe_log_prediction(
    input_payload: Dict[str, Any],
    crop_prediction: str | None,
    crop_confidence: float | None,
    irrigation_prediction: float | None,
    user_id: int | None,
) -> None:
    """Persist prediction details without breaking request flow on DB errors."""
    try:
        insert_prediction(
            input_payload=input_payload,
            crop_prediction=crop_prediction,
            crop_confidence=crop_confidence,
            irrigation_prediction=irrigation_prediction,
            user_id=user_id,
        )
    except Exception as exc:
        logger.exception("Prediction logging failed: %s", exc)


def _preprocess_input(input_data: Dict[str, Any]) -> Dict[str, float]:
    casted = validate_and_cast_types(input_data)
    ranged = validate_ranges(casted)
    return enforce_feature_order(ranged)
