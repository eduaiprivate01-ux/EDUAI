"""Privacy-conscious local measurements for document extraction throughput."""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
METRICS_PATH = ROOT / "data" / "extraction_metrics.jsonl"
_LOCK = threading.Lock()
_MAX_LOG_BYTES = 2 * 1024 * 1024
_MAX_STORED_RECORDS = 5_000
_ALLOWED_FIELDS = {
    "timestamp_utc",
    "status",
    "file_type",
    "file_size_bytes",
    "duration_ms",
    "page_count",
    "character_count",
    "pages_per_second",
    "megabytes_per_second",
    "stage_durations_ms",
}


def append_extraction_record(values):
    """Save timings and counts only; omit filenames, extracted text, and user IDs."""
    values = dict(values or {})
    record = {
        key: value
        for key, value in values.items()
        if key in _ALLOWED_FIELDS
        and (value is None or isinstance(value, (str, int, float, bool, dict)))
    }
    record.setdefault("timestamp_utc", datetime.now(timezone.utc).isoformat())
    try:
        serialized = json.dumps(record, ensure_ascii=False, allow_nan=False)
        with _LOCK:
            METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
            if METRICS_PATH.exists() and METRICS_PATH.stat().st_size >= _MAX_LOG_BYTES:
                lines = METRICS_PATH.read_text(encoding="utf-8").splitlines()
                METRICS_PATH.write_text(
                    "\n".join(lines[-(_MAX_STORED_RECORDS - 1):]) + "\n",
                    encoding="utf-8",
                )
            with METRICS_PATH.open("a", encoding="utf-8", newline="\n") as metrics_file:
                metrics_file.write(serialized + "\n")
        return True
    except (OSError, TypeError, ValueError):
        return False


def load_recent_extraction_records(limit=200):
    """Read newest local extraction measurements, skipping malformed records."""
    try:
        limit = max(1, min(int(limit), 1_000))
        with _LOCK:
            lines = METRICS_PATH.read_text(encoding="utf-8").splitlines()
    except (OSError, ValueError):
        return []

    records = []
    for line in reversed(lines[-_MAX_STORED_RECORDS:]):
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(record, dict):
            records.append(record)
            if len(records) >= limit:
                break
    return records
