from __future__ import annotations

import json
import os
import secrets
from pathlib import Path

USER_DATA = Path(os.environ.get("FREQTRADE_USER_DATA_DIR", "/freqtrade/user_data"))
USER_DATA.mkdir(parents=True, exist_ok=True)
(USER_DATA / "strategies").mkdir(parents=True, exist_ok=True)
(USER_DATA / "logs").mkdir(parents=True, exist_ok=True)

api_user = os.environ.get("FT_API_USERNAME", "").strip()
api_password = os.environ.get("FT_API_PASSWORD", "").strip()
jwt_secret = os.environ.get("FT_JWT_SECRET", "").strip()
ws_token = os.environ.get("FT_WS_TOKEN", "").strip()
if not api_user or len(api_password) < 20 or len(jwt_secret) < 32 or len(ws_token) < 32:
    raise SystemExit("Missing/weak FT_API_USERNAME, FT_API_PASSWORD, FT_JWT_SECRET or FT_WS_TOKEN in .env")

exchange_name = os.environ.get("EXCHANGE_NAME", "binance").strip().lower()
exchange_key = os.environ.get("EXCHANGE_API_KEY", "")
exchange_secret = os.environ.get("EXCHANGE_SECRET", "")

config = {
    "$schema": "https://schema.freqtrade.io/schema.json",
    "max_open_trades": 3,
    "stake_currency": "USDT",
    "stake_amount": 50,
    "tradable_balance_ratio": 0.95,
    "fiat_display_currency": "USD",
    "dry_run": True,
    "dry_run_wallet": 1000,
    "cancel_open_orders_on_exit": True,
    "timeframe": "5m",
    "trailing_stop": False,
    "use_exit_signal": True,
    "exit_profit_only": False,
    "trading_mode": "spot",
    "minimal_roi": {"0": 0.015},
    "stoploss": -0.02,
    "unfilledtimeout": {"entry": 10, "exit": 10, "exit_timeout_count": 0, "unit": "minutes"},
    "entry_pricing": {"price_side": "same", "use_order_book": True, "order_book_top": 1},
    "exit_pricing": {"price_side": "same", "use_order_book": True, "order_book_top": 1},
    "order_types": {
        "entry": "limit",
        "exit": "limit",
        "emergency_exit": "market",
        "force_exit": "market",
        "force_entry": "market",
        "stoploss": "market",
        "stoploss_on_exchange": False,
        "stoploss_price_type": "last",
        "stoploss_on_exchange_interval": 60,
        "stoploss_on_exchange_limit_ratio": 0.99,
    },
    "order_time_in_force": {"entry": "GTC", "exit": "GTC"},
    "exchange": {
        "name": exchange_name,
        "key": exchange_key,
        "secret": exchange_secret,
        "ccxt_config": {},
        "ccxt_async_config": {},
        "pair_whitelist": [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
            "ADA/USDT", "DOGE/USDT", "LINK/USDT", "LTC/USDT", "AVAX/USDT"
        ],
        "pair_blacklist": [".*UP/USDT", ".*DOWN/USDT"],
    },
    "pairlists": [{"method": "StaticPairList"}],
    "api_server": {
        "enabled": True,
        "listen_ip_address": "0.0.0.0",
        "listen_port": 8080,
        "verbosity": "error",
        "enable_openapi": False,
        "jwt_secret_key": jwt_secret,
        "CORS_origins": [],
        "username": api_user,
        "password": api_password,
        "ws_token": ws_token,
    },
    "telegram": {"enabled": False, "token": "", "chat_id": ""},
    "bot_name": "Crypto AI Trader (Dry-run)",
    "db_url": "sqlite:////freqtrade/user_data/tradesv3.sqlite",
    "initial_state": "stopped",
    "force_entry_enable": False,
    "strategy": "CryptoAIBaseline",
    "strategy_path": "/freqtrade/user_data/strategies",
    "internals": {"process_throttle_secs": 5, "heartbeat_interval": 60},
}

path = USER_DATA / "config.json"
tmp_path = USER_DATA / "config.json.tmp"
tmp_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
os.replace(tmp_path, path)
print(f"Generated safe Dry-run configuration at {path}")
