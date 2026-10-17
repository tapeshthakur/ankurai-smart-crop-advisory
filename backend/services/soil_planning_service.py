from __future__ import annotations

import json
import math
import sqlite3
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict

from database.db import get_connection


PRACTICE_TYPES = {
    "cover_crop",
    "crop_rotation",
    "reduced_tillage",
    "residue_retention",
    "compost",
    "agroforestry",
    "nutrient_management",
    "other",
}
TASK_STATUSES = {"planned", "completed", "skipped"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _date(value: Any, label: str) -> str:
    try:
        return date.fromisoformat(str(value)).isoformat()
    except (TypeError, ValueError):
        raise ValueError(f"{label} must use YYYY-MM-DD format.") from None


def _optional_number(payload: Dict[str, Any], key: str, low: float, high: float | None = None) -> float | None:
    raw = payload.get(key)
    if raw in (None, ""):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be a number.") from None
    if not math.isfinite(value) or value < low or (high is not None and value > high):
        bound = f"between {low} and {high}" if high is not None else f"at least {low}"
        raise ValueError(f"{key} must be {bound}.")
    return value


def _owned_field(conn: sqlite3.Connection, user_id: int, farm_id: int, field_id: int) -> sqlite3.Row | None:
    conn.row_factory = sqlite3.Row
    return conn.execute(
        "SELECT * FROM fields WHERE id=? AND farm_id=? AND user_id=?",
        (field_id, farm_id, user_id),
    ).fetchone()


def _build_tasks(plan: Dict[str, Any], start_date: str) -> list[Dict[str, Any]]:
    years = plan.get("plan")
    if not isinstance(years, list) or not years:
        raise ValueError("A soil plan with at least one year is required.")
    if len(years) > 5:
        raise ValueError("A soil restoration plan can cover at most five years.")

    start = date.fromisoformat(start_date)
    tasks: list[Dict[str, Any]] = []
    for index, year_plan in enumerate(years, start=1):
        if not isinstance(year_plan, dict):
            raise ValueError("Each soil plan year must be an object.")
        year = int(year_plan.get("year", index))
        if year < 1 or year > 5:
            raise ValueError("Plan years must be between 1 and 5.")
        schedules = (
            ("pre_sowing", 0),
            ("at_sowing", 30),
            ("post_harvest", 180),
        )

        def add(category: str, title: str, description: str, season: str, offset: int, key_index: int = 0) -> None:
            if description.strip():
                due = start + timedelta(days=365 * (year - 1) + offset)
                tasks.append({
                    "task_key": f"y{year}:{category}:{key_index}",
                    "year_number": year,
                    "season": season,
                    "category": category,
                    "title": title,
                    "description": description.strip(),
                    "due_date": due.isoformat(),
                })

        add("soil_test", "Record a soil test", "Repeat a soil test in the same season before changing amendment rates.", "Before sowing", schedules[0][1])
        add("rotation", "Review crop rotation", str(year_plan.get("rotation", "")), "Before sowing", schedules[0][1])
        add("microbial", "Review microbial support", str(year_plan.get("microbial_support", "")), "At sowing", schedules[1][1])
        add("cover_crop", "Plan cover and residue", str(year_plan.get("cover_crop", "")), "After harvest", schedules[2][1])
        practices = year_plan.get("practices") or []
        if isinstance(practices, list):
            for practice_index, description in enumerate(practices):
                add("field_practice", "Complete planned soil practice", str(description), "After harvest", schedules[2][1], practice_index)
        add("review", "Review the season", str(year_plan.get("focus", "Review soil-test and field records.")), "After harvest", schedules[2][1])
    return tasks


def save_soil_plan(user_id: int, farm_id: int, field_id: int, start_date: Any, plan: Dict[str, Any]) -> Dict[str, Any]:
    normalized_start = _date(start_date or date.today().isoformat(), "start_date")
    if not isinstance(plan, dict):
        raise ValueError("plan must be an advisory soil-restoration object.")
    tasks = _build_tasks(plan, normalized_start)
    now = _now()
    with get_connection() as conn:
        if not _owned_field(conn, user_id, farm_id, field_id):
            raise LookupError("Farm field not found.")
        conn.execute(
            """INSERT INTO soil_plans (user_id,farm_id,field_id,start_date,plan_json,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(field_id) DO UPDATE SET start_date=excluded.start_date, plan_json=excluded.plan_json, updated_at=excluded.updated_at""",
            (user_id, farm_id, field_id, normalized_start, json.dumps(plan), now, now),
        )
        row = conn.execute("SELECT id FROM soil_plans WHERE field_id=? AND user_id=?", (field_id, user_id)).fetchone()
        if not row:
            raise LookupError("Farm field not found.")
        plan_id = int(row[0])
        for task in tasks:
            conn.execute(
                """INSERT INTO soil_plan_tasks (plan_id,task_key,year_number,season,category,title,description,due_date)
                   VALUES (?,?,?,?,?,?,?,?)
                   ON CONFLICT(plan_id,task_key) DO UPDATE SET season=excluded.season,category=excluded.category,title=excluded.title,description=excluded.description,due_date=excluded.due_date""",
                (plan_id, task["task_key"], task["year_number"], task["season"], task["category"], task["title"], task["description"], task["due_date"]),
            )
        conn.commit()
    return get_soil_plan(user_id, farm_id, field_id)


def get_soil_plan(user_id: int, farm_id: int, field_id: int) -> Dict[str, Any]:
    with get_connection() as conn:
        if not _owned_field(conn, user_id, farm_id, field_id):
            raise LookupError("Farm field not found.")
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM soil_plans WHERE user_id=? AND farm_id=? AND field_id=?", (user_id, farm_id, field_id)).fetchone()
        if not row:
            return {"plan": None, "tasks": []}
        tasks = [dict(task) for task in conn.execute("SELECT * FROM soil_plan_tasks WHERE plan_id=? ORDER BY year_number,due_date,id", (row["id"],))]
        return {"plan": {**dict(row), "plan": json.loads(row["plan_json"])}, "tasks": tasks}


def update_soil_task(user_id: int, task_id: int, status: str, notes: str = "") -> Dict[str, Any]:
    if status not in TASK_STATUSES:
        raise ValueError("status must be planned, completed, or skipped.")
    if len(notes) > 1500:
        raise ValueError("Task notes must be 1500 characters or fewer.")
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        task = conn.execute(
            """SELECT t.id FROM soil_plan_tasks t JOIN soil_plans p ON p.id=t.plan_id
               WHERE t.id=? AND p.user_id=?""",
            (task_id, user_id),
        ).fetchone()
        if not task:
            raise LookupError("Soil plan task not found.")
        completed_at = _now() if status == "completed" else None
        conn.execute("UPDATE soil_plan_tasks SET status=?,notes=?,completed_at=? WHERE id=?", (status, notes.strip(), completed_at, task_id))
        conn.commit()
        return dict(conn.execute("SELECT * FROM soil_plan_tasks WHERE id=?", (task_id,)).fetchone())


def add_soil_test(user_id: int, farm_id: int, field_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    sample_date = _date(payload.get("sample_date"), "sample_date")
    organic_carbon = _optional_number(payload, "organic_carbon_pct", 0, 100)
    if organic_carbon is None:
        raise ValueError("organic_carbon_pct is required.")
    ph = _optional_number(payload, "ph", 0, 14)
    nitrogen = _optional_number(payload, "nitrogen", 0)
    phosphorus = _optional_number(payload, "phosphorus", 0)
    potassium = _optional_number(payload, "potassium", 0)
    nutrient_units = str(payload.get("nutrient_units", "")).strip()
    if any(value is not None for value in (nitrogen, phosphorus, potassium)) and nutrient_units not in {"mg/kg", "kg/ha", "ppm", "%"}:
        raise ValueError("Choose the units shown on the laboratory report for NPK values.")
    lab_name = str(payload.get("lab_name", "")).strip()
    evidence = str(payload.get("evidence_reference", "")).strip()
    notes = str(payload.get("notes", "")).strip()
    if len(lab_name) > 200 or len(evidence) > 500 or len(notes) > 1500:
        raise ValueError("Lab name, evidence reference, or notes exceed the allowed length.")
    with get_connection() as conn:
        if not _owned_field(conn, user_id, farm_id, field_id):
            raise LookupError("Farm field not found.")
        cursor = conn.execute(
            """INSERT INTO soil_tests (user_id,farm_id,field_id,sample_date,organic_carbon_pct,ph,nitrogen,phosphorus,potassium,nutrient_units,lab_name,evidence_reference,notes,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, farm_id, field_id, sample_date, organic_carbon, ph, nitrogen, phosphorus, potassium, nutrient_units, lab_name, evidence, notes, _now()),
        )
        conn.commit()
        conn.row_factory = sqlite3.Row
        return dict(conn.execute("SELECT * FROM soil_tests WHERE id=?", (cursor.lastrowid,)).fetchone())


def update_soil_test(user_id: int, record_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    sample_date = _date(payload.get("sample_date"), "sample_date")
    organic_carbon = _optional_number(payload, "organic_carbon_pct", 0, 100)
    if organic_carbon is None:
        raise ValueError("organic_carbon_pct is required.")
    ph = _optional_number(payload, "ph", 0, 14)
    nutrients = [_optional_number(payload, key, 0) for key in ("nitrogen", "phosphorus", "potassium")]
    nutrient_units = str(payload.get("nutrient_units", "")).strip()
    if any(value is not None for value in nutrients) and nutrient_units not in {"mg/kg", "kg/ha", "ppm", "%"}:
        raise ValueError("Choose the units shown on the laboratory report for NPK values.")
    lab_name = str(payload.get("lab_name", "")).strip()
    evidence = str(payload.get("evidence_reference", "")).strip()
    notes = str(payload.get("notes", "")).strip()
    if len(lab_name) > 200 or len(evidence) > 500 or len(notes) > 1500:
        raise ValueError("Lab name, evidence reference, or notes exceed the allowed length.")
    with get_connection() as conn:
        cursor = conn.execute(
            """UPDATE soil_tests SET sample_date=?,organic_carbon_pct=?,ph=?,nitrogen=?,phosphorus=?,potassium=?,nutrient_units=?,lab_name=?,evidence_reference=?,notes=? WHERE id=? AND user_id=?""",
            (sample_date, organic_carbon, ph, *nutrients, nutrient_units, lab_name, evidence, notes, record_id, user_id),
        )
        if not cursor.rowcount:
            raise LookupError("Soil test record not found.")
        conn.commit()
        conn.row_factory = sqlite3.Row
        return dict(conn.execute("SELECT * FROM soil_tests WHERE id=?", (record_id,)).fetchone())


def add_regenerative_practice(user_id: int, farm_id: int, field_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    practice_type = str(payload.get("practice_type", "")).strip().lower()
    if practice_type not in PRACTICE_TYPES:
        raise ValueError(f"practice_type must be one of: {', '.join(sorted(PRACTICE_TYPES))}.")
    start_date = _date(payload.get("start_date"), "start_date")
    end_date = _date(payload["end_date"], "end_date") if payload.get("end_date") else None
    if end_date and end_date < start_date:
        raise ValueError("end_date cannot be before start_date.")
    area_ha = _optional_number(payload, "area_ha", 0)
    evidence = str(payload.get("evidence_reference", "")).strip()
    notes = str(payload.get("notes", "")).strip()
    if len(evidence) > 500 or len(notes) > 1500:
        raise ValueError("Evidence reference or notes exceed the allowed length.")
    with get_connection() as conn:
        field = _owned_field(conn, user_id, farm_id, field_id)
        if not field:
            raise LookupError("Farm field not found.")
        if area_ha and field["area_ha"] and area_ha > field["area_ha"]:
            raise ValueError("Practice area cannot exceed the recorded field area.")
        cursor = conn.execute(
            """INSERT INTO regenerative_practices (user_id,farm_id,field_id,practice_type,start_date,end_date,area_ha,evidence_reference,notes,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (user_id, farm_id, field_id, practice_type, start_date, end_date, area_ha, evidence, notes, _now()),
        )
        conn.commit()
        conn.row_factory = sqlite3.Row
        return dict(conn.execute("SELECT * FROM regenerative_practices WHERE id=?", (cursor.lastrowid,)).fetchone())


def update_regenerative_practice(user_id: int, record_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    practice_type = str(payload.get("practice_type", "")).strip().lower()
    if practice_type not in PRACTICE_TYPES:
        raise ValueError(f"practice_type must be one of: {', '.join(sorted(PRACTICE_TYPES))}.")
    start_date = _date(payload.get("start_date"), "start_date")
    end_date = _date(payload["end_date"], "end_date") if payload.get("end_date") else None
    if end_date and end_date < start_date:
        raise ValueError("end_date cannot be before start_date.")
    area_ha = _optional_number(payload, "area_ha", 0)
    evidence = str(payload.get("evidence_reference", "")).strip()
    notes = str(payload.get("notes", "")).strip()
    if len(evidence) > 500 or len(notes) > 1500:
        raise ValueError("Evidence reference or notes exceed the allowed length.")
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        record = conn.execute("SELECT field_id FROM regenerative_practices WHERE id=? AND user_id=?", (record_id, user_id)).fetchone()
        if not record:
            raise LookupError("Practice record not found.")
        field = conn.execute("SELECT area_ha FROM fields WHERE id=? AND user_id=?", (record["field_id"], user_id)).fetchone()
        if area_ha and field and field["area_ha"] and area_ha > field["area_ha"]:
            raise ValueError("Practice area cannot exceed the recorded field area.")
        conn.execute(
            """UPDATE regenerative_practices SET practice_type=?,start_date=?,end_date=?,area_ha=?,evidence_reference=?,notes=? WHERE id=? AND user_id=?""",
            (practice_type, start_date, end_date, area_ha, evidence, notes, record_id, user_id),
        )
        conn.commit()
        return dict(conn.execute("SELECT * FROM regenerative_practices WHERE id=?", (record_id,)).fetchone())


def get_carbon_readiness(user_id: int, farm_id: int, field_id: int) -> Dict[str, Any]:
    with get_connection() as conn:
        field = _owned_field(conn, user_id, farm_id, field_id)
        if not field:
            raise LookupError("Farm field not found.")
        conn.row_factory = sqlite3.Row
        soil_tests = [dict(row) for row in conn.execute("SELECT * FROM soil_tests WHERE user_id=? AND farm_id=? AND field_id=? ORDER BY sample_date DESC,id DESC", (user_id, farm_id, field_id))]
        practices = [dict(row) for row in conn.execute("SELECT * FROM regenerative_practices WHERE user_id=? AND farm_id=? AND field_id=? ORDER BY start_date DESC,id DESC", (user_id, farm_id, field_id))]

    sample_dates = {sample["sample_date"] for sample in soil_tests}
    first_sample = min(soil_tests, key=lambda sample: sample["sample_date"]) if soil_tests else None
    checklist = [
        {"key": "field_area", "label": "Field area recorded", "complete": bool(field["area_ha"] and field["area_ha"] > 0)},
        {"key": "baseline_soil_test", "label": "Baseline soil organic carbon measurement recorded", "complete": bool(soil_tests)},
        {"key": "repeat_soil_test", "label": "Follow-up soil measurement on a separate date", "complete": len(sample_dates) >= 2},
        {"key": "practice_log", "label": "At least one regenerative practice logged", "complete": bool(practices)},
        {"key": "evidence", "label": "Lab and practice evidence references recorded", "complete": bool(first_sample and first_sample["evidence_reference"] and any(item["evidence_reference"] for item in practices))},
    ]
    complete_count = sum(item["complete"] for item in checklist)
    readiness = "documentation_complete" if complete_count == len(checklist) else "in_progress" if complete_count else "not_started"
    return {
        "field": {"id": field["id"], "name": field["name"], "area_ha": field["area_ha"]},
        "readiness": readiness,
        "completed_items": complete_count,
        "total_items": len(checklist),
        "checklist": checklist,
        "soil_tests": soil_tests,
        "practices": practices,
        "carbon_credits": {"estimated": False, "verified": False, "message": "This tracker organizes records only. Credit eligibility and tonnes of CO2e require a selected methodology, baseline, monitoring period, and independent verification."},
    }
