from __future__ import annotations

import sys
from pathlib import Path

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import db
from routes.feedback_routes import feedback_bp


@pytest.fixture()
def feedback_client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "feedback.sqlite3")
    db.init_db()
    farmer = db.create_user("Feedback Farmer", "feedback@example.com", "hash", "farmer")
    admin = db.create_user("Feedback Admin", "admin-feedback@example.com", "hash", "admin")
    app = Flask(__name__)
    app.config.update(TESTING=True, JWT_SECRET_KEY="translation-feedback-test-secret")
    JWTManager(app)
    app.register_blueprint(feedback_bp)
    client = app.test_client()

    def auth(user, role):
        with app.app_context():
            token = create_access_token(
                identity=str(user["id"]),
                additional_claims={"user_id": user["id"], "role": role},
            )
        return {"Authorization": f"Bearer {token}"}

    return client, farmer, admin, auth


def test_translation_feedback_is_saved_and_admin_can_resolve(feedback_client):
    client, farmer, admin, auth = feedback_client
    created = client.post(
        "/api/translation-feedback",
        headers=auth(farmer, "farmer"),
        json={
            "language": "hi",
            "page": "/dashboard",
            "reported_text": "मौसम संकेत",
            "suggested_text": "मौसम की चेतावनी",
            "note": "This label is unclear in context.",
        },
    )
    assert created.status_code == 201
    feedback_id = created.get_json()["feedback"]["id"]

    forbidden = client.get("/api/admin/translation-feedback", headers=auth(farmer, "farmer"))
    assert forbidden.status_code == 403
    listed = client.get("/api/admin/translation-feedback?status=open", headers=auth(admin, "admin"))
    assert listed.status_code == 200
    assert listed.get_json()["feedback"][0]["reported_text"] == "मौसम संकेत"

    resolved = client.patch(
        f"/api/admin/translation-feedback/{feedback_id}",
        headers=auth(admin, "admin"),
        json={"status": "resolved"},
    )
    assert resolved.status_code == 200
    assert client.get("/api/admin/translation-feedback?status=open", headers=auth(admin, "admin")).get_json()["feedback"] == []


def test_translation_feedback_validates_payload(feedback_client):
    client, farmer, _, auth = feedback_client
    response = client.post(
        "/api/translation-feedback",
        headers=auth(farmer, "farmer"),
        json={"language": "en", "reported_text": "Text", "note": "Needs review"},
    )
    assert response.status_code == 400
