from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config import settings

DB_PATH = settings.db_path
EXPECTED_PREDICTION_COLUMNS = [
    "id",
    "timestamp",
    "input_data",
    "crop_prediction",
    "crop_confidence",
    "irrigation_prediction",
    "user_id",
]


def get_connection() -> sqlite3.Connection:
    """Create and return a SQLite connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate_predictions_table(conn: sqlite3.Connection) -> None:
    existing = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='predictions'"
    ).fetchone()

    if existing:
        cols = conn.execute("PRAGMA table_info(predictions)").fetchall()
        current_columns = [col[1] for col in cols]
        if current_columns != EXPECTED_PREDICTION_COLUMNS:
            backup_name = f"predictions_legacy_{int(datetime.now().timestamp())}"
            conn.execute(f"ALTER TABLE predictions RENAME TO {backup_name}")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    input_data TEXT NOT NULL,
                    crop_prediction TEXT,
                    crop_confidence REAL,
                    irrigation_prediction REAL,
                    user_id INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
                """
            )

            legacy_columns = set(current_columns)
            select_user_id = "NULL"
            if "user_id" in legacy_columns:
                select_user_id = "user_id"
            select_crop_confidence = "NULL"
            if "crop_confidence" in legacy_columns:
                select_crop_confidence = "crop_confidence"

            conn.execute(
                f"""
                INSERT INTO predictions (id, timestamp, input_data, crop_prediction, crop_confidence, irrigation_prediction, user_id)
                SELECT id, timestamp, input_data, crop_prediction, {select_crop_confidence}, irrigation_prediction, {select_user_id}
                FROM {backup_name}
                """
            )
            return

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            input_data TEXT NOT NULL,
            crop_prediction TEXT,
            crop_confidence REAL,
            irrigation_prediction REAL,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )


def init_db() -> None:
    """Create or migrate users and predictions tables."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'farmer')),
                created_at TEXT NOT NULL
            )
            """
        )

        _migrate_predictions_table(conn)
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS farms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                location TEXT,
                latitude REAL,
                longitude REAL,
                area REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS fields (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                crop TEXT,
                variety TEXT,
                planting_date TEXT,
                expected_harvest_date TEXT,
                season TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (farm_id) REFERENCES farms(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS farm_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                farm_id INTEGER NOT NULL,
                field_id INTEGER,
                event_type TEXT NOT NULL,
                event_date TEXT NOT NULL,
                crop TEXT,
                title TEXT NOT NULL,
                description TEXT,
                source TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (farm_id) REFERENCES farms(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS interventions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                farm_id INTEGER NOT NULL,
                field_id INTEGER,
                recommendation_event_id INTEGER,
                intervention_type TEXT NOT NULL,
                description TEXT NOT NULL,
                event_date TEXT NOT NULL,
                product TEXT,
                dosage TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                crop TEXT,
                problem TEXT,
                practice_group TEXT NOT NULL DEFAULT 'unknown',
                action_status TEXT NOT NULL DEFAULT 'recommended',
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (farm_id) REFERENCES farms(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                intervention_id INTEGER NOT NULL,
                outcome_date TEXT NOT NULL,
                status TEXT NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (intervention_id) REFERENCES interventions(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS translation_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                language TEXT NOT NULL CHECK(language IN ('hi','mr')),
                page TEXT NOT NULL DEFAULT '',
                reported_text TEXT NOT NULL,
                suggested_text TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','reviewed','resolved')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS ai_answer_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                rating TEXT NOT NULL CHECK(rating IN ('helpful','not_helpful')),
                category TEXT NOT NULL DEFAULT 'general',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_ai_answer_feedback_created ON ai_answer_feedback(created_at DESC);
            CREATE TABLE IF NOT EXISTS ai_chat_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                created_at_epoch REAL NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_ai_chat_requests_user_time ON ai_chat_requests(user_id, created_at_epoch);
            CREATE INDEX IF NOT EXISTS idx_farms_user ON farms(user_id);
            CREATE INDEX IF NOT EXISTS idx_fields_farm ON fields(farm_id);
            CREATE INDEX IF NOT EXISTS idx_events_farm_date ON farm_events(farm_id, event_date DESC);
            CREATE INDEX IF NOT EXISTS idx_interventions_farm ON interventions(farm_id);
            CREATE INDEX IF NOT EXISTS idx_outcomes_intervention ON outcomes(intervention_id);
            CREATE INDEX IF NOT EXISTS idx_translation_feedback_status ON translation_feedback(status, created_at DESC);
            """
        )
        intervention_columns = {row[1] for row in conn.execute("PRAGMA table_info(interventions)").fetchall()}
        if "practice_group" not in intervention_columns:
            conn.execute("ALTER TABLE interventions ADD COLUMN practice_group TEXT NOT NULL DEFAULT 'unknown'")
            conn.execute("UPDATE interventions SET practice_group='recommended' WHERE intervention_type='applied'")
        if "action_status" not in intervention_columns:
            conn.execute("ALTER TABLE interventions ADD COLUMN action_status TEXT NOT NULL DEFAULT 'recommended'")
            conn.execute("UPDATE interventions SET action_status=CASE WHEN intervention_type='applied' THEN 'applied' ELSE 'recommended' END")
        field_columns = {row[1] for row in conn.execute("PRAGMA table_info(fields)").fetchall()}
        if "area_ha" not in field_columns:
            conn.execute("ALTER TABLE fields ADD COLUMN area_ha REAL")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS soil_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                farm_id INTEGER NOT NULL,
                field_id INTEGER NOT NULL UNIQUE,
                start_date TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (farm_id) REFERENCES farms(id) ON DELETE CASCADE,
                FOREIGN KEY (field_id) REFERENCES fields(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS soil_plan_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                task_key TEXT NOT NULL,
                year_number INTEGER NOT NULL,
                season TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                due_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'planned' CHECK(status IN ('planned','completed','skipped')),
                notes TEXT NOT NULL DEFAULT '',
                completed_at TEXT,
                FOREIGN KEY (plan_id) REFERENCES soil_plans(id) ON DELETE CASCADE,
                UNIQUE(plan_id, task_key)
            );
            CREATE TABLE IF NOT EXISTS soil_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                farm_id INTEGER NOT NULL,
                field_id INTEGER NOT NULL,
                sample_date TEXT NOT NULL,
                organic_carbon_pct REAL NOT NULL,
                ph REAL,
                nitrogen REAL,
                phosphorus REAL,
                potassium REAL,
                nutrient_units TEXT NOT NULL DEFAULT '',
                lab_name TEXT NOT NULL DEFAULT '',
                evidence_reference TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (farm_id) REFERENCES farms(id) ON DELETE CASCADE,
                FOREIGN KEY (field_id) REFERENCES fields(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS regenerative_practices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                farm_id INTEGER NOT NULL,
                field_id INTEGER NOT NULL,
                practice_type TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT,
                area_ha REAL,
                evidence_reference TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (farm_id) REFERENCES farms(id) ON DELETE CASCADE,
                FOREIGN KEY (field_id) REFERENCES fields(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_soil_tests_field_date ON soil_tests(field_id, sample_date);
            CREATE INDEX IF NOT EXISTS idx_regenerative_practices_field_date ON regenerative_practices(field_id, start_date);
            """
        )
        soil_test_columns = {row[1] for row in conn.execute("PRAGMA table_info(soil_tests)").fetchall()}
        if "nutrient_units" not in soil_test_columns:
            conn.execute("ALTER TABLE soil_tests ADD COLUMN nutrient_units TEXT NOT NULL DEFAULT ''")
        conn.commit()


def create_user(name: str, email: str, password_hash: str, role: str) -> Dict[str, Any]:
    created_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO users (name, email, password, role, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, email.lower(), password_hash, role, created_at),
        )
        conn.commit()

        return {
            "id": int(cursor.lastrowid),
            "name": name,
            "email": email.lower(),
            "role": role,
            "created_at": created_at,
        }


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id, name, email, password, role, created_at FROM users WHERE email = ?",
            (email.lower(),),
        ).fetchone()

    if not row:
        return None

    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "password": row["password"],
        "role": row["role"],
        "created_at": row["created_at"],
    }


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id, name, email, role, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    if not row:
        return None

    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
        "created_at": row["created_at"],
    }


def get_user_count() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
    return int(row[0]) if row else 0


def insert_prediction(
    input_payload: Dict[str, Any],
    crop_prediction: Optional[str] = None,
    crop_confidence: Optional[float] = None,
    irrigation_prediction: Optional[float] = None,
    user_id: Optional[int] = None,
) -> int:
    """
    Insert a prediction record with timestamp, input JSON, and predictions.
    Returns inserted row id.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    input_json = json.dumps(input_payload, ensure_ascii=False)

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO predictions (
                timestamp,
                input_data,
                crop_prediction,
                crop_confidence,
                irrigation_prediction,
                user_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (timestamp, input_json, crop_prediction, crop_confidence, irrigation_prediction, user_id),
        )
        conn.commit()
        return int(cursor.lastrowid)


def _get_predictions(limit: int = 20, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    query = """
        SELECT id, timestamp, input_data, crop_prediction, crop_confidence, irrigation_prediction, user_id
        FROM predictions
    """
    params: List[Any] = []

    if user_id is not None:
        query += " WHERE user_id = ?"
        params.append(user_id)

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, tuple(params)).fetchall()

    results: List[Dict[str, Any]] = []
    for row in rows:
        input_data: Any = row["input_data"]
        try:
            input_data = json.loads(input_data)
        except (TypeError, json.JSONDecodeError):
            pass

        results.append(
            {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "input_data": input_data,
                "crop_prediction": row["crop_prediction"],
                "crop_confidence": row["crop_confidence"],
                "irrigation_prediction": row["irrigation_prediction"],
                "user_id": row["user_id"],
            }
        )

    return results


def get_recent_predictions(limit: int = 20) -> List[Dict[str, Any]]:
    return _get_predictions(limit=limit, user_id=None)


def get_recent_predictions_for_user(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    return _get_predictions(limit=limit, user_id=user_id)


def get_prediction_count() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()
    return int(row[0]) if row else 0


def get_usage_analytics(days: int = 30) -> Dict[str, Any]:
    """Return aggregate prediction activity without exposing user identifiers."""
    days = max(1, min(int(days), 90))
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT date(timestamp) AS day,
                      COUNT(DISTINCT user_id) AS active_users,
                      SUM(CASE WHEN crop_prediction IS NOT NULL AND crop_prediction != '' THEN 1 ELSE 0 END) AS crop_usage,
                      SUM(CASE WHEN irrigation_prediction IS NOT NULL THEN 1 ELSE 0 END) AS irrigation_usage
               FROM predictions
               WHERE timestamp >= datetime('now', ?)
               GROUP BY date(timestamp)
               ORDER BY day""",
            (f"-{days} days",),
        ).fetchall()
        active_users = conn.execute(
            """SELECT COUNT(DISTINCT user_id) FROM predictions
               WHERE user_id IS NOT NULL AND timestamp >= datetime('now', '-7 days')"""
        ).fetchone()[0]
        active_users_30d = conn.execute(
            """SELECT COUNT(DISTINCT user_id) FROM predictions
               WHERE user_id IS NOT NULL AND timestamp >= datetime('now', '-30 days')"""
        ).fetchone()[0]

    daily = [dict(row) for row in rows]
    return {
        "days": daily,
        "active_users_7d": int(active_users or 0),
        "active_users_30d": int(active_users_30d or 0),
        "crop_usage_30d": sum(int(row["crop_usage"] or 0) for row in daily),
        "irrigation_usage_30d": sum(int(row["irrigation_usage"] or 0) for row in daily),
    }


def create_translation_feedback(
    user_id: int, language: str, page: str, reported_text: str, suggested_text: str, note: str
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO translation_feedback
               (user_id, language, page, reported_text, suggested_text, note, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?)""",
            (user_id, language, page, reported_text, suggested_text, note, now, now),
        )
        feedback_id = int(cursor.lastrowid)
        conn.commit()
    return {
        "id": feedback_id,
        "user_id": user_id,
        "language": language,
        "page": page,
        "reported_text": reported_text,
        "suggested_text": suggested_text,
        "note": note,
        "status": "open",
        "created_at": now,
        "updated_at": now,
    }


def list_translation_feedback(status: str | None = None, limit: int = 100) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit), 250))
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        if status in {"open", "reviewed", "resolved"}:
            rows = conn.execute(
                """SELECT f.*, u.name AS user_name FROM translation_feedback f
                   JOIN users u ON u.id=f.user_id WHERE f.status=?
                   ORDER BY f.created_at DESC LIMIT ?""",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT f.*, u.name AS user_name FROM translation_feedback f
                   JOIN users u ON u.id=f.user_id ORDER BY f.created_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
    return [dict(row) for row in rows]


def update_translation_feedback_status(feedback_id: int, status: str) -> bool:
    if status not in {"open", "reviewed", "resolved"}:
        raise ValueError("Invalid translation feedback status.")
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE translation_feedback SET status=?, updated_at=? WHERE id=?",
            (status, now, feedback_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def create_ai_answer_feedback(user_id: int, rating: str, category: str = "general") -> Dict[str, Any]:
    if rating not in {"helpful", "not_helpful"}:
        raise ValueError("Invalid AI answer rating.")
    allowed_categories = {"general", "accuracy", "clarity", "language", "safety"}
    if category not in allowed_categories:
        raise ValueError("Invalid AI answer feedback category.")
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO ai_answer_feedback (user_id,rating,category,created_at) VALUES (?,?,?,?)",
            (user_id, rating, category, now),
        )
        conn.commit()
        return {"id": int(cursor.lastrowid), "rating": rating, "category": category, "created_at": now}


def list_ai_answer_feedback(limit: int = 100) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit), 250))
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT f.id,f.rating,f.category,f.created_at,u.name AS user_name
               FROM ai_answer_feedback f JOIN users u ON u.id=f.user_id
               ORDER BY f.created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def reserve_ai_chat_request(user_id: int, limit: int = 10, window_seconds: int = 60) -> int:
    now = time.time()
    cutoff = now - window_seconds
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM ai_chat_requests WHERE created_at_epoch < ?", (cutoff,))
        count, oldest = conn.execute(
            "SELECT COUNT(*), MIN(created_at_epoch) FROM ai_chat_requests WHERE user_id=? AND created_at_epoch>=?",
            (user_id, cutoff),
        ).fetchone()
        if count >= limit:
            conn.rollback()
            return max(1, int(window_seconds - (now - oldest)))
        conn.execute("INSERT INTO ai_chat_requests (user_id,created_at_epoch) VALUES (?,?)", (user_id, now))
        conn.commit()
    return 0
