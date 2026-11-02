import json
import os
import subprocess
import sys
from pathlib import Path


def test_config_generator_creates_spot_dry_run(tmp_path):
    env = os.environ.copy()
    env.update({
        "FREQTRADE_USER_DATA_DIR": str(tmp_path),
        "FT_API_USERNAME": "cryptoai",
        "FT_API_PASSWORD": "p" * 32,
        "FT_JWT_SECRET": "j" * 48,
        "FT_WS_TOKEN": "w" * 48,
        "EXCHANGE_NAME": "binance",
        "EXCHANGE_API_KEY": "",
        "EXCHANGE_SECRET": "",
    })
    script = Path(__file__).resolve().parents[1] / "server" / "generate_config.py"
    subprocess.run([sys.executable, str(script)], env=env, check=True, capture_output=True, text=True)
    config = json.loads((tmp_path / "config.json").read_text())
    assert config["dry_run"] is True
    assert config["trading_mode"] == "spot"
    assert config["dry_run_wallet"] == 1000
    assert config["initial_state"] == "stopped"
    assert config["force_entry_enable"] is False
    assert len(config["exchange"]["pair_whitelist"]) == 10
