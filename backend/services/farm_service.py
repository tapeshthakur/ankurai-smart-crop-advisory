from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from database.db import get_connection
from config import settings

OUTCOME_STATUSES = {"improved", "no_change", "worsened", "unknown"}
PRACTICE_GROUPS = {"recommended", "usual_practice"}


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
    area_ha = payload.get("area_ha")
    if area_ha not in (None, ""):
        try:
            area_ha = float(area_ha)
        except (TypeError, ValueError):
            raise ValueError("Field area must be a positive number of hectares.") from None
        if not math.isfinite(area_ha) or area_ha <= 0:
            raise ValueError("Field area must be a positive number of hectares.")
    else:
        area_ha = None
    now = _now()
    with get_connection() as conn:
        if not _owned_farm(conn, user_id, farm_id):
            raise LookupError("Farm not found.")
        cursor = conn.execute(
            "INSERT INTO fields (farm_id,user_id,name,crop,variety,planting_date,expected_harvest_date,season,status,area_ha,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (farm_id, user_id, name, payload.get("crop"), payload.get("variety"), payload.get("planting_date"), payload.get("expected_harvest_date"), payload.get("season"), "active", area_ha, now, now),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "farm_id": farm_id, "user_id": user_id, "name": name, "crop": payload.get("crop"), "area_ha": area_ha, "status": "active", "created_at": now, "updated_at": now}


def update_field_area(user_id: int, farm_id: int, field_id: int, raw_area: Any) -> Dict[str, Any]:
    if raw_area in (None, ""):
        area_ha = None
    else:
        try:
            area_ha = float(raw_area)
        except (TypeError, ValueError):
            raise ValueError("Field area must be a positive number of hectares.") from None
        if not math.isfinite(area_ha) or area_ha <= 0:
            raise ValueError("Field area must be a positive number of hectares.")
    with get_connection() as conn:
        if not _owned_farm(conn, user_id, farm_id) or not _owned_field(conn, user_id, farm_id, field_id):
            raise LookupError("Farm field not found.")
        conn.execute("UPDATE fields SET area_ha=?,updated_at=? WHERE id=? AND farm_id=? AND user_id=?", (area_ha, _now(), field_id, farm_id, user_id))
        conn.commit()
        conn.row_factory = sqlite3.Row
        return dict(conn.execute("SELECT * FROM fields WHERE id=?", (field_id,)).fetchone())


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
            "INSERT INTO interventions (user_id,farm_id,field_id,recommendation_event_id,intervention_type,description,event_date,created_at,crop,problem,practice_group,action_status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (user_id, farm_id, field_id, event.lastrowid, "recommended", description or f"Review the {crop} recommendation.", now, now, crop, problem, "recommended", "recommended"),
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
            if item["action_status"] == "recommended":
                due = created + timedelta(hours=settings.intervention_reminder_hours)
                item.update({"kind": "action", "title": "Have you taken this action?", "due": due.isoformat()})
            elif item["action_status"] == "applied":
                due = created + timedelta(hours=settings.follow_up_reminder_hours)
                item.update({"kind": "follow_up", "title": "How is the crop responding?", "due": due.isoformat()})
            else:
                continue
            item["due_now"] = now >= due
            reminders.append(item)
        return reminders


def acknowledge_intervention(user_id: int, intervention_id: int, notes: str = "", practice_group: str = "recommended") -> Dict[str, Any]:
    if practice_group not in PRACTICE_GROUPS:
        raise ValueError("Choose the recommendation or usual practice group.")
    with get_connection() as conn:
        row = _intervention(conn, user_id, intervention_id)
        if not row:
            raise LookupError("Intervention not found.")
        if row["action_status"] != "recommended":
            return dict(row)
        now = _now()
        conn.execute("UPDATE interventions SET intervention_type='applied', action_status='applied', practice_group=?, event_date=?, notes=? WHERE id=? AND user_id=?", (practice_group, now, notes, intervention_id, user_id))
        conn.execute("INSERT INTO farm_events (user_id,farm_id,field_id,event_type,event_date,crop,title,description,source,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)", (user_id,row["farm_id"],row["field_id"],"intervention",now,row["crop"],"Action recorded",row["description"],"farmer",now))
        conn.commit()
        return {"id": intervention_id, "status": "applied", "follow_up_hours": settings.follow_up_reminder_hours}


def get_follow_up(user_id: int, intervention_id: int) -> Dict[str, Any]:
    with get_connection() as conn:
        row = _intervention(conn, user_id, intervention_id)
        if not row:
            raise LookupError("Intervention not found.")
        if row["action_status"] != "applied":
            raise ValueError("Follow-up is not available until the action is recorded.")
        return {"intervention_id": intervention_id, "title": "How is the crop responding?", "statuses": sorted(OUTCOME_STATUSES)}


def record_outcome(user_id: int, intervention_id: int, status: str, notes: str = "") -> Dict[str, Any]:
    if status not in OUTCOME_STATUSES:
        raise ValueError("Status must be improved, no_change, worsened, or unknown.")
    with get_connection() as conn:
        row = _intervention(conn, user_id, intervention_id)
        if not row:
            raise LookupError("Intervention not found.")
        if row["action_status"] != "applied":
            raise ValueError("Record the action before adding an outcome.")
        existing = conn.execute("SELECT id FROM outcomes WHERE intervention_id=? AND user_id=?", (intervention_id, user_id)).fetchone()
        if existing:
            raise ValueError("An outcome has already been recorded for this intervention.")
        now = _now()
        outcome = conn.execute("INSERT INTO outcomes (user_id,intervention_id,outcome_date,status,notes,created_at) VALUES (?,?,?,?,?,?)", (user_id,intervention_id,now,status,notes,now))
        conn.execute("INSERT INTO farm_events (user_id,farm_id,field_id,event_type,event_date,crop,title,description,source,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)", (user_id,row["farm_id"],row["field_id"],"outcome",now,row["crop"],"Outcome recorded",status,"farmer",now))
        conn.commit()
        return {"id": outcome.lastrowid, "status": status}


def build_rationale(user_id: int, farm_id: int, field_id: Optional[int], crop: str, problem: str = "", practice_group: str = "") -> Dict[str, Any]:
    with get_connection() as conn:
        if not _owned_farm(conn, user_id, farm_id) or not _owned_field(conn, user_id, farm_id, field_id):
            raise LookupError("Farm or field not found.")
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT i.id, i.practice_group, i.crop, i.problem, i.farm_id, i.field_id, o.status
               FROM interventions i LEFT JOIN outcomes o ON o.intervention_id=i.id
               WHERE i.user_id=? AND i.farm_id=? AND (i.field_id IS ? OR i.field_id=?) AND i.crop=?
                 AND (i.problem=? OR (?='' AND (i.problem IS NULL OR i.problem='')))""",
            (user_id, farm_id, field_id, field_id, crop, problem, problem),
        ).fetchall()
    target = practice_group if practice_group in PRACTICE_GROUPS else "recommended"
    comparison_group = "usual_practice" if target == "recommended" else "recommended"
    target_rows = [r for r in rows if r["practice_group"] == target and r["status"] in {"improved", "no_change", "worsened"}]
    comparison_rows = [r for r in rows if r["practice_group"] == comparison_group and r["status"] in {"improved", "no_change", "worsened"}]
    target_improved = sum(r["status"] == "improved" for r in target_rows)
    comparison_improved = sum(r["status"] == "improved" for r in comparison_rows)
    evidence = "tier_0"
    match_level = "same_field_crop_problem" if field_id is not None else "same_farm_crop_problem"
    limitations = ["Observational evidence; not proof of causation.", "Weather was not recorded consistently, so results are not weather-adjusted."]
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
    enough_target = len(target_rows) >= settings.outcome_min_evidence_cases
    enough_comparison = len(comparison_rows) >= settings.outcome_min_evidence_cases
    result["evidence"] = {
        "intervention_cases": len(target_rows),
        "comparison_cases": len(comparison_rows),
        "intervention_improved": target_improved,
        "comparison_improved": comparison_improved,
        "minimum_cases": settings.outcome_min_evidence_cases,
        "intervention_improvement_rate": target_improved / len(target_rows) if enough_target else None,
        "comparison_improvement_rate": comparison_improved / len(comparison_rows) if enough_comparison else None,
        "intervention_group": target,
        "comparison_group": comparison_group,
    }
    if enough_target and enough_comparison:
        intervention_rate = target_improved / len(target_rows)
        comparison_rate = comparison_improved / len(comparison_rows)
        result["evidence"]["observed_difference"] = intervention_rate - comparison_rate
        result["reason_code"] = "comparison_ready"
        result["reason"] = "Observed improvement rates are {{recommended_rate}} for the selected group and {{usual_rate}} for usual practice; this is observational, not causal evidence.".replace("{{recommended_rate}}", f"{intervention_rate:.0%}").replace("{{usual_rate}}", f"{comparison_rate:.0%}")
    elif enough_target:
        needed = max(0, settings.outcome_min_evidence_cases - len(comparison_rows))
        result["reason_code"] = "comparison_pending"
        result["reason"] = f"Recorded {len(target_rows)} recommendation outcomes. Add {needed} usual-practice comparison outcome(s) for a side-by-side estimate."
    else:
        needed = max(0, settings.outcome_min_evidence_cases - len(target_rows))
        result["reason_code"] = "collecting"
        result["reason"] = f"Record {needed} more recommendation outcome(s) to meet the minimum of {settings.outcome_min_evidence_cases}; usual-practice outcomes are counted separately."
    return result
