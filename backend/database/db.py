from __future__ import annotations

import json
import sqlite3
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
            CREATE INDEX IF NOT EXISTS idx_farms_user ON farms(user_id);
            CREATE INDEX IF NOT EXISTS idx_fields_farm ON fields(farm_id);
            CREATE INDEX IF NOT EXISTS idx_events_farm_date ON farm_events(farm_id, event_date DESC);
            CREATE INDEX IF NOT EXISTS idx_interventions_farm ON interventions(farm_id);
            CREATE INDEX IF NOT EXISTS idx_outcomes_intervention ON outcomes(intervention_id);
            """
        )
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
