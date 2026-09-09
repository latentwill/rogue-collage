#!/usr/bin/env python3
"""Run the local API and web editor together; stop both cleanly on Ctrl-C."""
from pathlib import Path
import os
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
python = ROOT / '.venv' / 'bin' / 'python'
if not python.exists() or not (ROOT / 'node_modules').exists():
    sys.exit('Run ./scripts/setup.sh first to install the local dependencies.')
children = []

def shutdown():
    for child in children:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
    for child in children:
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()

def stop(*_):
    raise KeyboardInterrupt

for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, stop)
exit_code = 0
try:
    children.append(subprocess.Popen([str(python), '-m', 'uvicorn', 'server.app:app', '--host', '127.0.0.1', '--port', '8765', '--no-access-log'], start_new_session=True))
    children.append(subprocess.Popen(['npm', 'run', 'dev', '--', '--port', '5174', '--strictPort'], start_new_session=True))
    print('\nRogue Collage: http://127.0.0.1:5174\nPress Ctrl-C to stop both services.\n', flush=True)
    while all(child.poll() is None for child in children):
        time.sleep(.5)
    exit_code = next((child.returncode for child in children if child.returncode is not None), 1)
except KeyboardInterrupt:
    pass
finally:
    shutdown()
sys.exit(exit_code)
