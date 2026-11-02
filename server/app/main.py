from __future__ import annotations

import asyncio
import hmac
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .settings import Settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("crypto_ai_trader.gateway")

app = FastAPI(
    title="Crypto AI Trader Gateway",
    version="0.2.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
bearer = HTTPBearer(auto_error=False)


def get_settings() -> Settings:
    try:
        return Settings.from_env()
    except RuntimeError as exc:
        logger.error("Gateway configuration error: %s", exc)
        raise HTTPException(status_code=503, detail="Server is not configured") from exc


async def require_app_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    settings: Settings = Depends(get_settings),
) -> Settings:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required")
    if not hmac.compare_digest(credentials.credentials, settings.app_api_token):
        raise HTTPException(status_code=401, detail="Invalid access token")
    return settings


async def ft_request(
    settings: Settings,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
) -> Any:
    """Call only explicitly selected Freqtrade API endpoints over the private Docker network."""
    url = f"{settings.ft_api_url}/api/v1/{path.lstrip('/')}"
    auth = httpx.BasicAuth(settings.ft_api_username, settings.ft_api_password)
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0), auth=auth) as client:
            response = await client.request(method, url, params=params)
            response.raise_for_status()
            if response.status_code == 204 or not response.content:
                return {"status": "ok"}
            return response.json()
    except httpx.TimeoutException as exc:
        logger.warning("Freqtrade API timeout for endpoint %s", path)
        raise HTTPException(status_code=504, detail="Trading engine timed out") from exc
    except httpx.HTTPStatusError as exc:
        # Do not return upstream response bodies: they may contain internal details.
        logger.warning("Freqtrade API returned HTTP %s for endpoint %s", exc.response.status_code, path)
        raise HTTPException(status_code=502, detail="Trading engine rejected the request") from exc
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Freqtrade API unavailable for endpoint %s", path)
        raise HTTPException(status_code=502, detail="Trading engine is unavailable") from exc


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Non-sensitive liveness endpoint for the reverse proxy."""
    return {"status": "ok", "service": "crypto-ai-trader-gateway"}


@app.get("/api/dashboard")
async def dashboard(settings: Settings = Depends(require_app_token)) -> dict[str, Any]:
    status_data, profit, count, balance, show_config, version = await asyncio.gather(
        ft_request(settings, "GET", "status"),
        ft_request(settings, "GET", "profit"),
        ft_request(settings, "GET", "count"),
        ft_request(settings, "GET", "balance"),
        ft_request(settings, "GET", "show_config"),
        ft_request(settings, "GET", "version"),
    )
    # Return only non-secret configuration fields to the Android client.
    safe_config = {
        "state": show_config.get("state", "unknown"),
        "dry_run": bool(show_config.get("dry_run", False)),
        "exchange": show_config.get("exchange", "unknown"),
        "stake_currency": show_config.get("stake_currency", "USDT"),
        "timeframe": show_config.get("timeframe", "5m"),
        "strategy": show_config.get("strategy", "unknown"),
        "max_open_trades": show_config.get("max_open_trades", 0),
    }
    return {
        "updated_at": datetime.now(UTC).isoformat(),
        "bot": {
            "reachable": True,
            "version": version.get("version", "unknown"),
            **safe_config,
        },
        "profit": profit,
        "count": count,
        "balance": balance,
        "open_trades": status_data if isinstance(status_data, list) else [],
    }


@app.get("/api/trades")
async def trades(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10000),
    settings: Settings = Depends(require_app_token),
) -> Any:
    return await ft_request(settings, "GET", "trades", params={"limit": limit, "offset": offset})


@app.get("/api/pairs")
async def pairs(settings: Settings = Depends(require_app_token)) -> Any:
    return await ft_request(settings, "GET", "whitelist")


@app.get("/api/candles")
async def candles(
    pair: str = Query(min_length=3, max_length=32),
    timeframe: str = Query(default="5m", pattern="^(1m|5m|15m|30m|1h|4h|1d)$"),
    limit: int = Query(default=100, ge=20, le=500),
    settings: Settings = Depends(require_app_token),
) -> Any:
    allowed = await ft_request(settings, "GET", "whitelist")
    allowed_pairs = allowed.get("whitelist", []) if isinstance(allowed, dict) else []
    if pair not in allowed_pairs:
        raise HTTPException(status_code=400, detail="Pair is not enabled in the bot whitelist")
    return await ft_request(
        settings,
        "GET",
        "pair_candles",
        params={"pair": pair, "timeframe": timeframe, "limit": limit},
    )


async def ensure_dry_run(settings: Settings) -> None:
    config = await ft_request(settings, "GET", "show_config")
    if config.get("dry_run") is not True:
        raise HTTPException(status_code=409, detail="Mobile control is locked unless Freqtrade is in Dry-run mode")


@app.post("/api/bot/start")
async def bot_start(settings: Settings = Depends(require_app_token)) -> Any:
    await ensure_dry_run(settings)
    return await ft_request(settings, "POST", "start")


@app.post("/api/bot/pause")
async def bot_pause(settings: Settings = Depends(require_app_token)) -> Any:
    await ensure_dry_run(settings)
    return await ft_request(settings, "POST", "pause")


@app.post("/api/bot/stop")
async def bot_stop(settings: Settings = Depends(require_app_token)) -> Any:
    await ensure_dry_run(settings)
    return await ft_request(settings, "POST", "stop")
