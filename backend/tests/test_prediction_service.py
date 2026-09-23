from __future__ import annotations

import numpy as np
from types import SimpleNamespace

from services import prediction_service


class LowConfidenceClassifier:
    classes_ = np.array(["rice", "wheat", "maize"])

    def predict(self, _df):
        return np.array(["rice"])

    def predict_proba(self, _df):
        return np.array([[0.40, 0.35, 0.25]])


def test_crop_prediction_returns_best_crop_when_confidence_is_low(monkeypatch):
    monkeypatch.setattr(prediction_service, "classifier_model", LowConfidenceClassifier())
    monkeypatch.setattr(prediction_service, "_safe_log_prediction", lambda **_: None)
    monkeypatch.setattr(
        prediction_service,
        "settings",
        SimpleNamespace(crop_confidence_threshold=0.80),
    )

    result = prediction_service.predict_crop(
        {
            "N": 52,
            "P": 50,
            "K": 52,
            "temperature": 20,
            "humidity": 68,
            "ph": 6.7,
            "rainfall": 140,
        }
    )

    assert "error" not in result
    assert result["predicted_crop"] == "rice"
    assert result["confidence"] == 0.40
    assert result["is_low_confidence"] is True
    assert result["confidence_threshold"] == 0.80
    assert result["top_crops"][0] == {"crop": "rice", "confidence": 0.40}
