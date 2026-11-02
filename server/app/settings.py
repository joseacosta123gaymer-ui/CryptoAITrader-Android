from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_api_token: str
    ft_api_url: str
    ft_api_username: str
    ft_api_password: str

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("APP_API_TOKEN", "").strip()
        if len(token) < 32:
            raise RuntimeError("APP_API_TOKEN must be set to a random value of at least 32 characters")
        username = os.getenv("FT_API_USERNAME", "").strip()
        password = os.getenv("FT_API_PASSWORD", "").strip()
        if not username or len(password) < 20:
            raise RuntimeError("FT_API_USERNAME and a strong FT_API_PASSWORD are required")
        return cls(
            app_api_token=token,
            ft_api_url=os.getenv("FT_API_URL", "http://freqtrade:8080").rstrip("/"),
            ft_api_username=username,
            ft_api_password=password,
        )
