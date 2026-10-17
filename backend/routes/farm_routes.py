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
    update_field_area,
)
from services.soil_planning_service import (
    add_regenerative_practice,
    add_soil_test,
    get_carbon_readiness,
    get_soil_plan,
    save_soil_plan,
    update_regenerative_practice,
    update_soil_test,
    update_soil_task,
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
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify({"intervention": acknowledge_intervention(_user_id(), intervention_id, str(payload.get("notes", "")), str(payload.get("practice_group", "recommended")))}), 200
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


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
        result = build_rationale(_user_id(), farm_id, request.args.get("field_id", type=int), request.args.get("crop", "").strip().lower(), request.args.get("problem", "").strip().lower(), request.args.get("practice_group", "").strip().lower())
        return jsonify({"rationale": result}), 200
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404


@farm_bp.get("/api/farms/<int:farm_id>/soil-plan")
@role_required("farmer", "admin")
def soil_plan(farm_id: int):
    field_id = request.args.get("field_id", type=int)
    if not field_id:
        return jsonify({"error": "field_id is required."}), 400
    try:
        return jsonify(get_soil_plan(_user_id(), farm_id, field_id)), 200
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404


@farm_bp.post("/api/farms/<int:farm_id>/soil-plan")
@role_required("farmer", "admin")
def save_field_soil_plan(farm_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        saved = save_soil_plan(_user_id(), farm_id, int(payload.get("field_id")), payload.get("start_date"), payload.get("plan"))
        return jsonify(saved), 200
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc) or "field_id is required."}), 400
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404


@farm_bp.patch("/api/soil-plan-tasks/<int:task_id>")
@role_required("farmer", "admin")
def update_soil_plan_task(task_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify({"task": update_soil_task(_user_id(), task_id, str(payload.get("status", "")), str(payload.get("notes", "")))}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404


@farm_bp.patch("/api/farms/<int:farm_id>/fields/<int:field_id>")
@role_required("farmer", "admin")
def update_field(farm_id: int, field_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify({"field": update_field_area(_user_id(), farm_id, field_id, payload.get("area_ha"))}), 200
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@farm_bp.get("/api/farms/<int:farm_id>/carbon-readiness")
@role_required("farmer", "admin")
def carbon_readiness(farm_id: int):
    field_id = request.args.get("field_id", type=int)
    if not field_id:
        return jsonify({"error": "field_id is required."}), 400
    try:
        return jsonify(get_carbon_readiness(_user_id(), farm_id, field_id)), 200
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404


@farm_bp.post("/api/farms/<int:farm_id>/soil-tests")
@role_required("farmer", "admin")
def add_field_soil_test(farm_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        sample = add_soil_test(_user_id(), farm_id, int(payload.get("field_id")), payload)
        return jsonify({"soil_test": sample}), 201
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc) or "field_id is required."}), 400
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404


@farm_bp.put("/api/soil-tests/<int:record_id>")
@role_required("farmer", "admin")
def edit_soil_test(record_id: int):
    try:
        return jsonify({"soil_test": update_soil_test(_user_id(), record_id, request.get_json(silent=True) or {})}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404


@farm_bp.post("/api/farms/<int:farm_id>/regenerative-practices")
@role_required("farmer", "admin")
def add_field_regenerative_practice(farm_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        practice = add_regenerative_practice(_user_id(), farm_id, int(payload.get("field_id")), payload)
        return jsonify({"practice": practice}), 201
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc) or "field_id is required."}), 400
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404


@farm_bp.put("/api/regenerative-practices/<int:record_id>")
@role_required("farmer", "admin")
def edit_regenerative_practice(record_id: int):
    try:
        return jsonify({"practice": update_regenerative_practice(_user_id(), record_id, request.get_json(silent=True) or {})}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
