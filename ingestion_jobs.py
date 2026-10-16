"""Owner-scoped background queues for document preview and vector indexing."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
from pathlib import Path
import threading
import time
import uuid

from ai_pipeline import ingest_document_bytes, prepare_document_preview
from extraction_metrics import append_extraction_record


# Preview work may include PDF rendering and OCR, so allow two independent
# document jobs. Heavy OCR/vision model inference remains protected by the
# pipeline's shared inference lock. Chroma writes remain serial to avoid SQLite
# write contention.
try:
    _PREVIEW_WORKERS = max(1, min(3, int(os.getenv("EDUAI_PREVIEW_WORKERS", "2"))))
except ValueError:
    _PREVIEW_WORKERS = 2
_PREVIEW_EXECUTOR = ThreadPoolExecutor(
    max_workers=_PREVIEW_WORKERS, thread_name_prefix="eduai-preview",
)
_INDEX_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="eduai-index")
_LOCK = threading.Lock()
_JOBS = {}
_MAX_ACTIVE_JOBS = 3


def _timestamp():
    return datetime.now(timezone.utc).isoformat()


def _new_job(owner_eduai_id, kind):
    job_id = str(uuid.uuid4())
    with _LOCK:
        if len(_JOBS) >= 100:
            for old_id in list(_JOBS):
                if _JOBS[old_id]["status"] in {"complete", "failed"}:
                    del _JOBS[old_id]
                    if len(_JOBS) < 80:
                        break
        active = sum(job["status"] in {"queued", "running"} for job in _JOBS.values())
        if active >= _MAX_ACTIVE_JOBS:
            raise RuntimeError("The document processing queue is full. Wait for a current job to finish.")
        _JOBS[job_id] = {
            "owner_eduai_id": str(owner_eduai_id),
            "kind": kind,
            "status": "queued",
            "stage": "Waiting for a document worker",
            "progress_percent": 0.0,
            "current_page": None,
            "page_total": None,
            "chunks": 0,
            "completed_units": 0,
            "total_units": None,
            "elapsed_seconds": 0.0,
            "stage_durations_ms": {},
            "result": None,
            "error": None,
            "updated_at": _timestamp(),
            "_started_perf": None,
            "_stage_started_perf": None,
        }
    return job_id


def _make_reporter(job_id):
    def report(event, chunks=None):
        # Accept the former (stage, chunks) callback form for compatibility with
        # any local integrations that still use it.
        if isinstance(event, dict):
            values = dict(event)
        else:
            values = {"stage": str(event), "chunks": int(chunks or 0)}
        stage = str(values.get("stage") or "Processing document")
        now = time.perf_counter()
        with _LOCK:
            job = _JOBS.get(job_id)
            if not job:
                return
            job["status"] = "running"
            if job["_started_perf"] is None:
                job["_started_perf"] = now
                job["_stage_started_perf"] = now
                job["_active_stage"] = stage
            elif stage != job.get("_active_stage"):
                previous = job.get("_active_stage")
                previous_started = job.get("_stage_started_perf")
                if previous and previous_started is not None:
                    durations = job["stage_durations_ms"]
                    durations[previous] = round(
                        durations.get(previous, 0.0) + (now - previous_started) * 1000,
                        2,
                    )
                job["_active_stage"] = stage
                job["_stage_started_perf"] = now
            job["stage"] = stage
            if "progress_percent" in values:
                try:
                    progress = max(0.0, min(100.0, float(values["progress_percent"])))
                    job["progress_percent"] = max(job["progress_percent"], progress)
                except (TypeError, ValueError):
                    pass
            if "current_page" in values:
                job["current_page"] = values["current_page"]
            if "page_total" in values:
                job["page_total"] = values["page_total"]
            if "chunks" in values:
                job["chunks"] = int(values["chunks"] or 0)
            if "completed_units" in values:
                job["completed_units"] = values["completed_units"]
            if "total_units" in values:
                job["total_units"] = values["total_units"]
            if "detail" in values:
                job["detail"] = str(values["detail"])
            if job["_started_perf"] is not None:
                job["elapsed_seconds"] = round(now - job["_started_perf"], 1)
            job["updated_at"] = _timestamp()

    return report


def _finish_stage_timer(job_id):
    now = time.perf_counter()
    with _LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return
        stage = job.get("_active_stage")
        started = job.get("_stage_started_perf")
        if stage and started is not None:
            durations = job["stage_durations_ms"]
            durations[stage] = round(
                durations.get(stage, 0.0) + (now - started) * 1000,
                2,
            )
        if job.get("_started_perf") is not None:
            job["elapsed_seconds"] = round(now - job["_started_perf"], 1)
        job["_stage_started_perf"] = None


def submit_document_preview(filename, file_bytes, *, owner_eduai_id):
    """Run slow extraction for the review screen in a progress-reporting worker."""
    job_id = _new_job(owner_eduai_id, "preview")
    report = _make_reporter(job_id)

    def run():
        started = time.perf_counter()
        report({"stage": "Starting document extraction", "progress_percent": 0})
        pages = None
        error_text = None
        try:
            pages = prepare_document_preview(
                filename, file_bytes, progress_callback=report,
            )
        except Exception as error:
            error_text = str(error)
            with _LOCK:
                _JOBS[job_id].update(
                    status="failed", stage="Extraction failed", error=error_text,
                    updated_at=_timestamp(),
                )
        else:
            with _LOCK:
                processed_page_total = int(_JOBS[job_id].get("page_total") or 0)
            processed_page_total = max(processed_page_total, len(pages))
            report({
                "stage": "Extraction complete",
                "progress_percent": 100,
                "current_page": processed_page_total,
                "page_total": processed_page_total,
            })
            with _LOCK:
                _JOBS[job_id].update(
                    status="complete", stage="Extraction complete", result=pages,
                    progress_percent=100.0,
                    updated_at=_timestamp(),
                )
        finally:
            _finish_stage_timer(job_id)
            elapsed = max(0.000001, time.perf_counter() - started)
            with _LOCK:
                job = _JOBS.get(job_id, {})
                durations = dict(job.get("stage_durations_ms", {}))
                processed_pages = int(job.get("page_total") or len(pages or []))
            page_count = max(processed_pages, len(pages or []))
            character_count = sum(len(page.get("text", "")) for page in pages or [])
            append_extraction_record({
                "status": "success" if pages is not None and error_text is None else "failed",
                "file_type": Path(str(filename)).suffix.lower().lstrip(".") or "unknown",
                "file_size_bytes": len(file_bytes),
                "duration_ms": round(elapsed * 1000, 2),
                "page_count": page_count,
                "character_count": character_count,
                "pages_per_second": round(page_count / elapsed, 3) if page_count else 0.0,
                "megabytes_per_second": round(len(file_bytes) / (1024 * 1024) / elapsed, 4),
                "stage_durations_ms": durations,
            })

    _PREVIEW_EXECUTOR.submit(run)
    return job_id


def submit_document_ingestion(filename, file_bytes, *, owner_eduai_id, role, **metadata):
    """Queue one upload for SQL/Chroma indexing and return its progress ID."""
    job_id = _new_job(owner_eduai_id, "index")
    report = _make_reporter(job_id)

    def run():
        report({"stage": "Starting indexing", "progress_percent": 0})
        try:
            result = ingest_document_bytes(
                filename,
                file_bytes,
                owner_eduai_id=owner_eduai_id,
                role=role,
                progress_callback=report,
                **metadata,
            )
        except Exception as error:
            with _LOCK:
                _JOBS[job_id].update(
                    status="failed", stage="Indexing failed", error=str(error),
                    updated_at=_timestamp(),
                )
        else:
            with _LOCK:
                _JOBS[job_id].update(
                    status="complete", stage="Complete", result=result,
                    progress_percent=100.0,
                    updated_at=_timestamp(),
                )
        finally:
            _finish_stage_timer(job_id)

    _INDEX_EXECUTOR.submit(run)
    return job_id


def get_ingestion_job(job_id, owner_eduai_id):
    """Return progress and results only to the user who submitted the file."""
    with _LOCK:
        job = _JOBS.get(str(job_id))
        if not job or job["owner_eduai_id"] != str(owner_eduai_id):
            return None
        result = {
            key: value
            for key, value in job.items()
            if key != "owner_eduai_id" and not key.startswith("_")
        }
        if job.get("_started_perf") is not None and job["status"] in {"queued", "running"}:
            result["elapsed_seconds"] = round(
                time.perf_counter() - job["_started_perf"], 1,
            )
        return result
