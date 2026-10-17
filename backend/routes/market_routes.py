from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.market_service import fetch_mandi_price_trend, get_market_overview
from utils.auth import role_required


market_bp = Blueprint("market_bp", __name__)


@market_bp.get("/api/market/overview")
@role_required("farmer", "admin")
def market_overview():
    state = request.args.get("state")
    crop = request.args.get("crop")
    season = request.args.get("season")
    district = request.args.get("district", "").strip()[:100]
    market = request.args.get("market", "").strip()[:120]

    try:
        return jsonify(get_market_overview(state=state, crop=crop, season=season, district=district, market=market)), 200
    except Exception:
        return jsonify({"error": "Failed to load market and government scheme information."}), 500


@market_bp.get("/api/market/trends")
@role_required("farmer", "admin")
def market_trends():
    state = request.args.get("state", "Maharashtra").strip()[:100]
    crop = request.args.get("crop", "wheat").strip()[:80]
    district = request.args.get("district", "").strip()[:100]
    market = request.args.get("market", "").strip()[:120]
    return jsonify(fetch_mandi_price_trend(state, crop, district, market)), 200
