from __future__ import annotations

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
example = root / ".env.example"
target = root / ".env"
if target.exists():
    raise SystemExit(".env already exists. Refusing to overwrite secrets.")

domain = input("Dominio HTTPS que apunta a la IP del VPS (ej. trader.midominio.com): ").strip()
if not domain or "/" in domain or " " in domain:
    raise SystemExit("Dominio inválido.")

values = {
    "APP_DOMAIN": domain,
    "APP_API_TOKEN": secrets.token_urlsafe(48),
    "FT_API_USERNAME": "cryptoai",
    "FT_API_PASSWORD": secrets.token_urlsafe(32),
    "FT_JWT_SECRET": secrets.token_urlsafe(48),
    "FT_WS_TOKEN": secrets.token_urlsafe(48),
}
lines = []
for line in example.read_text(encoding="utf-8").splitlines():
    if not line or line.lstrip().startswith("#") or "=" not in line:
        lines.append(line)
        continue
    key, _ = line.split("=", 1)
    if key in values:
        lines.append(f"{key}={values[key]}")
    else:
        lines.append(line)
target.write_text("\n".join(lines) + "\n", encoding="utf-8")
target.chmod(0o600)
print("Created .env with fresh secrets. Keep it private; do not upload it to GitHub.")
