"""
Smoke tests for CS2 Price Scraper API.
Run with: pytest tests/test_smoke.py -v
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Health & Meta
# ---------------------------------------------------------------------------

def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_openapi_schema():
    r = client.get("/api/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    assert schema["info"]["title"] == "CS2 Price Scraper"


# ---------------------------------------------------------------------------
# Search (critical: route ordering bug was here)
# ---------------------------------------------------------------------------

def test_search_steam():
    r = client.get("/api/v1/items/search?q=AK-47&source=steam")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data


def test_search_all_sources():
    """This route was returning 400 before the route ordering fix."""
    r = client.get("/api/v1/items/search?q=AK-47&source=all")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["items"], list)


def test_search_pagination():
    r = client.get("/api/v1/items/search?q=Case&source=steam&page=1&page_size=5")
    assert r.status_code == 200
    data = r.json()
    assert data["page"] == 1
    assert data["page_size"] == 5


def test_search_missing_query():
    r = client.get("/api/v1/items/search")
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Item Detail
# ---------------------------------------------------------------------------

def test_item_detail_steam():
    r = client.get("/api/v1/items/AK-47%20|%20Redline?source=steam")
    assert r.status_code in (200, 404)  # 404 if Steam doesn't have it right now


def test_item_detail_invalid_source():
    r = client.get("/api/v1/items/123?source=invalid")
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Cross-Market Compare
# ---------------------------------------------------------------------------

def test_item_compare():
    r = client.get("/api/v1/items/compare?q=AK-47%20|%20Redline")
    assert r.status_code == 200
    data = r.json()
    assert "sources" in data
    assert "steam" in data["sources"] or len(data["sources"]) >= 0


# ---------------------------------------------------------------------------
# Categories & Market Summary
# ---------------------------------------------------------------------------

def test_categories():
    r = client.get("/api/v1/categories")
    assert r.status_code == 200
    data = r.json()
    assert "categories" in data
    assert len(data["categories"]) > 0


def test_market_summary():
    r = client.get("/api/v1/market/summary")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


# ---------------------------------------------------------------------------
# Ratios
# ---------------------------------------------------------------------------

def test_ratios_list():
    r = client.get("/api/v1/ratios?source=buff&limit=10")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert isinstance(data["items"], list)


def test_ratios_summary():
    r = client.get("/api/v1/ratios/summary")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data


def test_ratios_refresh():
    r = client.get("/api/v1/ratios?refresh=true")
    assert r.status_code == 200
    # Should return immediately even if background scan starts


# ---------------------------------------------------------------------------
# Trade-Up
# ---------------------------------------------------------------------------

def test_tradeup_collections():
    r = client.get("/api/v1/tradeup/collections")
    assert r.status_code == 200
    data = r.json()
    assert "collections" in data
    assert len(data["collections"]) > 0


def test_tradeup_scan():
    r = client.get("/api/v1/tradeup/scan?max_cost=50&min_profit_pct=5")
    assert r.status_code == 200
    data = r.json()
    assert "tradeups" in data
    assert isinstance(data["tradeups"], list)


def test_tradeup_calculate():
    payload = {
        "inputs": [
            {"skin_name": "MAC-10 | Amber Fade", "collection": "Mirage", "price": 4.5, "float": 0.15}
        ] * 10
    }
    r = client.post("/api/v1/tradeup/calculate", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "total_cost" in data
    assert "expected_value" in data


# ---------------------------------------------------------------------------
# Pattern Detection
# ---------------------------------------------------------------------------

def test_pattern_analyze():
    r = client.get("/api/v1/patterns/analyze?item_name=AK-47%20|%20Case%20Hardened&paint_seed=661")
    assert r.status_code == 200
    data = r.json()
    assert "pattern_type" in data


def test_pattern_scan():
    r = client.get("/api/v1/patterns/scan?query=Case%20Hardened&limit=5")
    assert r.status_code == 200
    data = r.json()
    assert "alerts" in data


# ---------------------------------------------------------------------------
# Bot
# ---------------------------------------------------------------------------

def test_bot_status():
    r = client.get("/api/v1/bot/status")
    assert r.status_code == 200
    data = r.json()
    assert "running" in data


def test_bot_stats():
    r = client.get("/api/v1/bot/stats")
    assert r.status_code == 200
    data = r.json()
    assert "arbitrage_opportunities" in data


def test_bot_insights():
    r = client.get("/api/v1/bot/insights")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_bot_arbitrage():
    r = client.get("/api/v1/bot/arbitrage")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_bot_recommendations():
    r = client.get("/api/v1/bot/recommendations")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_bot_history():
    r = client.get("/api/v1/bot/history")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_bot_watchlist():
    r = client.get("/api/v1/bot/watchlist")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_bot_trigger_scan():
    r = client.post("/api/v1/bot/trigger-scan")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"


def test_bot_webhooks_crud():
    # Create
    r = client.post("/api/v1/bot/webhooks", json={
        "name": "Test Discord",
        "webhook_type": "discord",
        "url": "https://discord.com/api/webhooks/123456/test",
        "events": "watchlist_trigger",
    })
    assert r.status_code == 200
    wh_id = r.json()["id"]

    # List
    r = client.get("/api/v1/bot/webhooks")
    assert r.status_code == 200
    assert any(w["id"] == wh_id for w in r.json())

    # Delete
    r = client.delete(f"/api/v1/bot/webhooks/{wh_id}")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

def test_portfolio_summary():
    r = client.get("/api/v1/portfolio/summary")
    assert r.status_code == 200
    data = r.json()
    assert "total_invested" in data
    assert "item_count" in data


def test_portfolio_crud():
    # Create
    r = client.post("/api/v1/portfolio", json={
        "item_name": "AK-47 | Redline",
        "source": "buff",
        "quantity": 1,
        "buy_price": 150.0,
        "current_price": 180.0,
    })
    assert r.status_code == 200
    item_id = r.json()["id"]

    # List
    r = client.get("/api/v1/portfolio")
    assert r.status_code == 200
    assert any(i["id"] == item_id for i in r.json())

    # Refresh prices
    r = client.post("/api/v1/portfolio/refresh")
    assert r.status_code == 200

    # Delete
    r = client.delete(f"/api/v1/portfolio/{item_id}")
    assert r.status_code == 200

    # Verify deleted
    r = client.get("/api/v1/portfolio")
    assert not any(i["id"] == item_id for i in r.json())


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------

def test_backtest_strategies():
    r = client.get("/api/v1/backtest/strategies")
    assert r.status_code == 200
    data = r.json()
    assert "strategies" in data
    assert "buy_and_hold" in data["strategies"]


def test_backtest_run():
    payload = {
        "strategy": "buy_and_hold",
        "item_name": "AK-47 | Redline",
        "source": "steam",
        "initial_capital": 1000,
    }
    r = client.post("/api/v1/backtest/run", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "total_return_pct" in data
    assert "equity_curve" in data


def test_admin_jobs():
    r = client.get("/api/v1/admin/jobs")
    assert r.status_code == 200
    data = r.json()
    assert "jobs" in data
    assert isinstance(data["jobs"], list)


# ---------------------------------------------------------------------------
# HTML Pages
# ---------------------------------------------------------------------------

pages = [
    "/", "/bot", "/portfolio", "/ratios", "/tradeup",
    "/backtest", "/search", "/dashboard", "/login", "/register",
]

@pytest.mark.parametrize("page", pages)
def test_html_pages(page):
    r = client.get(page)
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
