"""Small, privacy-conscious local log for RAG latency measurements."""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
METRICS_PATH = ROOT / "data" / "performance_metrics.jsonl"
_LOCK = threading.Lock()
_MAX_LOG_BYTES = 2 * 1024 * 1024
_MAX_STORED_RECORDS = 5_000
_ALLOWED_FIELDS = {
    "timestamp_utc",
    "status",
    "retrieval_ms",
    "vector_search_ms",
    "authorization_ms",
    "fusion_ms",
    "reranker_ms",
    "generation_ms",
    "first_output_ms",
    "total_ms",
    "candidate_count",
    "retrieved_chunks",
    "reranker_enabled",
    "reranker_ready",
    "reranker_used",
    "response_chars",
    "response_words",
    "characters_per_second",
    "max_output_tokens",
    "answer_style",
    "knowledge_mode",
    "conversation_context_used",
    "contextual_retrieval_used",
}


def append_performance_record(values):
    """Append timings only; never store prompts, answers, or account identifiers."""
    record = {
        key: value
        for key, value in dict(values or {}).items()
        if key in _ALLOWED_FIELDS
        and (value is None or isinstance(value, (str, int, float, bool)))
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
        # Telemetry should never prevent the tutor from answering.
        return False


def load_recent_performance(limit=200):
    """Return the newest local latency records, without exposing chat content."""
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
