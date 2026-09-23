from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.advisory_service import build_full_advisory
from services.farm_service import build_rationale
from flask_jwt_extended import get_jwt
from utils.auth import role_required


advisory_bp = Blueprint("advisory_bp", __name__)


@advisory_bp.route("/api/advisory", methods=["POST"])
@role_required("farmer", "admin")
def advisory_route():
    """Build farmer-friendly advisory from prediction outputs and inputs."""
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Invalid or missing JSON body."}), 400

    required = ["crop", "confidence", "irrigation", "inputs"]
    missing = [field for field in required if field not in payload]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    try:
        advisory = build_full_advisory(
            crop=payload["crop"],
            confidence=float(payload["confidence"]),
            irrigation_value=float(payload["irrigation"]),
            inputs=payload["inputs"],
            season=payload.get("season"),
            state=payload.get("state"),
            top_crops=payload.get("top_crops"),
            planting_date=payload.get("planting_date"),
        )
        farm_id = payload.get("farm_id")
        if farm_id:
            advisory["rationale"] = build_rationale(
                user_id=int(get_jwt()["user_id"]),
                farm_id=int(farm_id),
                field_id=int(payload["field_id"]) if payload.get("field_id") else None,
                crop=str(payload["crop"]).strip().lower(),
                problem=str(payload.get("problem", "")).strip().lower(),
            )
        return jsonify({"advisory": advisory}), 200
    except (LookupError, TypeError, ValueError) as exc:
        return jsonify({"error": f"Invalid advisory payload: {exc}"}), 400
