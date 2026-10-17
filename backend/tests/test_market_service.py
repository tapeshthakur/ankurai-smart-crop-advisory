from services import market_service


def test_agmarknet_report_is_normalized_to_market_records(monkeypatch):
    filters = {
        "state_data": [{"state_id": 20, "state_name": "Maharashtra"}],
        "district_data": [{"id": 12, "state_id": 20, "district_name": "Pune"}],
        "market_data": [{"id": 34, "mkt_name": "Pune APMC", "state_id": 20, "district_id": 12}],
    }
    report = {
        "success": True,
        "commodityGroups": [{
            "commodities": [{
                "commodityName": "Rice",
                "markets": [{
                    "marketCenter": "Pune APMC",
                    "data": [{"variety": "Other", "grade": "FAQ", "minimumPrice": 4000, "maximumPrice": 4500, "modalPrice": 4250, "unitOfPrice": "Rs./Quintal"}],
                }],
            }],
        }],
    }
    monkeypatch.setattr(market_service, "_MANDI_CACHE", {})
    monkeypatch.setattr(market_service, "_AGMARKNET_FILTERS_CACHE", {"expires_at": 10**20, "data": filters})
    monkeypatch.setattr(market_service, "_request_agmarknet", lambda *args, **kwargs: report)

    result = market_service.fetch_live_mandi_prices("Maharashtra", "rice")

    assert result["is_live"] is True
    assert result["source"].startswith("AGMARKNET 2.0")
    assert result["records"][0]["district"] == "Pune"
    assert result["records"][0]["modal_price"] == 4250
    assert result["summary"]["record_count"] == 1


def test_agmarknet_failure_is_reported_without_mislabeling_fallback(monkeypatch):
    monkeypatch.setattr(market_service, "_MANDI_CACHE", {})
    monkeypatch.setattr(market_service, "_AGMARKNET_FILTERS_CACHE", {"expires_at": 0, "data": None})

    def unavailable(*args, **kwargs):
        raise TimeoutError("upstream timed out")

    monkeypatch.setattr(market_service, "_request_agmarknet", unavailable)
    result = market_service.fetch_live_mandi_prices("Maharashtra", "rice")

    assert result["is_live"] is False
    assert "could not be reached" in result["message"]
    assert result["errors"] == ["upstream timed out"]


def test_market_uses_national_live_rows_when_selected_state_has_none(monkeypatch):
    filters = {
        "state_data": [{"state_id": 20, "state_name": "Maharashtra"}],
        "district_data": [],
        "market_data": [],
        "cmdt_data": [{"cmdt_id": 41, "cmdt_name": "Coffee", "cmdt_group_id": 9}],
    }
    monkeypatch.setattr(market_service, "_MANDI_CACHE", {})
    monkeypatch.setattr(market_service, "_AGMARKNET_FILTERS_CACHE", {"expires_at": 10**20, "data": filters})

    def report(path, params, timeout_seconds):
        if path.endswith("daily-report-state"):
            return {"success": True, "commodityGroups": []}
        return {
            "success": True,
            "states": [{"stateName": "Keralam", "markets": [{"marketName": "Kalpetta Market", "data": [{"minimumPrice": 20000, "maximumPrice": 22000, "modalPrice": 21000}]}]}],
        }

    monkeypatch.setattr(market_service, "_request_agmarknet", report)
    result = market_service.fetch_live_mandi_prices("Maharashtra", "coffee")

    assert result["is_live"] is True
    assert result["scope"] == "national"
    assert result["records"][0]["state"] == "Keralam"


def test_market_overview_uses_current_season_msp_and_does_not_fake_state_schemes(monkeypatch):
    monkeypatch.setattr(market_service, "fetch_live_mandi_prices", lambda *args, **kwargs: {"is_live": False, "records": []})

    rabi = market_service.get_market_overview("Goa", "wheat", "Rabi")
    kharif = market_service.get_market_overview("Goa", "rice", "Kharif")

    assert rabi["msp"]["value"] == 2585
    assert rabi["msp"]["marketing_season"] == "RMS 2026-27"
    assert kharif["msp"]["value"] == 2441
    assert len(rabi["schemes"]) == 2
    assert all("Goa" not in scheme.get("states", []) for scheme in rabi["schemes"])
    assert rabi["kvk"]["contact"].startswith("https://kvk.icar.gov.in/")


def test_selected_mandi_filter_scopes_live_rows(monkeypatch):
    filters = {
        "state_data": [{"state_id": 20, "state_name": "Maharashtra"}],
        "district_data": [{"id": 12, "state_id": 20, "district_name": "Pune"}, {"id": 13, "state_id": 20, "district_name": "Nashik"}],
        "market_data": [{"id": 34, "mkt_name": "Pune APMC", "state_id": 20, "district_id": 12}, {"id": 35, "mkt_name": "Nashik APMC", "state_id": 20, "district_id": 13}],
    }
    report = {"success": True, "commodityGroups": [{"commodities": [{"commodityName": "Rice", "markets": [
        {"marketCenter": "Pune APMC", "data": [{"modalPrice": 4000}]},
        {"marketCenter": "Nashik APMC", "data": [{"modalPrice": 4200}]},
    ]}]}]}
    monkeypatch.setattr(market_service, "_MANDI_CACHE", {})
    monkeypatch.setattr(market_service, "_AGMARKNET_FILTERS_CACHE", {"expires_at": 10**20, "data": filters})
    monkeypatch.setattr(market_service, "_request_agmarknet", lambda *args, **kwargs: report)

    result = market_service.fetch_live_mandi_prices("Maharashtra", "rice", "Pune", "Pune APMC")

    assert result["is_live"] is True
    assert [row["market"] for row in result["records"]] == ["Pune APMC"]
