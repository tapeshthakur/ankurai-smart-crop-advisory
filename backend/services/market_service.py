from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

from config import settings
from services.advisory_service import detect_season


MSP_SEASONS = {
    "kharif": {
        "paddy": 2441, "rice": 2441, "rice_grade_a": 2461, "jowar": 4023, "bajra": 2900, "ragi": 5205,
        "maize": 2410, "corn": 2410, "tur": 8450, "arhar": 8450, "moong": 8780,
        "mung": 8780, "urad": 8200, "groundnut": 7517, "sunflower": 8343,
        "soybean": 5708, "soyabean": 5708, "sesame": 10346, "sesamum": 10346,
        "nigerseed": 10052, "cotton": 8267, "cotton_long_staple": 8667,
    },
    "rabi": {
        "wheat": 2585, "barley": 2150, "chickpea": 5875, "gram": 5875,
        "lentil": 7000, "masur": 7000, "mustard": 6200, "rapeseed": 6200,
        "safflower": 6540,
    },
}
MSP_SOURCE = "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2260618&lang=1&reg=3"
MSP_RABI_SOURCE = "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2173567&lang=2&reg=3"


GOVT_SCHEMES = {
    "Maharashtra": [
        {"name": "Magel Tyala Shet Tale", "benefit": "Farm pond and irrigation support", "link": "https://mahadbt.maharashtra.gov.in"},
        {"name": "PM-KISAN", "benefit": "Rs. 6000 yearly income support", "link": "https://pmkisan.gov.in"},
    ],
    "Punjab": [
        {"name": "PM-KISAN", "benefit": "Rs. 6000 yearly income support", "link": "https://pmkisan.gov.in"},
        {"name": "PANI Bachao Paisa Kamao", "benefit": "Incentive for groundwater saving", "link": "https://agripb.gov.in"},
    ],
    "Uttar Pradesh": [
        {"name": "PM-KISAN", "benefit": "Rs. 6000 yearly income support", "link": "https://pmkisan.gov.in"},
        {"name": "Krishak Durghatna Kalyan Yojana", "benefit": "Farmer family accident support", "link": "https://upagripardarshi.gov.in"},
    ],
    "Karnataka": [
        {"name": "Raitha Siri", "benefit": "Support for millet and sustainable cultivation", "link": "https://raitamitra.karnataka.gov.in"},
        {"name": "PM-KISAN", "benefit": "Rs. 6000 yearly income support", "link": "https://pmkisan.gov.in"},
    ],
    "Gujarat": [
        {"name": "Ikhedut Portal", "benefit": "State agriculture scheme applications and subsidy support", "link": "https://ikhedut.gujarat.gov.in"},
        {"name": "PM-KISAN", "benefit": "Rs. 6000 yearly income support", "link": "https://pmkisan.gov.in"},
    ],
}


KVK_CONTACTS = {
    "Maharashtra": {"name": "KVK Baramati / district KVK network", "contact": "+91-2112-255227"},
    "Punjab": {"name": "KVK Ludhiana / district KVK network", "contact": "+91-161-2401960"},
    "Uttar Pradesh": {"name": "KVK Kanpur / district KVK network", "contact": "+91-512-2693191"},
    "Karnataka": {"name": "KVK Bengaluru Rural / district KVK network", "contact": "+91-80-28466317"},
    "Gujarat": {"name": "KVK Anand / district KVK network", "contact": "+91-2692-261310"},
}


SEASONAL_MARKET_TIPS = {
    "Kharif": "Monitor rainfall timing and paddy/maize mandi arrivals before locking the crop choice.",
    "Rabi": "Compare procurement support, irrigation availability, and storage options for wheat and pulses.",
    "Zaid": "Short-duration summer crops can work well, but market timing and irrigation reliability matter most.",
}


_MANDI_CACHE: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
_TREND_CACHE: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
_AGMARKNET_FILTERS_CACHE: Dict[str, Any] = {"expires_at": 0, "data": None}
AGMARKNET_BASE_URL = "https://api.agmarknet.gov.in/v1"
AGMARKNET_SOURCE_URL = "https://agmarknet.gov.in/home"

AGMARKNET_COMMODITY_ALIASES = {
    "wheat": ["Wheat"],
    "rice": ["Rice", "Paddy(Dhan)(Common)", "Paddy"],
    "paddy": ["Paddy(Dhan)(Common)", "Paddy", "Rice"],
    "maize": ["Maize"],
    "corn": ["Maize"],
    "chickpea": ["Bengal Gram(Gram)(Whole)", "Bengal Gram", "Chickpea", "Gram"],
    "coffee": ["Coffee"],
    "cotton": ["Cotton", "Cotton (Kapas)"],
    "soybean": ["Soyabean", "Soybean"],
    "sugarcane": ["Sugarcane"],
    "groundnut": ["Groundnut"],
    "mustard": ["Mustard"],
    "barley": ["Barley"],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cache_get(key: Tuple[str, str]) -> Dict[str, Any] | None:
    cached = _MANDI_CACHE.get(key)
    if not cached:
        return None
    age_seconds = time.time() - float(cached.get("_cached_at", 0))
    if age_seconds > settings.mandi_cache_ttl_seconds:
        return None
    return cached.get("payload")


def _cache_set(key: Tuple[str, str], payload: Dict[str, Any]) -> Dict[str, Any]:
    _MANDI_CACHE[key] = {"_cached_at": time.time(), "payload": payload}
    return payload


def _float_or_none(value: Any) -> float | None:
    try:
        if value in {None, ""}:
            return None
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _request_agmarknet(path: str, params: Dict[str, Any] | None = None, timeout_seconds: float = 8) -> Dict[str, Any]:
    url = f"{AGMARKNET_BASE_URL}/{path.lstrip('/')}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://agmarknet.gov.in",
            "Referer": "https://agmarknet.gov.in/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _agmarknet_filters() -> Dict[str, Any]:
    now = time.monotonic()
    cached = _AGMARKNET_FILTERS_CACHE.get("data")
    if cached and now < _AGMARKNET_FILTERS_CACHE["expires_at"]:
        return cached
    payload = _request_agmarknet("daily-price-arrival/filters", timeout_seconds=8)
    if not payload.get("status"):
        raise ValueError(payload.get("message") or "AGMARKNET filters are unavailable")
    data = payload.get("data") or {}
    _AGMARKNET_FILTERS_CACHE.update(data=data, expires_at=now + 21600)
    return data


def _normalise_name(value: Any) -> str:
    return "".join(character for character in str(value or "").lower() if character.isalnum())


def _district_lookup(filters: Dict[str, Any]) -> Dict[int, str]:
    return {
        int(item["id"]): str(item.get("district_name") or "")
        for item in filters.get("district_data", [])
        if str(item.get("id", "")).isdigit()
    }


def _market_lookup(filters: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(item.get("mkt_name") or "").strip(): item
        for item in filters.get("market_data", [])
        if item.get("mkt_name")
    }


def _price_record(
    state: str,
    market: str,
    item: Dict[str, Any],
    commodity: str,
    report_date: date,
    district_by_id: Dict[int, str],
    market_by_name: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    market_info = market_by_name.get(market.strip(), {})
    district_id = market_info.get("district_id")
    district = district_by_id.get(int(district_id), "") if str(district_id or "").isdigit() else ""
    return {
        "state": state,
        "district": district,
        "market": market.strip(),
        "commodity": commodity,
        "variety": item.get("variety") or "",
        "grade": item.get("grade") or "",
        "arrival_date": report_date.isoformat(),
        "min_price": _float_or_none(item.get("minimumPrice")),
        "max_price": _float_or_none(item.get("maximumPrice")),
        "modal_price": _float_or_none(item.get("modalPrice")),
        "unit": item.get("unitOfPrice") or "Rs./Quintal",
    }


def _summarise_live_prices(records: List[Dict[str, Any]], commodity: str) -> Dict[str, Any]:
    modal_prices = [record["modal_price"] for record in records if record.get("modal_price") is not None]
    min_prices = [record["min_price"] for record in records if record.get("min_price") is not None]
    max_prices = [record["max_price"] for record in records if record.get("max_price") is not None]
    latest_date = max((str(record.get("arrival_date") or "") for record in records), default="")

    summary: Dict[str, Any] = {
        "commodity": commodity,
        "record_count": len(records),
        "latest_arrival_date": latest_date,
        "average_modal_price": round(sum(modal_prices) / len(modal_prices), 2) if modal_prices else None,
        "lowest_min_price": min(min_prices) if min_prices else None,
        "highest_max_price": max(max_prices) if max_prices else None,
        "unit": "Rs/quintal",
    }
    if summary["average_modal_price"] is not None:
        summary["display_price"] = f"Rs. {summary['average_modal_price']:,.0f} / quintal"
    else:
        summary["display_price"] = "Live price unavailable"
    return summary


def fetch_live_mandi_prices(state: str, crop: str, district: str = "", market: str = "") -> Dict[str, Any]:
    cache_key = (state.strip().title(), str(crop or "wheat").strip().lower(), district.strip().casefold(), market.strip().casefold())
    cached = _cache_get(cache_key)
    if cached:
        return {**cached, "from_cache": True}

    errors: List[str] = []
    try:
        filters = _agmarknet_filters()
        normalized_state = _normalise_name(state)
        state_row = next(
            (item for item in filters.get("state_data", []) if _normalise_name(item.get("state_name")) == normalized_state),
            None,
        )
        if not state_row:
            raise ValueError(f"AGMARKNET has no state mapping for {state}")
        state_id = int(state_row["state_id"])
        district_by_id = _district_lookup(filters)
        market_by_name = _market_lookup(filters)
        crop_key = str(crop or "wheat").strip().lower()
        aliases = {_normalise_name(item) for item in AGMARKNET_COMMODITY_ALIASES.get(crop_key, [crop_key])}
        today = date.today()

        for offset in range(4):
            report_date = today - timedelta(days=offset)
            payload = _request_agmarknet(
                "prices-and-arrivals/commodity-market/daily-report-state",
                {"date": report_date.isoformat(), "state": state_id, "includeExcel": "false"},
                timeout_seconds=8,
            )
            if not payload.get("success"):
                continue

            records = []
            for group in payload.get("commodityGroups", []):
                for commodity in group.get("commodities", []):
                    if _normalise_name(commodity.get("commodityName")) not in aliases:
                        continue
                    for market_row in commodity.get("markets", []):
                        market_name = str(market_row.get("marketCenter") or "").strip()
                        for item in market_row.get("data", []):
                            records.append(_price_record(state, market_name, item, commodity.get("commodityName"), report_date, district_by_id, market_by_name))
            if district:
                records = [record for record in records if _normalise_name(record.get("district")) == _normalise_name(district)]
            if market:
                records = [record for record in records if _normalise_name(record.get("market")) == _normalise_name(market)]
            if records:
                selected_commodity = records[0]["commodity"]
                live_payload = {
                    "is_live": True,
                    "from_cache": False,
                    "source": "AGMARKNET 2.0 - Directorate of Marketing & Inspection",
                    "source_url": AGMARKNET_SOURCE_URL,
                    "scope": "state",
                    "fetched_at": _now_iso(),
                    "summary": _summarise_live_prices(records, selected_commodity),
                    "records": records,
                }
                return _cache_set(cache_key, live_payload)

        commodity_rows = filters.get("cmdt_data", [])
        commodity_row = next(
            (item for item in commodity_rows if _normalise_name(item.get("cmdt_name")) in aliases),
            None,
        )
        if commodity_row and not (district or market):
            for offset in range(2):
                report_date = today - timedelta(days=offset)
                report = _request_agmarknet(
                    "prices-and-arrivals/market-report/specific",
                    {
                        "date": report_date.isoformat(),
                        "commodityGroupId": commodity_row.get("cmdt_group_id"),
                        "commodityId": commodity_row.get("cmdt_id"),
                        "includeExcel": "false",
                    },
                    timeout_seconds=8,
                )
                national_records = []
                for state_data in report.get("states", []):
                    state_name = str(state_data.get("stateName") or "")
                    for market in state_data.get("markets", []):
                        market_name = str(market.get("marketName") or "")
                        for item in market.get("data", []):
                            national_records.append(_price_record(state_name, market_name, item, commodity_row.get("cmdt_name"), report_date, district_by_id, market_by_name))
                if national_records:
                    live_payload = {
                        "is_live": True,
                        "from_cache": False,
                        "source": "AGMARKNET 2.0 - Directorate of Marketing & Inspection",
                        "source_url": AGMARKNET_SOURCE_URL,
                        "scope": "national",
                        "requested_state": state,
                        "fetched_at": _now_iso(),
                        "summary": _summarise_live_prices(national_records, commodity_row.get("cmdt_name")),
                        "records": national_records,
                    }
                    return _cache_set(cache_key, live_payload)
    except urllib.error.HTTPError as exc:
        errors.append(f"HTTP {exc.code}")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError, KeyError) as exc:
        errors.append(str(exc))

    return {
        "is_live": False,
        "from_cache": False,
        "source": "AGMARKNET 2.0 - Directorate of Marketing & Inspection",
        "source_url": AGMARKNET_SOURCE_URL,
        "fetched_at": _now_iso(),
        "message": (
            "Live AGMARKNET data could not be reached; reference data is shown."
            if errors
            else "No AGMARKNET records were reported for this crop and state in the last four reporting days."
        ),
        "errors": errors[:3],
        "records": [],
    }


def fetch_mandi_price_trend(state: str, crop: str, district: str = "", market: str = "") -> Dict[str, Any]:
    cache_key = (state.strip().title(), str(crop or "wheat").strip().lower(), district.strip().casefold(), market.strip().casefold())
    cached = _TREND_CACHE.get(cache_key)
    if cached and time.time() - cached["cached_at"] < min(settings.mandi_cache_ttl_seconds, 1800):
        return cached["payload"]
    try:
        filters = _agmarknet_filters()
        state_key = _normalise_name(state)
        state_row = next((row for row in filters.get("state_data", []) if _normalise_name(row.get("state_name")) == state_key), None)
        if not state_row:
            return {"records": [], "source_url": AGMARKNET_SOURCE_URL, "message": "No AGMARKNET state mapping was found."}
        aliases = {_normalise_name(item) for item in AGMARKNET_COMMODITY_ALIASES.get(str(crop).lower(), [crop])}
        district_by_id = _district_lookup(filters)
        market_by_name = _market_lookup(filters)
        state_id = int(state_row["state_id"])
        days = [date.today() - timedelta(days=offset) for offset in range(7)]

        def load_day(report_date: date) -> List[Dict[str, Any]]:
            payload = _request_agmarknet(
                "prices-and-arrivals/commodity-market/daily-report-state",
                {"date": report_date.isoformat(), "state": state_id, "includeExcel": "false"},
                timeout_seconds=6,
            )
            day_records = []
            if not payload.get("success"):
                return day_records
            for group in payload.get("commodityGroups", []):
                for commodity in group.get("commodities", []):
                    if _normalise_name(commodity.get("commodityName")) not in aliases:
                        continue
                    for market_row in commodity.get("markets", []):
                        name = str(market_row.get("marketCenter") or "").strip()
                        for item in market_row.get("data", []):
                            day_records.append(_price_record(state, name, item, commodity.get("commodityName"), report_date, district_by_id, market_by_name))
            return day_records

        records: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(load_day, day) for day in days]
            for future in as_completed(futures):
                try:
                    records.extend(future.result())
                except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
                    continue
        if district:
            records = [row for row in records if _normalise_name(row.get("district")) == _normalise_name(district)]
        if market:
            records = [row for row in records if _normalise_name(row.get("market")) == _normalise_name(market)]
        by_date: Dict[str, List[float]] = {}
        for row in records:
            price = row.get("modal_price")
            if price is not None:
                by_date.setdefault(row["arrival_date"], []).append(float(price))
        trend = [{"date": day, "average_modal_price": round(sum(values) / len(values), 2), "records": len(values)} for day, values in sorted(by_date.items())]
        result = {"records": trend, "source_url": AGMARKNET_SOURCE_URL, "fetched_at": _now_iso(), "scope": "market" if market else "district" if district else "state"}
        _TREND_CACHE[cache_key] = {"cached_at": time.time(), "payload": result}
        return result
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError, KeyError) as exc:
        return {"records": [], "source_url": AGMARKNET_SOURCE_URL, "message": str(exc)[:240]}


def get_market_overview(state: str | None, crop: str | None, season: str | None, district: str = "", market: str = "") -> Dict[str, Any]:
    active_state = (state or "Maharashtra").strip().title()
    active_crop = str(crop or "wheat").strip().lower()
    active_season = detect_season(season)

    state_schemes: List[Dict[str, Any]] = GOVT_SCHEMES.get(active_state, [])
    schemes: List[Dict[str, Any]] = [
        {
            "name": "PM-KISAN", "category": "income", "benefit": "Income support for eligible landholding farmer families; eKYC and official verification apply.",
            "eligibility": "Landholding farmer family, subject to scheme exclusions and verified land records.",
            "documents": ["Aadhaar", "Land records", "Bank account details"], "link": "https://pmkisan.gov.in/",
            "states": ["all"], "crops": ["all"], "official": True,
        },
        {
            "name": "Pradhan Mantri Fasal Bima Yojana", "category": "insurance", "benefit": "Crop insurance for notified crops and areas, subject to the current state notification and enrolment window.",
            "eligibility": "Farmers with insurable interest in a crop notified for their area and season; tenant/sharecropper documentation rules vary by state.",
            "documents": ["Aadhaar", "Land or cultivation proof", "Bank details", "Sown-crop declaration"], "link": "https://pmfby.gov.in/",
            "states": ["all"], "crops": ["notified"], "official": True,
        },
        *state_schemes,
    ]
    unique_schemes: List[Dict[str, Any]] = []
    seen_scheme_names = set()
    for scheme in schemes:
        if scheme["name"] in seen_scheme_names:
            continue
        seen_scheme_names.add(scheme["name"])
        scheme.setdefault("category", "state")
        scheme.setdefault("eligibility", "Eligibility, notified components, and application dates are determined by the official state portal.")
        scheme.setdefault("documents", ["Aadhaar", "Farmer/land records", "Bank details"])
        scheme.setdefault("states", [active_state])
        scheme.setdefault("crops", ["all"])
        unique_schemes.append(scheme)
    schemes = unique_schemes
    kvk = KVK_CONTACTS.get(active_state, {"name": "Find your nearest Krishi Vigyan Kendra", "contact": "https://kvk.icar.gov.in/"})
    season_key = "rabi" if active_season.lower() == "rabi" else "kharif"
    crop_key = active_crop.replace(" ", "_")
    msp_value = MSP_SEASONS.get(season_key, {}).get(crop_key)
    msp_variants: List[Dict[str, Any]] = []
    if season_key == "kharif" and crop_key in {"rice", "paddy"}:
        msp_variants = [{"id": "common", "label": "Paddy (Common)", "value": 2441}, {"id": "grade_a", "label": "Paddy (Grade A)", "value": 2461}]
    elif season_key == "kharif" and crop_key == "cotton":
        msp_variants = [{"id": "medium", "label": "Cotton (Medium Staple)", "value": 8267}, {"id": "long", "label": "Cotton (Long Staple)", "value": 8667}]
    msp = {
        "value": msp_value,
        "msp": f"Rs. {msp_value:,} / quintal" if msp_value is not None else "Not listed for this season",
        "marketing_season": "RMS 2026-27" if season_key == "rabi" else "KMS 2026-27",
        "source_url": MSP_RABI_SOURCE if season_key == "rabi" else MSP_SOURCE,
        "variants": msp_variants,
        "trend": "Official announced MSP reference; procurement depends on notified crop, quality, dates, and local procurement arrangements." if msp_value is not None else "No MSP figure is listed for this crop in the selected season.",
    }
    mandi = fetch_live_mandi_prices(active_state, active_crop, district, market)

    if mandi.get("is_live") and mandi.get("summary", {}).get("display_price"):
        msp = {
            **msp,
            "live_modal_price": mandi["summary"]["display_price"],
        }

    return {
        "state": active_state,
        "season": active_season,
        "crop": active_crop,
        "msp": msp,
        "mandi": mandi,
        "schemes": schemes,
        "kvk": kvk,
        "market_tip": SEASONAL_MARKET_TIPS.get(active_season, SEASONAL_MARKET_TIPS["Kharif"]),
    }
