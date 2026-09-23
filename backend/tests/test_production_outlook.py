from __future__ import annotations

from services.advisory_service import build_full_advisory, build_production_outlook, build_soil_restoration_plan


INPUTS = {"N": 90, "P": 45, "K": 42, "temperature": 27, "humidity": 84, "ph": 6.4, "rainfall": 245}


def test_production_outlook_has_yield_harvest_and_pest_sections():
    outlook = build_production_outlook("rice", INPUTS, season="Kharif", planting_date="2026-06-01")

    assert outlook["yield_estimate"]["planning_range_t_ha"][0] > 0
    assert outlook["harvest_window"]["start"] == "2026-09-19"
    assert outlook["harvest_window"]["planting_date_assumed_today"] is False
    assert outlook["pest_risk"]["level"] in {"low", "moderate", "high"}
    assert outlook["pest_risk"]["likely_pests"]


def test_advisory_integrates_production_outlook_without_changing_core_fields():
    advisory = build_full_advisory("rice", 0.92, 3.5, INPUTS, season="Kharif", planting_date="2026-06-01")

    assert advisory["crop"] == "rice"
    assert advisory["irrigation"]["value"] == 3.5
    assert advisory["production_outlook"]["harvest_window"]["planting_date"] == "2026-06-01"


def test_invalid_planting_date_uses_today_with_disclosure():
    outlook = build_production_outlook("maize", INPUTS, planting_date="not-a-date")

    assert outlook["harvest_window"]["planting_date_assumed_today"] is True
    assert any("does not replace" in item for item in outlook["limitations"])


def test_soil_restoration_plan_is_five_year_and_discloses_missing_measurements():
    plan = build_soil_restoration_plan(
        "maize",
        {"N": 20, "P": 20, "K": 20, "temperature": 28, "humidity": 60, "ph": 5.3, "rainfall": 150},
        season="Kharif",
    )

    assert plan["horizon_years"] == 5
    assert len(plan["plan"]) == 5
    assert plan["plan"][-1]["year"] == 5
    assert "low nitrogen indicator" in plan["priority_issues"]
    assert any("Organic carbon" in item for item in plan["limitations"])


def test_advisory_includes_soil_restoration_without_changing_irrigation():
    advisory = build_full_advisory("rice", 0.92, 3.5, INPUTS, season="Kharif")

    assert advisory["irrigation"]["value"] == 3.5
    assert advisory["soil_restoration"]["plan"][0]["year"] == 1
