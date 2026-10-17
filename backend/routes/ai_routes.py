from __future__ import annotations

import json

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context
from flask_jwt_extended import get_jwt

from database.db import create_ai_answer_feedback, list_ai_answer_feedback, reserve_ai_chat_request
from services.groq_service import GroqServiceError, ask_groq_farmer_assistant, stream_groq_farmer_assistant
from utils.auth import role_required


ai_bp = Blueprint("ai_bp", __name__)
_RATE_LIMIT = 10
_RATE_WINDOW_SECONDS = 60


def _validated_payload():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None, (jsonify({"error": "Invalid or missing JSON body."}), 400)
    message = str(payload.get("message", "")).strip()
    if not message:
        return None, (jsonify({"error": "Question is required."}), 400)
    if len(message) > 1200:
        return None, (jsonify({"error": "Question is too long. Please keep it under 1200 characters."}), 400)
    raw_context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    allowed_context = {"selectedState", "selectedSeason", "form", "liveWeather", "result", "advisory", "pestForecast", "latestCrop", "recentPredictions", "market"}
    context = {key: raw_context[key] for key in allowed_context if key in raw_context}
    raw_history = payload.get("history") if isinstance(payload.get("history"), list) else []
    history = [
        {"role": item.get("role"), "content": str(item.get("content", ""))[:1200]}
        for item in raw_history[-8:]
        if isinstance(item, dict) and item.get("role") in {"assistant", "user"}
    ]
    language = str(payload.get("language", "en")).lower()
    if language not in {"en", "hi", "mr"}:
        language = "en"
    return {"message": message, "context": context, "history": history, "language": language}, None


def _check_rate_limit(user_id: int) -> int:
    return reserve_ai_chat_request(user_id, _RATE_LIMIT, _RATE_WINDOW_SECONDS)


def _context_sources(context: dict) -> list[str]:
    sources = []
    market = context.get("market") if isinstance(context.get("market"), dict) else {}
    mandi = market.get("mandi") if isinstance(market.get("mandi"), dict) else {}
    msp = market.get("msp") if isinstance(market.get("msp"), dict) else {}
    if context.get("selectedState"):
        sources.append("state_season")
    if isinstance(context.get("form"), dict) and any(value not in (None, "") for value in context["form"].values()):
        sources.append("soil_weather_inputs")
    if context.get("result"):
        sources.append("crop_prediction")
    if context.get("advisory"):
        sources.append("farm_advisory")
    if context.get("liveWeather"):
        sources.append("session_weather")
    if context.get("pestForecast"):
        sources.append("pest_outlook")
    if context.get("recentPredictions"):
        sources.append("saved_predictions")
    if mandi.get("records"):
        sources.append("market_prices")
    if msp.get("value") is not None:
        sources.append("msp_reference")
    return sources


@ai_bp.route("/api/ai/chat", methods=["POST"])
@role_required("farmer", "admin")
def ai_chat_route():
    payload, error = _validated_payload()
    if error:
        return error
    retry_after = _check_rate_limit(int(get_jwt()["user_id"]))
    if retry_after:
        return jsonify({"error": "You are sending questions too quickly. Please wait a moment and try again."}), 429, {"Retry-After": str(retry_after)}

    try:
        answer = ask_groq_farmer_assistant(
            payload["message"], language=payload["language"], context=payload["context"], history=payload["history"],
        )
        return jsonify({"answer": answer}), 200
    except GroqServiceError as exc:
        return jsonify({"error": str(exc)}), 503


@ai_bp.post("/api/ai/chat/stream")
@role_required("farmer", "admin")
def ai_chat_stream_route():
    payload, error = _validated_payload()
    if error:
        return error
    retry_after = _check_rate_limit(int(get_jwt()["user_id"]))
    if retry_after:
        return jsonify({"error": "You are sending questions too quickly. Please wait a moment and try again."}), 429, {"Retry-After": str(retry_after)}

    def event_stream():
        sources = _context_sources(payload["context"])
        yield f"data: {json.dumps({'type': 'meta', 'context_used': sources}, ensure_ascii=False)}\n\n"
        got_content = False
        try:
            for fragment in stream_groq_farmer_assistant(
                payload["message"], language=payload["language"], context=payload["context"], history=payload["history"]
            ):
                got_content = True
                yield f"data: {json.dumps({'type': 'delta', 'text': fragment}, ensure_ascii=False)}\n\n"
            if not got_content:
                yield f"data: {json.dumps({'type': 'error', 'error': 'AI returned an empty answer. Please try again.'})}\n\n"
            else:
                yield "data: {\"type\":\"done\"}\n\n"
        except GroqServiceError as exc:
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)}, ensure_ascii=False)}\n\n"
        except Exception:
            current_app.logger.exception("Unexpected AI streaming error")
            yield f"data: {json.dumps({'type': 'error', 'error': 'AI assistant encountered a temporary error. Please retry.'})}\n\n"

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@ai_bp.post("/api/ai/feedback")
@role_required("farmer", "admin")
def ai_feedback_route():
    payload = request.get_json(silent=True) or {}
    rating = str(payload.get("rating", ""))
    category = str(payload.get("category", "general"))
    if rating not in {"helpful", "not_helpful"} or category not in {"general", "accuracy", "clarity", "language", "safety"}:
        return jsonify({"error": "Choose a valid rating and feedback category."}), 400
    feedback = create_ai_answer_feedback(int(get_jwt()["user_id"]), rating, category)
    return jsonify({"feedback": feedback}), 201


@ai_bp.get("/api/admin/ai-feedback")
@role_required("admin")
def ai_feedback_list_route():
    return jsonify({"feedback": list_ai_answer_feedback()}), 200
