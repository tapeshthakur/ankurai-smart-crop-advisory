from __future__ import annotations

import sys
from pathlib import Path

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import db
from routes import ai_routes


@pytest.fixture()
def ai_client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "ai.sqlite3")
    db.init_db()
    farmer = db.create_user("AI Farmer", "ai-farmer@example.com", "hash", "farmer")
    admin = db.create_user("AI Admin", "ai-admin@example.com", "hash", "admin")
    app = Flask(__name__)
    app.config.update(TESTING=True, JWT_SECRET_KEY="ai-test-secret-long-enough-for-sha256-signing")
    JWTManager(app)
    app.register_blueprint(ai_routes.ai_bp)
    client = app.test_client()
    def auth(user, role):
        with app.app_context():
            token = create_access_token(
                identity=str(user["id"]),
                additional_claims={"user_id": user["id"], "role": role},
            )
        return {"Authorization": f"Bearer {token}"}

    return client, farmer, admin, auth


def test_stream_discloses_only_context_keys_supplied(ai_client, monkeypatch):
    client, farmer, _, auth = ai_client
    monkeypatch.setattr(ai_routes, "stream_groq_farmer_assistant", lambda *args, **kwargs: iter(["Check the field."]))
    response = client.post(
        "/api/ai/chat/stream",
        headers=auth(farmer, "farmer"),
        json={"message": "What next?", "context": {"selectedState": "Maharashtra", "form": {"ph": 6.5}, "market": {"mandi": {"records": [{"market": "Pune"}]}}, "untrusted_extra": "never include me"}},
    )
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert '"context_used": ["state_season", "soil_weather_inputs", "market_prices"]' in body
    assert '"text": "Check the field."' in body
    assert '"type":"done"' in body


def test_ai_feedback_is_private_and_admin_readable(ai_client):
    client, farmer, admin, auth = ai_client
    saved = client.post("/api/ai/feedback", headers=auth(farmer, "farmer"), json={"rating": "helpful"})
    assert saved.status_code == 201
    forbidden = client.get("/api/admin/ai-feedback", headers=auth(farmer, "farmer"))
    assert forbidden.status_code == 403
    listed = client.get("/api/admin/ai-feedback", headers=auth(admin, "admin"))
    assert listed.status_code == 200
    assert listed.get_json()["feedback"][0]["rating"] == "helpful"
    assert "answer" not in listed.get_json()["feedback"][0]


def test_stream_rate_limit_is_scoped_to_authenticated_user(ai_client, monkeypatch):
    client, farmer, _, auth = ai_client
    monkeypatch.setattr(ai_routes, "stream_groq_farmer_assistant", lambda *args, **kwargs: iter(["ok"]))
    headers = auth(farmer, "farmer")
    for _ in range(ai_routes._RATE_LIMIT):
        assert client.post("/api/ai/chat/stream", headers=headers, json={"message": "Hi"}).status_code == 200
    limited = client.post("/api/ai/chat/stream", headers=headers, json={"message": "Hi"})
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) > 0


def test_ai_feedback_rejects_invalid_rating(ai_client):
    client, farmer, _, auth = ai_client
    response = client.post("/api/ai/feedback", headers=auth(farmer, "farmer"), json={"rating": "maybe"})
    assert response.status_code == 400
