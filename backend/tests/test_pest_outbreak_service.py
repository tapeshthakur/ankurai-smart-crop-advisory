from __future__ import annotations

import numpy as np

from services import pest_outbreak_service


class PestModel:
    classes_ = np.array([0, 1])

    def predict_proba(self, frame):
        rows = []
        for _, row in frame.iterrows():
            probability = 0.76 if row["pest_aphid"] == 1 else 0.18
            rows.append([1 - probability, probability])
        return np.array(rows)


def test_pest_outbreak_forecast_scores_requested_pests(monkeypatch):
    monkeypatch.setattr(pest_outbreak_service, "pest_outbreak_model", PestModel())

    result = pest_outbreak_service.predict_pest_outbreak(
        {
            "crop": "wheat",
            "pests": ["aphid", "whitefly"],
            "month": 9,
            "days_after_sowing": 48,
            "temperature_c": 27,
            "humidity_pct": 78,
            "rainfall_7d_mm": 34,
            "rainfall_14d_mm": 62,
            "wind_speed_kmh": 8,
            "soil_moisture_pct": 42,
            "trap_count_7d": 11,
            "previous_pest_count_7d": 7,
        }
    )

    assert result["crop"] == "wheat"
    assert result["forecast_window_days"] == 7
    assert result["highest_risk"]["pest"] == "aphid"
    assert result["highest_risk"]["risk_level"] == "high"
    assert result["forecasts"][0]["outbreak_next_7d"] == 1
    assert len(result["forecasts"]) == 2
