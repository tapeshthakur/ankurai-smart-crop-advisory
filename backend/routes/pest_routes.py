from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.pest_outbreak_service import predict_pest_outbreak
from utils.auth import role_required


pest_bp = Blueprint("pest_bp", __name__)


@pest_bp.route("/api/predict/pest-outbreak", methods=["POST"])
@role_required("farmer", "admin")
def predict_pest_outbreak_route():
    """Predict next-7-day pest outbreak risk from weekly field observations."""
    try:
        payload = request.get_json(silent=True)
        if payload is None:
            return jsonify({"error": "Invalid or missing JSON body."}), 400

        result = predict_pest_outbreak(payload)
        return jsonify({"result": result}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Internal server error."}), 500
