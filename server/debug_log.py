"""Opt-in operational metadata. Payloads and free-form text never enter this log."""
import json
import re
import threading
from datetime import datetime, timezone

LOCK = threading.Lock()
MAX_BYTES = 2 * 1024 * 1024
FIELDS = {'method', 'path', 'status', 'request_id', 'duration_ms', 'job_id', 'provider',
          'operation', 'previous_status', 'provider_status', 'action_count', 'warning_count',
          'error_type', 'count', 'layer_id', 'snippet_id', 'selected_count', 'target',
          'action', 'tag', 'input_type', 'enabled', 'source', 'command', 'success'}
TOKEN = re.compile(r'^[a-zA-Z0-9_./:{} -]{0,180}$')


def clean(event, details):
    event = event if isinstance(event, str) and re.fullmatch(r'[a-zA-Z0-9_.-]{1,80}', event) else 'invalid_event'
    safe = {}
    for key, value in (details.items() if isinstance(details, dict) else []):
        if key not in FIELDS:
            continue
        if isinstance(value, (bool, int)) or value is None:
            safe[key] = value
        elif isinstance(value, float):
            if value == value and abs(value) < 1e15:
                safe[key] = round(value, 2)
        elif isinstance(value, str) and TOKEN.fullmatch(value) and '://' not in value:
            safe[key] = value
    return {'time': datetime.now(timezone.utc).isoformat(), 'event': event, 'details': safe}


def record(directory, event, details=None):
    path = directory / 'debug.jsonl'
    line = json.dumps(clean(event, details), ensure_ascii=True) + '\n'
    try:
        with LOCK:
            if path.exists() and path.stat().st_size + len(line) > MAX_BYTES:
                path.replace(directory / 'debug.previous.jsonl')
            with path.open('a', encoding='utf-8') as stream:
                stream.write(line)
            path.chmod(0o600)
    except OSError:
        pass  # Diagnostics must never interrupt editing or an inference job.


def read(directory, limit=300):
    with LOCK:
        path = directory / 'debug.jsonl'
        if not path.exists():
            return []
        lines = path.read_text(encoding='utf-8').splitlines()[-max(1, min(limit, 1000)):]
    result = []
    for line in lines:
        try:
            result.append(json.loads(line))
        except ValueError:
            continue
    return result


def clear(directory):
    with LOCK:
        for name in ('debug.jsonl', 'debug.previous.jsonl'):
            (directory / name).unlink(missing_ok=True)
