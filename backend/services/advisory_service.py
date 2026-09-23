from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List


FEATURE_IMPORTANCE = {
    "N": 26.47,
    "rainfall": 19.13,
    "humidity": 16.24,
    "K": 13.23,
    "temperature": 9.09,
    "ph": 8.11,
    "P": 7.74,
}


CROP_PROFILES = {
    "rice": {
        "ideal": "Warm, humid climate with high rainfall.",
        "reason_fields": ["rainfall", "humidity", "N"],
        "fertilizer": {
            "N": (80, "Apply Urea in split doses to improve vegetative growth."),
            "P": (35, "Apply DAP before sowing for root development."),
            "K": (35, "Apply MOP if potassium is low for grain filling."),
        },
    },
    "maize": {
        "ideal": "Warm climate with moderate rainfall and balanced NPK.",
        "reason_fields": ["N", "rainfall", "K"],
        "fertilizer": {
            "N": (60, "Apply Urea after germination and again before tasseling."),
            "P": (30, "Apply DAP as a basal dose during sowing."),
            "K": (30, "Apply MOP if potassium is below recommended level."),
        },
    },
    "wheat": {
        "ideal": "Cool season crop with moderate humidity and 100-180 mm rainfall.",
        "reason_fields": ["temperature", "rainfall", "ph"],
        "fertilizer": {
            "N": (50, "Apply Urea in two split doses: sowing and crown-root initiation."),
            "P": (45, "Apply DAP at sowing for strong root growth."),
            "K": (45, "Apply MOP if potassium is deficient."),
        },
    },
    "chickpea": {
        "ideal": "Cool and dry conditions with moderate phosphorus and potassium.",
        "reason_fields": ["P", "K", "rainfall"],
        "fertilizer": {
            "N": (25, "Prefer compost or rhizobium biofertilizer; avoid excess nitrogen."),
            "P": (45, "Apply DAP/SSP as basal phosphorus support."),
            "K": (40, "Apply MOP only if potassium is low."),
        },
    },
    "coffee": {
        "ideal": "Mild temperature, slightly acidic pH, and moderate rainfall.",
        "reason_fields": ["temperature", "ph", "rainfall"],
        "fertilizer": {
            "N": (30, "Use organic manure with light nitrogen application."),
            "P": (30, "Apply rock phosphate or DAP based on soil test."),
            "K": (30, "Apply MOP for berry development if potassium is low."),
        },
    },
}


CROP_COMPARISON_RULES = {
    "wheat": {
        "temperature": (10, 25),
        "humidity": (45, 75),
        "rainfall": (75, 180),
        "ph": (6.0, 7.8),
        "nutrients": {"N": 50, "P": 45, "K": 45},
        "water_need": "Medium",
        "risk": "Heat stress if sown outside cool months.",
    },
    "rice": {
        "temperature": (22, 32),
        "humidity": (70, 95),
        "rainfall": (180, 320),
        "ph": (5.5, 7.2),
        "nutrients": {"N": 80, "P": 35, "K": 35},
        "water_need": "High",
        "risk": "High irrigation dependency if rainfall is weak.",
    },
    "maize": {
        "temperature": (20, 32),
        "humidity": (50, 80),
        "rainfall": (90, 180),
        "ph": (5.8, 7.5),
        "nutrients": {"N": 60, "P": 30, "K": 30},
        "water_need": "Medium",
        "risk": "Sensitive to moisture stress during flowering.",
    },
}


SEASON_WINDOWS = {
    "Kharif": {"months": {6, 7, 8, 9, 10}, "crops": {"rice", "maize", "cotton", "jute", "pigeonpeas"}},
    "Rabi": {"months": {11, 12, 1, 2, 3}, "crops": {"wheat", "chickpea", "lentil", "mustard", "barley"}},
    "Zaid": {"months": {4, 5}, "crops": {"maize", "watermelon", "muskmelon", "cucumber"}},
}


STATE_CROP_CONTEXT = {
    "Maharashtra": {
        "note": "Maharashtra farmers should prioritise water-efficient scheduling because rainfall distribution is uneven.",
        "preferred": {"cotton", "soybean", "maize", "chickpea", "rice", "wheat"},
    },
    "Punjab": {
        "note": "Punjab benefits from strong procurement channels for wheat and paddy, but water conservation is important.",
        "preferred": {"wheat", "rice", "maize"},
    },
    "Uttar Pradesh": {
        "note": "Uttar Pradesh supports wheat, rice, sugarcane, and pulses across multiple agro-climatic zones.",
        "preferred": {"wheat", "rice", "maize", "chickpea"},
    },
    "Karnataka": {
        "note": "Karnataka conditions vary by district, so rainfall timing and soil pH are especially important.",
        "preferred": {"maize", "ragi", "rice", "coffee", "tur"},
    },
    "Gujarat": {
        "note": "Gujarat farmers often benefit from drought-aware irrigation planning and market-timed crop choice.",
        "preferred": {"cotton", "groundnut", "wheat", "rice", "maize"},
    },
}


# Broad planning ranges only. These are intentionally presented as scenario
# estimates that must be calibrated with local variety, area, and field records.
PRODUCTION_PROFILES = {
    "rice": {"yield": (3.5, 6.0), "days": (110, 150), "temp": (22, 32), "humidity": (70, 95), "rainfall": (180, 320), "ph": (5.5, 7.2), "pests": ["stem borer", "brown planthopper"]},
    "wheat": {"yield": (3.0, 5.0), "days": (120, 140), "temp": (10, 25), "humidity": (45, 75), "rainfall": (75, 180), "ph": (6.0, 7.8), "pests": ["aphid", "termite"]},
    "maize": {"yield": (3.5, 6.0), "days": (90, 120), "temp": (20, 32), "humidity": (50, 80), "rainfall": (90, 180), "ph": (5.8, 7.5), "pests": ["fall armyworm", "stem borer"]},
    "chickpea": {"yield": (1.2, 2.2), "days": (100, 130), "temp": (15, 28), "humidity": (35, 65), "rainfall": (50, 130), "ph": (6.0, 8.0), "pests": ["pod borer", "aphid"]},
    "coffee": {"yield": (0.7, 1.5), "days": (240, 300), "temp": (18, 28), "humidity": (60, 90), "rainfall": (120, 300), "ph": (5.0, 6.8), "pests": ["coffee berry borer", "leaf miner"]},
    "cotton": {"yield": (1.5, 3.0), "days": (150, 180), "temp": (22, 35), "humidity": (45, 75), "rainfall": (60, 160), "ph": (5.8, 8.0), "pests": ["pink bollworm", "whitefly"]},
    "soybean": {"yield": (1.8, 3.0), "days": (90, 120), "temp": (20, 32), "humidity": (55, 85), "rainfall": (100, 250), "ph": (5.8, 7.5), "pests": ["girdle beetle", "leaf defoliator"]},
    "sugarcane": {"yield": (60.0, 90.0), "days": (300, 365), "temp": (22, 35), "humidity": (55, 85), "rainfall": (120, 300), "ph": (6.0, 8.0), "pests": ["early shoot borer", "internode borer"]},
}


CROP_FAMILIES = {
    "rice": "cereal",
    "wheat": "cereal",
    "maize": "cereal",
    "sugarcane": "grass",
    "chickpea": "legume",
    "soybean": "legume",
    "coffee": "perennial",
    "cotton": "fiber",
}


def _planning_profile(crop: str) -> Dict[str, Any]:
    aliases = {"paddy": "rice", "corn": "maize"}
    crop_key = aliases.get(str(crop).strip().lower(), str(crop).strip().lower())
    return PRODUCTION_PROFILES.get(crop_key, PRODUCTION_PROFILES["wheat"])


def _parse_planting_date(value: Any) -> tuple[date, bool]:
    if value:
        try:
            return date.fromisoformat(str(value)), False
        except ValueError:
            pass
    return date.today(), True


def _production_score(crop: str, inputs: Dict[str, Any], season: str | None) -> tuple[float, List[str]]:
    profile = _planning_profile(crop)
    fertilizer_profile = CROP_PROFILES.get(str(crop).lower(), CROP_PROFILES["wheat"])["fertilizer"]
    nutrient_targets = {nutrient: target for nutrient, (target, _) in fertilizer_profile.items()}
    climate_scores = [
        _range_score(inputs.get("temperature"), *profile["temp"]),
        _range_score(inputs.get("humidity"), *profile["humidity"]),
        _range_score(inputs.get("rainfall"), *profile["rainfall"]),
        _range_score(inputs.get("ph"), *profile["ph"]),
    ]
    nutrient_score = _nutrient_score(inputs, nutrient_targets)
    score = (sum(climate_scores) / len(climate_scores)) * 0.7 + nutrient_score * 0.3
    active_season = detect_season(season)
    if str(crop).lower() not in SEASON_WINDOWS.get(active_season, SEASON_WINDOWS["Kharif"])["crops"]:
        score -= 12
    drivers: List[str] = []
    for field, bounds in (("temperature", profile["temp"]), ("humidity", profile["humidity"]), ("rainfall", profile["rainfall"]), ("ph", profile["ph"])):
        if _range_score(inputs.get(field), *bounds) < 70:
            drivers.append(f"{field} is outside the broad planning range")
    return max(0.0, min(100.0, score)), drivers


def build_production_outlook(crop: str, inputs: Dict[str, Any], season: str | None = None, planting_date: Any = None) -> Dict[str, Any]:
    """Return transparent planning estimates; this is not a trained yield model."""
    profile = _planning_profile(crop)
    score, constraints = _production_score(crop, inputs, season)
    multiplier = 0.65 + (score / 100.0) * 0.35
    yield_low, yield_high = profile["yield"]
    planted_on, assumed_today = _parse_planting_date(planting_date)
    harvest_start = planted_on + timedelta(days=profile["days"][0])
    harvest_end = planted_on + timedelta(days=profile["days"][1])

    try:
        temperature = float(inputs.get("temperature", 0) or 0)
        humidity = float(inputs.get("humidity", 0) or 0)
        rainfall = float(inputs.get("rainfall", 0) or 0)
    except (TypeError, ValueError):
        temperature = humidity = rainfall = 0.0
    warm_humid = 20 <= temperature <= 34 and humidity >= 75
    dry_hot = temperature >= 30 and humidity <= 50
    pest_score = 30 + (25 if warm_humid else 0) + (15 if rainfall >= 100 else 0) + (15 if dry_hot else 0)
    risk = "high" if pest_score >= 65 else "moderate" if pest_score >= 45 else "low"
    risk_drivers = []
    if warm_humid:
        risk_drivers.append("warm and humid conditions can favor pest activity")
    if rainfall >= 100:
        risk_drivers.append("recently wet conditions increase the need for field scouting")
    if dry_hot:
        risk_drivers.append("hot, dry conditions can increase sap-feeding pest pressure")
    if not risk_drivers:
        risk_drivers.append("current entered conditions do not indicate elevated weather-driven pressure")

    return {
        "yield_estimate": {
            "planning_range_t_ha": [round(yield_low * multiplier, 1), round(yield_high * multiplier, 1)],
            "suitability_score": round(score),
            "confidence": "planning estimate",
            "constraints": constraints or ["entered soil and weather values are within broad planning ranges"],
        },
        "harvest_window": {
            "start": harvest_start.isoformat(),
            "end": harvest_end.isoformat(),
            "crop_duration_days": list(profile["days"]),
            "planting_date": planted_on.isoformat(),
            "planting_date_assumed_today": assumed_today,
        },
        "pest_risk": {
            "level": risk,
            "likely_pests": profile["pests"],
            "drivers": risk_drivers,
            "recommended_action": "Scout representative plants this week and confirm symptoms with local extension guidance before applying control measures.",
        },
        "limitations": [
            "Planning estimate based on entered soil, weather, crop, and season inputs.",
            "It does not replace field yield measurements, pest traps, or local agronomy advice.",
        ],
    }


def _status(value: float, threshold: float) -> str:
    if value < threshold * 0.8:
        return "low"
    if value > threshold * 1.25:
        return "high"
    return "adequate"


def detect_season(raw_season: str | None = None, month: int | None = None) -> str:
    if raw_season and raw_season.strip() and raw_season.strip().lower() != "auto":
        return raw_season.strip().title()

    current_month = month or datetime.now().month
    for season, config in SEASON_WINDOWS.items():
        if current_month in config["months"]:
            return season
    return "Kharif"


def build_fertilizer_advice(crop: str, inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
    profile = CROP_PROFILES.get(str(crop).lower(), CROP_PROFILES["wheat"])
    advice: List[Dict[str, Any]] = []
    for nutrient in ["N", "P", "K"]:
        value = float(inputs.get(nutrient, 0))
        threshold, recommendation = profile["fertilizer"][nutrient]
        status = _status(value, threshold)
        if status == "low":
            message = recommendation
        elif status == "high":
            message = f"{nutrient} is already high. Avoid extra {nutrient}-heavy fertilizer."
        else:
            message = f"{nutrient} level is adequate. Maintain with compost or normal basal dose."
        advice.append(
            {
                "nutrient": nutrient,
                "value": value,
                "target": threshold,
                "status": status,
                "recommendation": message,
            }
        )
    return advice


def build_prediction_explanation(crop: str, confidence: float, inputs: Dict[str, Any]) -> Dict[str, Any]:
    crop_key = str(crop).lower()
    profile = CROP_PROFILES.get(crop_key, CROP_PROFILES["wheat"])
    confidence_percent = confidence * 100 if confidence <= 1 else confidence
    important_fields = profile["reason_fields"]
    drivers = [
        {
            "feature": field,
            "value": inputs.get(field),
            "importance": FEATURE_IMPORTANCE.get(field, 0),
        }
        for field in important_fields
    ]
    driver_text = ", ".join(
        f"{item['feature']}={item['value']} ({item['importance']:.2f}% model importance)"
        for item in drivers
    )
    return {
        "summary": (
            f"The model selected {crop.title()} with {confidence_percent:.2f}% confidence. "
            f"This crop profile matches: {profile['ideal']}"
        ),
        "main_drivers": drivers,
        "plain_reason": f"Important matching factors for this result are {driver_text}.",
        "confidence_level": "high" if confidence_percent >= 80 else "medium" if confidence_percent >= 55 else "low",
    }


def build_seasonal_advice(crop: str, season: str | None = None, state: str | None = None) -> Dict[str, Any]:
    crop_key = str(crop).lower()
    active_season = detect_season(season)
    season_config = SEASON_WINDOWS.get(active_season, SEASON_WINDOWS["Kharif"])
    state_profile = STATE_CROP_CONTEXT.get(str(state or "").strip(), {})
    season_crops = sorted(season_config["crops"])

    season_fit = crop_key in season_config["crops"]
    if season_fit:
        season_message = f"{crop.title()} is a good fit for the {active_season} season."
    else:
        season_message = f"{crop.title()} is less common in {active_season}; compare with local sowing calendars before final selection."

    state_message = state_profile.get("note", "Use local mandi trends and extension guidance to confirm final crop choice.")
    state_fit = crop_key in state_profile.get("preferred", set()) if state_profile else None

    if state_fit is True:
        location_message = f"{crop.title()} is commonly cultivated in {state} and aligns reasonably well with local patterns. {state_message}"
    elif state_fit is False:
        location_message = f"{crop.title()} may still work in {state}, but it is not among the most typical recommendations there. {state_message}"
    else:
        location_message = state_message

    return {
        "current_season": active_season,
        "season_fit": season_fit,
        "season_priority": "recommended" if season_fit else "review before sowing",
        "recommended_season_crops": season_crops,
        "season_message": season_message,
        "location_message": location_message,
        "state": state or "Not specified",
    }


def _range_score(value: Any, low: float, high: float) -> float:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return 0.0

    if low <= numeric_value <= high:
        return 100.0

    width = max(high - low, 1.0)
    distance = low - numeric_value if numeric_value < low else numeric_value - high
    return max(0.0, 100.0 - (distance / width) * 100.0)


def _nutrient_score(inputs: Dict[str, Any], targets: Dict[str, float]) -> float:
    scores = []
    for nutrient, target in targets.items():
        try:
            value = float(inputs.get(nutrient, 0))
        except (TypeError, ValueError):
            value = 0.0
        difference_ratio = abs(value - target) / max(target, 1)
        scores.append(max(0.0, 100.0 - difference_ratio * 100.0))
    return sum(scores) / len(scores) if scores else 0.0


def build_crop_comparison(inputs: Dict[str, Any], season: str | None = None, state: str | None = None) -> List[Dict[str, Any]]:
    active_season = detect_season(season)
    season_crops = SEASON_WINDOWS.get(active_season, SEASON_WINDOWS["Kharif"])["crops"]
    state_profile = STATE_CROP_CONTEXT.get(str(state or "").strip(), {})
    state_crops = state_profile.get("preferred", set())
    comparisons: List[Dict[str, Any]] = []

    for crop_name, rules in CROP_COMPARISON_RULES.items():
        climate_score = (
            _range_score(inputs.get("temperature"), *rules["temperature"]) * 0.25
            + _range_score(inputs.get("humidity"), *rules["humidity"]) * 0.20
            + _range_score(inputs.get("rainfall"), *rules["rainfall"]) * 0.25
            + _range_score(inputs.get("ph"), *rules["ph"]) * 0.15
            + _nutrient_score(inputs, rules["nutrients"]) * 0.15
        )
        season_score = 100.0 if crop_name in season_crops else 45.0
        state_score = 100.0 if crop_name in state_crops else 70.0 if state_crops else 80.0
        final_score = round((climate_score * 0.62) + (season_score * 0.25) + (state_score * 0.13), 2)

        comparisons.append(
            {
                "crop": crop_name.title(),
                "suitability_score": final_score,
                "season_fit": crop_name in season_crops,
                "state_fit": crop_name in state_crops if state_crops else None,
                "water_need": rules["water_need"],
                "fertilizer_focus": ", ".join(rules["nutrients"].keys()),
                "risk": rules["risk"],
            }
        )

    return sorted(comparisons, key=lambda item: item["suitability_score"], reverse=True)


def build_season_adjusted_ranking(
    crop: str,
    confidence: float,
    inputs: Dict[str, Any],
    season: str | None = None,
    state: str | None = None,
    top_crops: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    active_season = detect_season(season)
    season_crops = SEASON_WINDOWS.get(active_season, SEASON_WINDOWS["Kharif"])["crops"]
    comparison_by_crop = {item["crop"].lower(): item for item in build_crop_comparison(inputs, active_season, state)}
    candidate_map: Dict[str, float] = {}

    for item in top_crops or []:
        crop_name = str(item.get("crop", "")).strip().lower()
        if crop_name:
            raw_confidence = float(item.get("confidence", 0))
            candidate_map[crop_name] = raw_confidence * 100 if raw_confidence <= 1 else raw_confidence

    crop_key = str(crop).strip().lower()
    if crop_key and crop_key not in candidate_map:
        candidate_map[crop_key] = confidence * 100 if confidence <= 1 else confidence

    for crop_name in comparison_by_crop:
        candidate_map.setdefault(crop_name, 0.0)

    ranking = []
    for crop_name, ml_score in candidate_map.items():
        comparison_score = comparison_by_crop.get(crop_name, {}).get("suitability_score", 60.0)
        season_score = 100.0 if crop_name in season_crops else 45.0
        final_score = round((ml_score * 0.55) + (comparison_score * 0.30) + (season_score * 0.15), 2)
        ranking.append(
            {
                "crop": crop_name.title(),
                "ml_confidence": round(ml_score, 2),
                "season_fit": crop_name in season_crops,
                "input_suitability": round(float(comparison_score), 2),
                "season_adjusted_score": final_score,
            }
        )

    ranking.sort(key=lambda item: item["season_adjusted_score"], reverse=True)
    adjusted_crop = ranking[0]["crop"] if ranking else str(crop).title()
    original_crop = str(crop).title()

    return {
        "original_ml_crop": original_crop,
        "season_adjusted_crop": adjusted_crop,
        "changed_from_ml": adjusted_crop.lower() != original_crop.lower(),
        "active_season": active_season,
        "ranking": ranking[:5],
        "message": (
            f"Season adjustment kept {original_crop} as the best recommendation."
            if adjusted_crop.lower() == original_crop.lower()
            else f"Season adjustment suggests reviewing {adjusted_crop} because it fits {active_season} and the entered conditions better."
        ),
    }


def interpret_irrigation(irrigation_value: float) -> Dict[str, Any]:
    value = float(irrigation_value)
    if value < 1:
        level = "very low"
        message = "Irrigation is barely required. Monitor soil moisture before watering."
    elif value < 3:
        level = "low to moderate"
        message = "Light irrigation is enough. Avoid over-watering."
    elif value < 5:
        level = "moderate"
        message = "Irrigate in the morning or evening to reduce evaporation loss."
    else:
        level = "high"
        message = "Higher irrigation is required. Split watering into multiple sessions if possible."
    return {
        "value": round(value, 4),
        "unit": "model-estimated mm",
        "level": level,
        "recommendation": message,
    }


def build_soil_restoration_plan(crop: str, inputs: Dict[str, Any], season: str | None = None) -> Dict[str, Any]:
    """Create a conservative five-year soil-restoration plan from available inputs."""
    try:
        nitrogen = float(inputs.get("N", 0))
        phosphorus = float(inputs.get("P", 0))
        potassium = float(inputs.get("K", 0))
        soil_ph = float(inputs.get("ph", 0))
    except (TypeError, ValueError):
        nitrogen = phosphorus = potassium = soil_ph = 0.0

    crop_key = str(crop).strip().lower()
    family = CROP_FAMILIES.get(crop_key, "annual")
    priorities: List[str] = []
    amendments: List[str] = ["Retain suitable crop residues and add mature compost based on a soil test."]
    if nitrogen < 40:
        priorities.append("low nitrogen indicator")
        amendments.append("Use a legume cover crop or green manure before the next heavy-feeding crop.")
    if phosphorus < 30:
        priorities.append("low phosphorus indicator")
        amendments.append("Confirm phosphorus availability through a soil test before applying a locally recommended amendment.")
    if potassium < 30:
        priorities.append("low potassium indicator")
        amendments.append("Review potassium with a soil test and return crop residues where appropriate.")
    if soil_ph and soil_ph < 5.8:
        priorities.append("acidic pH indicator")
        amendments.append("Seek local soil-test guidance before lime application; rate depends on soil buffer capacity.")
    elif soil_ph > 7.8:
        priorities.append("alkaline pH indicator")
        amendments.append("Use organic matter and obtain local guidance before any sulphur or micronutrient correction.")
    if not priorities:
        priorities.append("maintain current nutrient balance with periodic testing")

    legume_rotation = "chickpea or soybean, selected for the local season"
    cereal_rotation = "maize or a locally suitable cereal after a legume phase"
    if family == "legume":
        year_one_rotation = cereal_rotation
    elif family in {"cereal", "grass"}:
        year_one_rotation = legume_rotation
    else:
        year_one_rotation = "a locally suitable legume cover crop between production cycles"

    return {
        "horizon_years": 5,
        "soil_condition": "restoration priority" if len(priorities) > 1 else "maintenance and restoration",
        "priority_issues": priorities,
        "plan": [
            {
                "year": 1,
                "focus": "Stabilize soil cover and nutrient cycling",
                "rotation": year_one_rotation,
                "cover_crop": "Use a locally suitable legume cover crop where the field is not under the main crop.",
                "microbial_support": "Consider crop-compatible Rhizobium only for legumes, and only from a verified local source.",
                "practices": amendments,
            },
            {
                "year": 2,
                "focus": "Build organic matter and break pest cycles",
                "rotation": "Alternate crop family: combine a cereal or oilseed with a legume phase.",
                "cover_crop": "Keep living cover or residue mulch during the longest fallow period.",
                "microbial_support": "Use microbial inoculants only where a soil test and local extension advice support their use.",
                "practices": ["Re-test pH and NPK before the main season.", "Avoid repeated monocropping where a rotation is practical."],
            },
            {
                "year": 3,
                "focus": "Consolidate and measure recovery",
                "rotation": "Repeat the best-performing cereal-legume sequence and adapt it to water availability.",
                "cover_crop": "Maintain cover through off-season periods to reduce erosion and nutrient loss.",
                "microbial_support": "Review inoculant performance with local agronomy support rather than assuming a response.",
                "practices": ["Compare soil-test trends with the starting baseline.", "Extend the plan for years 4-5 only after reviewing field records and soil tests."],
            },
            {
                "year": 4,
                "focus": "Refine the rotation from measured results",
                "rotation": "Keep the best-performing cereal-legume or oilseed-legume sequence and adjust it to local water availability.",
                "cover_crop": "Use a cover crop or mulch during exposed periods where it does not compete for scarce water.",
                "microbial_support": "Continue only locally validated inoculant practices that have been reviewed against crop and soil-test records.",
                "practices": ["Repeat the same-season soil test for a comparable trend.", "Record crop residue, compost, irrigation, and yield outcomes for the next review."],
            },
            {
                "year": 5,
                "focus": "Set the next restoration baseline",
                "rotation": "Choose the next cycle from the rotation that protected soil cover while meeting farm production needs.",
                "cover_crop": "Maintain residue cover or a locally suitable cover crop as part of the standard field calendar.",
                "microbial_support": "Do not assume continuing benefit; renew microbial recommendations only with local agronomy advice.",
                "practices": ["Compare five-year soil-test and yield records with the initial baseline.", "Create the next multi-year plan with a soil laboratory or extension officer."],
            },
        ],
        "limitations": [
            "Organic carbon, texture, salinity, microbial activity, and field history were not available in this advisory.",
            "This is a restoration planning guide, not a verified carbon-credit calculation; validate amendments and inoculants with a local soil laboratory or extension officer.",
        ],
    }


def build_full_advisory(
    crop: str,
    confidence: float,
    irrigation_value: float,
    inputs: Dict[str, Any],
    season: str | None = None,
    state: str | None = None,
    top_crops: List[Dict[str, Any]] | None = None,
    planting_date: Any = None,
) -> Dict[str, Any]:
    return {
        "crop": crop,
        "context": {"season": detect_season(season), "state": state or "Not specified"},
        "fertilizer": build_fertilizer_advice(crop, inputs),
        "explanation": build_prediction_explanation(crop, confidence, inputs),
        "seasonal_advice": build_seasonal_advice(crop, season=season, state=state),
        "season_adjusted": build_season_adjusted_ranking(
            crop=crop,
            confidence=confidence,
            inputs=inputs,
            season=season,
            state=state,
            top_crops=top_crops,
        ),
        "crop_comparison": build_crop_comparison(inputs, season=season, state=state),
        "irrigation": interpret_irrigation(irrigation_value),
        "production_outlook": build_production_outlook(crop, inputs, season=season, planting_date=planting_date),
        "soil_restoration": build_soil_restoration_plan(crop, inputs, season=season),
    }
