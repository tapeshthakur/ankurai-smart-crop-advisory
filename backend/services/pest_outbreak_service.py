from __future__ import annotations

from typing import Any, Dict, Iterable, List

import pandas as pd

from models import model_loader


CROP_COLUMNS = ["crop_rice", "crop_wheat", "crop_maize", "crop_cotton", "crop_soybean"]
PEST_COLUMNS = ["pest_stem_borer", "pest_aphid", "pest_fall_armyworm", "pest_whitefly"]
NUMERIC_COLUMNS = [
    "month",
    "days_after_sowing",
    "temperature_c",
    "humidity_pct",
    "rainfall_7d_mm",
    "rainfall_14d_mm",
    "wind_speed_kmh",
    "soil_moisture_pct",
    "trap_count_7d",
    "previous_pest_count_7d",
]
FEATURE_COLUMNS = CROP_COLUMNS + PEST_COLUMNS + NUMERIC_COLUMNS

CROP_ALIASES = {
    "rice": "crop_rice",
    "paddy": "crop_rice",
    "wheat": "crop_wheat",
    "maize": "crop_maize",
    "corn": "crop_maize",
    "cotton": "crop_cotton",
    "soybean": "crop_soybean",
    "soya": "crop_soybean",
}

PEST_ALIASES = {
    "stem_borer": "pest_stem_borer",
    "stem borer": "pest_stem_borer",
    "aphid": "pest_aphid",
    "aphids": "pest_aphid",
    "fall_armyworm": "pest_fall_armyworm",
    "fall armyworm": "pest_fall_armyworm",
    "whitefly": "pest_whitefly",
    "white fly": "pest_whitefly",
}

pest_outbreak_model = model_loader.load_latest_pest_outbreak_classifier()


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _label_from_column(column: str) -> str:
    return column.replace("pest_", "").replace("_", " ")


def _risk_level(probability: float) -> str:
    if probability >= 0.70:
        return "high"
    if probability >= 0.40:
        return "moderate"
    return "low"


def _positive_class_probability(model: Any, frame: pd.DataFrame) -> List[float]:
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(frame)
        classes = list(getattr(model, "classes_", []))
        positive_index = classes.index(1) if 1 in classes else probabilities.shape[1] - 1
        return [float(row[positive_index]) for row in probabilities]
    return [float(value) for value in model.predict(frame)]


def _resolve_pests(raw: Any) -> List[str]:
    if raw is None:
        return PEST_COLUMNS
    values: Iterable[Any] = raw if isinstance(raw, list) else [raw]
    resolved = []
    for value in values:
        key = _normalize_key(value).replace("_", " ")
        column = PEST_ALIASES.get(key) or PEST_ALIASES.get(key.replace(" ", "_"))
        if not column:
            raise ValueError(f"Unsupported pest: {value}")
        if column not in resolved:
            resolved.append(column)
    return resolved


def _numeric_value(payload: Dict[str, Any], key: str, default: float) -> float:
    try:
        return float(payload.get(key, default))
    except (TypeError, ValueError):
        raise ValueError(f"Field '{key}' must be numeric.") from None


def predict_pest_outbreak(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Input payload must be a JSON object.")

    crop_key = _normalize_key(payload.get("crop")).replace("_", " ")
    crop_column = CROP_ALIASES.get(crop_key) or CROP_ALIASES.get(crop_key.replace(" ", "_"))
    if not crop_column:
        raise ValueError("Provide a supported crop: rice, wheat, maize, cotton, or soybean.")

    pest_columns = _resolve_pests(payload.get("pests") or payload.get("pest"))
    base_numeric = {
        "month": _numeric_value(payload, "month", 7),
        "days_after_sowing": _numeric_value(payload, "days_after_sowing", 45),
        "temperature_c": _numeric_value(payload, "temperature_c", payload.get("temperature", 28)),
        "humidity_pct": _numeric_value(payload, "humidity_pct", payload.get("humidity", 70)),
        "rainfall_7d_mm": _numeric_value(payload, "rainfall_7d_mm", payload.get("rainfall", 20)),
        "rainfall_14d_mm": _numeric_value(payload, "rainfall_14d_mm", _numeric_value(payload, "rainfall_7d_mm", payload.get("rainfall", 20)) * 1.7),
        "wind_speed_kmh": _numeric_value(payload, "wind_speed_kmh", 8),
        "soil_moisture_pct": _numeric_value(payload, "soil_moisture_pct", 35),
        "trap_count_7d": _numeric_value(payload, "trap_count_7d", 0),
        "previous_pest_count_7d": _numeric_value(payload, "previous_pest_count_7d", 0),
    }

    rows = []
    for pest_column in pest_columns:
        row = {column: 0 for column in CROP_COLUMNS + PEST_COLUMNS}
        row[crop_column] = 1
        row[pest_column] = 1
        row.update(base_numeric)
        rows.append(row)

    frame = pd.DataFrame(rows, columns=FEATURE_COLUMNS)
    probabilities = _positive_class_probability(pest_outbreak_model, frame)

    forecasts = []
    for pest_column, probability in zip(pest_columns, probabilities):
        forecasts.append(
            {
                "pest": _label_from_column(pest_column),
                "outbreak_probability": probability,
                "outbreak_next_7d": int(probability >= 0.5),
                "risk_level": _risk_level(probability),
            }
        )

    forecasts.sort(key=lambda item: item["outbreak_probability"], reverse=True)
    return {
        "crop": crop_column.replace("crop_", ""),
        "forecast_window_days": 7,
        "features_used": base_numeric,
        "forecasts": forecasts,
        "highest_risk": forecasts[0] if forecasts else None,
    }
