from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt

from services.prediction_service import predict_crop
from services.farm_service import build_rationale, create_recommendation
from utils.auth import role_required


crop_bp = Blueprint("crop_bp", __name__)


@crop_bp.route("/api/predict/crop", methods=["POST"])
@role_required("farmer", "admin")
def predict_crop_route():
    """Predict crop label from soil/weather inputs."""
    try:
        payload = request.get_json(silent=True)
        if payload is None:
            return jsonify({"error": "Invalid or missing JSON body."}), 400

        claims = get_jwt()
        user_id = claims.get("user_id")

        result = predict_crop(payload, user_id=user_id)
        if "error" in result:
            return jsonify(result), 400

        farm_id = payload.get("farm_id")
        if farm_id:
            try:
                result["recommendation_tracking"] = create_recommendation(
                    user_id=user_id,
                    farm_id=int(farm_id),
                    field_id=int(payload["field_id"]) if payload.get("field_id") else None,
                    crop=str(result.get("predicted_crop", result.get("crop", ""))).lower(),
                    problem=str(payload.get("problem", "")).strip().lower(),
                    description="Review the crop and irrigation recommendation, then record the action taken.",
                )
                result["rationale"] = build_rationale(
                    user_id=user_id,
                    farm_id=int(farm_id),
                    field_id=int(payload["field_id"]) if payload.get("field_id") else None,
                    crop=str(result.get("predicted_crop", result.get("crop", ""))).lower(),
                    problem=str(payload.get("problem", "")).strip().lower(),
                )
            except (LookupError, ValueError) as exc:
                return jsonify({"error": str(exc)}), 400

        return jsonify({"result": result}), 200
    except Exception:
        return jsonify({"error": "Internal server error."}), 500
