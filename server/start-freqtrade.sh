#!/usr/bin/env bash
set -euo pipefail
python /opt/generate_config.py
exec freqtrade trade --config /freqtrade/user_data/config.json --userdir /freqtrade/user_data --strategy CryptoAIBaseline --logfile /freqtrade/user_data/logs/freqtrade.log
