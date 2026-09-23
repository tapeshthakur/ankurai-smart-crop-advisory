from __future__ import annotations

import sqlite3

import pytest

from database import db
from services import farm_service


@pytest.fixture()
def farm_db(tmp_path, monkeypatch):
    path = tmp_path / "outcome.sqlite3"
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(farm_service, "get_connection", db.get_connection)
    db.init_db()
    user = db.create_user("Outcome Farmer", "outcome@example.com", "hash", "farmer")
    farm = farm_service.create_farm(user["id"], {"name": "Demo Farm"})
    return user["id"], farm["id"]


def test_reminder_lifecycle_and_duplicate_prevention(farm_db):
    user_id, farm_id = farm_db
    first = farm_service.create_recommendation(user_id, farm_id, None, "tomato", "early blight", "Apply treatment")
    duplicate = farm_service.create_recommendation(user_id, farm_id, None, "tomato", "early blight", "Apply treatment")
    assert duplicate["duplicate"] is True
    reminders = farm_service.list_reminders(user_id, farm_id)
    assert reminders[0]["kind"] == "action"
    farm_service.acknowledge_intervention(user_id, first["intervention_id"])
    assert farm_service.list_reminders(user_id, farm_id)[0]["kind"] == "follow_up"
    farm_service.record_outcome(user_id, first["intervention_id"], "improved")
    assert farm_service.list_reminders(user_id, farm_id) == []


def test_attribution_uses_same_crop_problem_and_minimum_samples(farm_db):
    user_id, farm_id = farm_db
    for _ in range(3):
        item = farm_service.create_recommendation(user_id, farm_id, None, "tomato", "early blight", f"Treatment A {_}")
        farm_service.acknowledge_intervention(user_id, item["intervention_id"])
        farm_service.record_outcome(user_id, item["intervention_id"], "improved")
    for _ in range(3):
        item = farm_service.create_recommendation(user_id, farm_id, None, "tomato", "early blight", f"Treatment B {_}")
        with db.get_connection() as conn:
            conn.execute("UPDATE interventions SET intervention_type='alternative' WHERE id=?", (item["intervention_id"],))
            conn.commit()
        farm_service.acknowledge_intervention(user_id, item["intervention_id"])
        farm_service.record_outcome(user_id, item["intervention_id"], "worsened")
    rationale = farm_service.build_rationale(user_id, farm_id, None, "tomato", "early blight", "applied")
    assert rationale["evidence_level"] == "tier_2"
    assert rationale["evidence"]["observed_difference"] == 1.0
    assert "causation" in " ".join(rationale["limitations"])


def test_attribution_excludes_mismatched_context_and_unknown(farm_db):
    user_id, farm_id = farm_db
    item = farm_service.create_recommendation(user_id, farm_id, None, "rice", "blast", "Treatment")
    farm_service.acknowledge_intervention(user_id, item["intervention_id"])
    farm_service.record_outcome(user_id, item["intervention_id"], "unknown")
    rationale = farm_service.build_rationale(user_id, farm_id, None, "tomato", "blast", "applied")
    assert rationale["evidence_level"] == "tier_0"
    assert rationale["evidence"]["intervention_cases"] == 0
