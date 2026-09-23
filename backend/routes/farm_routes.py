from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt

from services.farm_service import (
    acknowledge_intervention,
    build_rationale,
    create_field,
    create_farm,
    get_follow_up,
    list_farms,
    list_reminders,
    record_outcome,
)
from utils.auth import role_required

farm_bp = Blueprint("farm_bp", __name__)


def _user_id() -> int:
    return int(get_jwt()["user_id"])


@farm_bp.get("/api/farms")
@role_required("farmer", "admin")
def farms():
    return jsonify({"farms": list_farms(_user_id())}), 200


@farm_bp.post("/api/farms")
@role_required("farmer", "admin")
def add_farm():
    try:
        return jsonify({"farm": create_farm(_user_id(), request.get_json(silent=True) or {})}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@farm_bp.post("/api/farms/<int:farm_id>/fields")
@role_required("farmer", "admin")
def add_field(farm_id: int):
    try:
        return jsonify({"field": create_field(_user_id(), farm_id, request.get_json(silent=True) or {})}), 201
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@farm_bp.get("/api/farms/<int:farm_id>/reminders")
@role_required("farmer", "admin")
def reminders(farm_id: int):
    try:
        return jsonify({"reminders": list_reminders(_user_id(), farm_id)}), 200
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404


@farm_bp.post("/api/interventions/<int:intervention_id>/acknowledge")
@role_required("farmer", "admin")
def acknowledge(intervention_id: int):
    try:
        return jsonify({"intervention": acknowledge_intervention(_user_id(), intervention_id, (request.get_json(silent=True) or {}).get("notes", ""))}), 200
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404


@farm_bp.post("/api/interventions/<int:intervention_id>/follow-up")
@role_required("farmer", "admin")
def follow_up(intervention_id: int):
    try:
        return jsonify({"follow_up": get_follow_up(_user_id(), intervention_id)}), 200
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@farm_bp.post("/api/interventions/<int:intervention_id>/outcome")
@role_required("farmer", "admin")
def outcome(intervention_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify({"outcome": record_outcome(_user_id(), intervention_id, str(payload.get("status", "unknown")), str(payload.get("notes", "")))}), 201
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@farm_bp.get("/api/farms/<int:farm_id>/rationale")
@role_required("farmer", "admin")
def rationale(farm_id: int):
    try:
        result = build_rationale(_user_id(), farm_id, request.args.get("field_id", type=int), request.args.get("crop", "").strip().lower(), request.args.get("problem", "").strip().lower(), request.args.get("intervention_type", "").strip().lower())
        return jsonify({"rationale": result}), 200
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
