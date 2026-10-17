from __future__ import annotations

import csv
import json
from typing import Any, Dict

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt

from config import settings
from database.db import (
    get_prediction_count,
    get_recent_predictions,
    get_recent_predictions_for_user,
    get_usage_analytics,
    get_user_count,
)
from utils.auth import role_required


system_bp = Blueprint("system_bp", __name__)


def _ml_dir():
    return settings.ml_dir


def _read_latest_json(pattern: str) -> Dict[str, Any]:
    latest = _latest_path(pattern)
    with latest.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _latest_path(pattern: str):
    candidates = list(_ml_dir().glob(pattern))
    if not candidates:
        raise FileNotFoundError(f"No ML artifact found for pattern: {pattern}")

    return max(candidates, key=lambda p: p.stat().st_mtime)


def _read_latest_feature_importance(pattern: str):
    latest = _latest_path(pattern)
    with latest.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        rows = []
        for row in reader:
            rows.append(
                {
                    "feature": row.get("feature", ""),
                    "importance": float(row.get("importance") or 0),
                }
            )
        return rows


def _artifact_summary(pattern: str) -> Dict[str, Any]:
    latest = _latest_path(pattern)
    stat = latest.stat()
    return {
        "file": latest.name,
        "updated_at": stat.st_mtime,
        "size_kb": round(stat.st_size / 1024, 2),
    }


def _read_optional_json(pattern: str) -> Dict[str, Any] | None:
    try:
        return _read_latest_json(pattern)
    except FileNotFoundError:
        return None


def _optional_artifact_summary(pattern: str) -> Dict[str, Any] | None:
    try:
        return _artifact_summary(pattern)
    except FileNotFoundError:
        return None


@system_bp.get("/api/model-info")
@role_required("admin")
def model_info():
    """Return model metrics plus explainability artifacts."""
    try:
        classifier_metrics = _read_latest_json("**/rf_classifier_*_metrics.json")
        regressor_metrics = _read_latest_json("**/rf_regressor_*_metrics.json")
        disease_metrics = _read_optional_json("**/leaf_disease_training_report.json")
        classifier_feature_importance = _read_latest_feature_importance(
            "**/rf_classifier_*_feature_importance.csv"
        )
        regressor_feature_importance = _read_latest_feature_importance(
            "**/rf_regressor_*_feature_importance.csv"
        )

        return (
            jsonify(
                {
                    "classifier_metrics": classifier_metrics,
                    "regressor_metrics": regressor_metrics,
                    "disease_metrics": disease_metrics,
                    "classifier_feature_importance": classifier_feature_importance,
                    "regressor_feature_importance": regressor_feature_importance,
                    "artifacts": {
                        "classifier_model": _artifact_summary("**/rf_classifier_*_v*.pkl"),
                        "regressor_model": _artifact_summary("**/rf_regressor_*_v*.pkl"),
                        "classifier_metrics": _artifact_summary("**/rf_classifier_*_metrics.json"),
                        "regressor_metrics": _artifact_summary("**/rf_regressor_*_metrics.json"),
                        "disease_model": _optional_artifact_summary("**/leaf_disease_mobilenetv2.keras"),
                        "disease_labels": _optional_artifact_summary("**/labels.json"),
                        "disease_training_report": _optional_artifact_summary(
                            "**/leaf_disease_training_report.json"
                        ),
                    },
                }
            ),
            200,
        )
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except (csv.Error, json.JSONDecodeError, OSError, ValueError) as exc:
        return jsonify({"error": f"Failed to read model metrics: {exc}"}), 500


@system_bp.get("/api/predictions")
@role_required("farmer", "admin")
def list_predictions():
    """Return latest prediction records from SQLite based on role."""
    try:
        claims = get_jwt()
        role = claims.get("role")
        user_id = int(claims.get("user_id"))

        if role == "admin":
            records = get_recent_predictions(limit=20)
        else:
            records = get_recent_predictions_for_user(user_id=user_id, limit=20)

        return jsonify({"predictions": records}), 200
    except Exception:
        return jsonify({"error": "Failed to fetch predictions."}), 500


@system_bp.get("/api/admin/stats")
@role_required("admin")
def admin_stats():
    try:
        return jsonify({"total_predictions": get_prediction_count(), "user_count": get_user_count()}), 200
    except Exception:
        return jsonify({"error": "Failed to fetch admin stats."}), 500


@system_bp.get("/api/admin/usage")
@role_required("admin")
def admin_usage():
    try:
        return jsonify(get_usage_analytics()), 200
    except Exception:
        return jsonify({"error": "Failed to fetch aggregate usage analytics."}), 500
