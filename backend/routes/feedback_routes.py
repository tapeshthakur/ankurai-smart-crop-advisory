from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt

from database.db import (
    create_translation_feedback,
    list_translation_feedback,
    update_translation_feedback_status,
)
from utils.auth import role_required

feedback_bp = Blueprint("feedback_bp", __name__)


@feedback_bp.post("/api/translation-feedback")
@role_required("farmer", "admin")
def submit_translation_feedback():
    payload = request.get_json(silent=True) or {}
    language = str(payload.get("language", "")).strip().lower()
    page = str(payload.get("page", "")).strip()[:160]
    reported_text = str(payload.get("reported_text", "")).strip()
    suggested_text = str(payload.get("suggested_text", "")).strip()
    note = str(payload.get("note", "")).strip()
    if language not in {"hi", "mr"}:
        return jsonify({"error": "Choose Hindi or Marathi translation feedback."}), 400
    if not reported_text or len(reported_text) > 1000:
        return jsonify({"error": "Reported text is required and must be at most 1000 characters."}), 400
    if not note or len(note) > 2000 or len(suggested_text) > 1000:
        return jsonify({"error": "Add a short note; keep notes under 2000 and suggestions under 1000 characters."}), 400
    feedback = create_translation_feedback(
        int(get_jwt()["user_id"]), language, page, reported_text, suggested_text, note
    )
    return jsonify({"feedback": feedback}), 201


@feedback_bp.get("/api/admin/translation-feedback")
@role_required("admin")
def get_translation_feedback():
    status = request.args.get("status")
    if status and status not in {"open", "reviewed", "resolved"}:
        return jsonify({"error": "Invalid status filter."}), 400
    return jsonify({"feedback": list_translation_feedback(status=status)}), 200


@feedback_bp.patch("/api/admin/translation-feedback/<int:feedback_id>")
@role_required("admin")
def update_feedback(feedback_id: int):
    payload = request.get_json(silent=True) or {}
    status = str(payload.get("status", "")).strip().lower()
    if status not in {"open", "reviewed", "resolved"}:
        return jsonify({"error": "Choose open, reviewed, or resolved."}), 400
    if not update_translation_feedback_status(feedback_id, status):
        return jsonify({"error": "Translation feedback was not found."}), 404
    return jsonify({"id": feedback_id, "status": status}), 200
