from database import db


def test_usage_analytics_returns_aggregates_without_user_ids(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "usage.db")
    db.init_db()
    first = db.create_user("Farmer One", "one@example.test", "hash", "farmer")
    second = db.create_user("Farmer Two", "two@example.test", "hash", "farmer")
    db.insert_prediction({"N": 80}, "rice", 0.8, None, first["id"])
    db.insert_prediction({"N": 80}, None, None, 12.5, first["id"])
    db.insert_prediction({"N": 80}, "wheat", 0.7, None, second["id"])

    result = db.get_usage_analytics()

    assert result["active_users_7d"] == 2
    assert result["active_users_30d"] == 2
    assert result["crop_usage_30d"] == 2
    assert result["irrigation_usage_30d"] == 1
    assert all("user_id" not in day for day in result["days"])
    assert all("email" not in day for day in result["days"])
