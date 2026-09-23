from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from database.db import get_connection
from config import settings

OUTCOME_STATUSES = {"improved", "no_change", "worsened", "unknown"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row(row: sqlite3.Row | None) -> Dict[str, Any] | None:
    return dict(row) if row else None


def _owned_farm(conn: sqlite3.Connection, user_id: int, farm_id: int) -> bool:
    return conn.execute("SELECT 1 FROM farms WHERE id = ? AND user_id = ?", (farm_id, user_id)).fetchone() is not None


def _owned_field(conn: sqlite3.Connection, user_id: int, farm_id: int, field_id: Optional[int]) -> bool:
    if field_id is None:
        return True
    return conn.execute(
        "SELECT 1 FROM fields WHERE id = ? AND farm_id = ? AND user_id = ?",
        (field_id, farm_id, user_id),
    ).fetchone() is not None


def list_farms(user_id: int) -> list[Dict[str, Any]]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        farms = [_row(row) for row in conn.execute("SELECT * FROM farms WHERE user_id = ? ORDER BY id", (user_id,))]
        for farm in farms:
            farm["fields"] = [_row(row) for row in conn.execute("SELECT * FROM fields WHERE farm_id = ? ORDER BY id", (farm["id"],))]
        return farms


def create_farm(user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValueError("Farm name is required.")
    now = _now()
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO farms (user_id,name,location,latitude,longitude,area,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (user_id, name, payload.get("location"), payload.get("latitude"), payload.get("longitude"), payload.get("area"), now, now),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "user_id": user_id, "name": name, "location": payload.get("location"), "created_at": now, "updated_at": now, "fields": []}


def create_field(user_id: int, farm_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValueError("Field name is required.")
    now = _now()
    with get_connection() as conn:
        if not _owned_farm(conn, user_id, farm_id):
            raise LookupError("Farm not found.")
        cursor = conn.execute(
            "INSERT INTO fields (farm_id,user_id,name,crop,variety,planting_date,expected_harvest_date,season,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (farm_id, user_id, name, payload.get("crop"), payload.get("variety"), payload.get("planting_date"), payload.get("expected_harvest_date"), payload.get("season"), "active", now, now),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "farm_id": farm_id, "user_id": user_id, "name": name, "crop": payload.get("crop"), "status": "active", "created_at": now, "updated_at": now}


def create_recommendation(user_id: int, farm_id: int, field_id: Optional[int], crop: str, problem: str = "", description: str = "") -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        if not _owned_farm(conn, user_id, farm_id) or not _owned_field(conn, user_id, farm_id, field_id):
            raise LookupError("Farm or field not found.")
        recent = conn.execute(
            "SELECT id FROM interventions WHERE user_id=? AND farm_id=? AND (field_id IS ? OR field_id=?) AND crop=? AND description=? AND intervention_type='recommended' AND created_at >= ?",
            (user_id, farm_id, field_id, field_id, crop, description or f"Review the {crop} recommendation.", (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()),
        ).fetchone()
        if recent:
            return {"intervention_id": recent[0], "duplicate": True}
        now = _now()
        metadata = json.dumps({"problem": problem, "reminder_hours": settings.intervention_reminder_hours})
        event = conn.execute(
            "INSERT INTO farm_events (user_id,farm_id,field_id,event_type,event_date,crop,title,description,source,metadata_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (user_id, farm_id, field_id, "recommendation", now, crop, "Recommendation created", description, "advisory", metadata, now),
        )
        intervention = conn.execute(
            "INSERT INTO interventions (user_id,farm_id,field_id,recommendation_event_id,intervention_type,description,event_date,created_at,crop,problem) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (user_id, farm_id, field_id, event.lastrowid, "recommended", description or f"Review the {crop} recommendation.", now, now, crop, problem),
        )
        conn.commit()
        return {"intervention_id": intervention.lastrowid, "event_id": event.lastrowid, "duplicate": False}


def _intervention(conn: sqlite3.Connection, user_id: int, intervention_id: int) -> sqlite3.Row | None:
    conn.row_factory = sqlite3.Row
    return conn.execute("SELECT * FROM interventions WHERE id=? AND user_id=?", (intervention_id, user_id)).fetchone()


def list_reminders(user_id: int, farm_id: int) -> list[Dict[str, Any]]:
    with get_connection() as conn:
        if not _owned_farm(conn, user_id, farm_id):
            raise LookupError("Farm not found.")
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT i.*, f.name AS farm_name, fld.name AS field_name, o.id AS outcome_id
               FROM interventions i JOIN farms f ON f.id=i.farm_id
               LEFT JOIN fields fld ON fld.id=i.field_id
               LEFT JOIN outcomes o ON o.intervention_id=i.id
               WHERE i.user_id=? AND i.farm_id=? ORDER BY i.id DESC""", (user_id, farm_id)
        ).fetchall()
        reminders = []
        now = datetime.now(timezone.utc)
        for row in rows:
            item = dict(row)
            if item["outcome_id"]:
                continue
            created = datetime.fromisoformat(item["created_at"])
            if item["intervention_type"] == "recommended":
                due = created + timedelta(hours=settings.intervention_reminder_hours)
                item.update({"kind": "action", "title": "Have you taken this action?", "due": due.isoformat()})
            elif item["intervention_type"] == "applied":
                due = created + timedelta(hours=settings.follow_up_reminder_hours)
                item.update({"kind": "follow_up", "title": "How is the crop responding?", "due": due.isoformat()})
            else:
                continue
            item["due_now"] = now >= due
            reminders.append(item)
        return reminders


def acknowledge_intervention(user_id: int, intervention_id: int, notes: str = "") -> Dict[str, Any]:
    with get_connection() as conn:
        row = _intervention(conn, user_id, intervention_id)
        if not row:
            raise LookupError("Intervention not found.")
        if row["intervention_type"] != "recommended":
            return dict(row)
        now = _now()
        conn.execute("UPDATE interventions SET intervention_type='applied', event_date=?, notes=? WHERE id=? AND user_id=?", (now, notes, intervention_id, user_id))
        conn.execute("INSERT INTO farm_events (user_id,farm_id,field_id,event_type,event_date,crop,title,description,source,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)", (user_id,row["farm_id"],row["field_id"],"intervention",now,row["crop"],"Action recorded",row["description"],"farmer",now))
        conn.commit()
        return {"id": intervention_id, "status": "applied", "follow_up_hours": settings.follow_up_reminder_hours}


def get_follow_up(user_id: int, intervention_id: int) -> Dict[str, Any]:
    with get_connection() as conn:
        row = _intervention(conn, user_id, intervention_id)
        if not row:
            raise LookupError("Intervention not found.")
        if row["intervention_type"] != "applied":
            raise ValueError("Follow-up is not available until the action is recorded.")
        return {"intervention_id": intervention_id, "title": "How is the crop responding?", "statuses": sorted(OUTCOME_STATUSES)}


def record_outcome(user_id: int, intervention_id: int, status: str, notes: str = "") -> Dict[str, Any]:
    if status not in OUTCOME_STATUSES:
        raise ValueError("Status must be improved, no_change, worsened, or unknown.")
    with get_connection() as conn:
        row = _intervention(conn, user_id, intervention_id)
        if not row:
            raise LookupError("Intervention not found.")
        existing = conn.execute("SELECT id FROM outcomes WHERE intervention_id=? AND user_id=?", (intervention_id, user_id)).fetchone()
        if existing:
            raise ValueError("An outcome has already been recorded for this intervention.")
        now = _now()
        outcome = conn.execute("INSERT INTO outcomes (user_id,intervention_id,outcome_date,status,notes,created_at) VALUES (?,?,?,?,?,?)", (user_id,intervention_id,now,status,notes,now))
        conn.execute("INSERT INTO farm_events (user_id,farm_id,field_id,event_type,event_date,crop,title,description,source,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)", (user_id,row["farm_id"],row["field_id"],"outcome",now,row["crop"],"Outcome recorded",status,"farmer",now))
        conn.commit()
        return {"id": outcome.lastrowid, "status": status}


def build_rationale(user_id: int, farm_id: int, field_id: Optional[int], crop: str, problem: str = "", intervention_type: str = "") -> Dict[str, Any]:
    with get_connection() as conn:
        if not _owned_farm(conn, user_id, farm_id) or not _owned_field(conn, user_id, farm_id, field_id):
            raise LookupError("Farm or field not found.")
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT i.id, i.intervention_type, i.crop, i.problem, i.farm_id, i.field_id, o.status
               FROM interventions i LEFT JOIN outcomes o ON o.intervention_id=i.id
               WHERE i.user_id=? AND i.farm_id=? AND (i.field_id IS ? OR i.field_id=?) AND i.crop=?
                 AND (i.problem=? OR (?='' AND (i.problem IS NULL OR i.problem='')))""",
            (user_id, farm_id, field_id, field_id, crop, problem, problem),
        ).fetchall()
    target = intervention_type or (rows[0]["intervention_type"] if rows else "")
    target_rows = [r for r in rows if r["intervention_type"] == target and r["status"] in {"improved", "no_change", "worsened"}]
    comparison_rows = [r for r in rows if r["intervention_type"] != target and r["status"] in {"improved", "no_change", "worsened"}]
    target_improved = sum(r["status"] == "improved" for r in target_rows)
    comparison_improved = sum(r["status"] == "improved" for r in comparison_rows)
    evidence = "tier_0"
    match_level = "same_field_crop_problem" if field_id is not None else "same_farm_crop_problem"
    limitations = ["Observational evidence; not proof of causation.", "Weather history was not available for this comparison."]
    if len(target_rows) >= settings.outcome_min_evidence_cases:
        evidence = "tier_1"
    if len(target_rows) >= settings.outcome_min_evidence_cases and len(comparison_rows) >= settings.outcome_min_evidence_cases:
        evidence = "tier_2"
    result: Dict[str, Any] = {
        "recommendation": crop,
        "target_context": {"crop": crop, "problem": problem or None, "farm_id": farm_id, "field_id": field_id},
        "evidence_level": evidence,
        "evidence_strength": {"tier_0": "Insufficient", "tier_1": "Descriptive", "tier_2": "Moderate"}[evidence],
        "match_level": match_level,
        "limitations": limitations,
    }
    if evidence == "tier_2":
        intervention_rate = target_improved / len(target_rows)
        comparison_rate = comparison_improved / len(comparison_rows)
        result["evidence"] = {
            "intervention_improvement_rate": intervention_rate,
            "comparison_improvement_rate": comparison_rate,
            "observed_difference": intervention_rate - comparison_rate,
            "intervention_cases": len(target_rows),
            "comparison_cases": len(comparison_rows),
        }
        result["reason"] = "Comparable cases with the same crop and problem provide observational support for this recommendation."
    else:
        result["evidence"] = {"intervention_cases": len(target_rows), "comparison_cases": len(comparison_rows)}
        result["reason"] = "Not enough comparable outcomes to estimate intervention effect."
    return result
