#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm install
printf '\nReady. Run python3 scripts/dev.py and open http://127.0.0.1:5174\n'
