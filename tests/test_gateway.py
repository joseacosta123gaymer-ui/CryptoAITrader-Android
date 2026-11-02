import os

from fastapi.testclient import TestClient

from server.app import main


def setup_env():
    os.environ["APP_API_TOKEN"] = "T" * 48
    os.environ["FT_API_USERNAME"] = "cryptoai"
    os.environ["FT_API_PASSWORD"] = "P" * 32
    os.environ["FT_API_URL"] = "http://freqtrade:8080"


def test_dashboard_requires_app_token():
    setup_env()
    client = TestClient(main.app)
    response = client.get("/api/dashboard")
    assert response.status_code == 401


def test_dashboard_returns_sanitized_data(monkeypatch):
    setup_env()

    async def fake_ft_request(settings, method, path, params=None):
        fixtures = {
            "status": [{"pair": "BTC/USDT"}],
            "profit": {"profit_all_coin": 2.5, "profit_all_percent": 2.5},
            "count": {"current": 1, "max": 3},
            "balance": {"total": 950.0, "stake": "USDT"},
            "show_config": {
                "state": "running", "dry_run": True, "exchange": "binance",
                "stake_currency": "USDT", "timeframe": "5m", "strategy": "CryptoAIBaseline",
                "max_open_trades": 3, "api_server": {"password": "must-not-leak"}
            },
            "version": {"version": "test"},
        }
        return fixtures[path]

    monkeypatch.setattr(main, "ft_request", fake_ft_request)
    client = TestClient(main.app)
    response = client.get("/api/dashboard", headers={"Authorization": f"Bearer {'T' * 48}"})
    assert response.status_code == 200
    data = response.json()
    assert data["bot"]["dry_run"] is True
    assert data["bot"]["exchange"] == "binance"
    assert "api_server" not in data["bot"]
    assert data["count"]["current"] == 1


def test_start_is_blocked_when_not_dry_run(monkeypatch):
    setup_env()
    calls = []

    async def fake_ft_request(settings, method, path, params=None):
        calls.append((method, path))
        if path == "show_config":
            return {"dry_run": False}
        return {"status": "started"}

    monkeypatch.setattr(main, "ft_request", fake_ft_request)
    client = TestClient(main.app)
    response = client.post("/api/bot/start", headers={"Authorization": f"Bearer {'T' * 48}"})
    assert response.status_code == 409
    assert calls == [("GET", "show_config")]
