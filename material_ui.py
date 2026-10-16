"""Shared material review, upload, indexing-progress, and library UI."""

import hashlib

import streamlit as st

from ai_pipeline import MAX_VISION_PAGES, delete_document, model_status
from database import ensure_schema, is_configured
from education_data import catalog_values, list_documents
from ingestion_jobs import (
    get_ingestion_job,
    submit_document_ingestion,
    submit_document_preview,
)


def _format_duration(seconds):
    seconds = max(0, int(seconds or 0))
    minutes, remaining_seconds = divmod(seconds, 60)
    if minutes:
        return f"{minutes}m {remaining_seconds}s"
    return f"{remaining_seconds}s"


def _render_job_progress(job_id, owner, *, job_kind, current_signature=None):
    @st.fragment(run_every=1)
    def render():
        job = get_ingestion_job(job_id, owner)
        if not job:
            st.warning("This document job is no longer available. The app may have restarted; submit it again.")
            return

        progress = max(0.0, min(100.0, float(job.get("progress_percent", 0) or 0)))
        st.progress(progress / 100, text=f"{progress:.0f}% · {job.get('stage', 'Processing document')}")
        elapsed = float(job.get("elapsed_seconds", 0) or 0)
        status_columns = st.columns(3)
        status_columns[0].caption(f"Elapsed: {_format_duration(elapsed)}")
        if progress >= 2 and elapsed >= 2 and job.get("status") in {"queued", "running"}:
            remaining = elapsed * (100 - progress) / progress
            status_columns[1].caption(f"Estimated time remaining: about {_format_duration(remaining)}")
        else:
            status_columns[1].caption("Estimating remaining time…")
        page = job.get("current_page")
        page_total = job.get("page_total")
        if page is not None and page_total:
            status_columns[2].caption(f"Working on page/item {page} of {page_total}")
        elif page is not None:
            status_columns[2].caption(f"Working on {page}")
        elif job.get("completed_units") and job.get("total_units"):
            status_columns[2].caption(
                f"Items: {job['completed_units']} of {job['total_units']}"
            )
        elif job.get("chunks"):
            status_columns[2].caption(f"Chunks processed: {job['chunks']:,}")

        if job.get("detail"):
            st.caption(job["detail"])

        if job["status"] == "complete":
            if job_kind == "preview":
                expected_signature = st.session_state.get("material_preview_job_signature")
                if expected_signature and expected_signature == current_signature:
                    pages = job.get("result") or []
                    st.session_state.material_review_pages = pages
                    st.session_state.material_review_signature = expected_signature
                    described = sum(
                        page.get("metadata", {}).get("diagram_vision_status") == "described"
                        for page in pages
                    )
                    statuses = {
                        page.get("metadata", {}).get("diagram_vision_status")
                        for page in pages
                    }
                    st.session_state["material_extraction_result_message"] = (
                        f"Extracted text from {len(pages)} page(s); added visual descriptions on "
                        f"{described} page(s). Review and correct it below before indexing."
                    )
                    st.session_state["material_extraction_statuses"] = statuses
                else:
                    st.session_state["material_extraction_result_message"] = (
                        "Extraction finished for the previous file selection. Select that file again to review its text."
                    )
                st.session_state.pop("active_preview_job_id", None)
                st.session_state.pop("material_preview_job_signature", None)
                st.rerun()
            else:
                result = job.get("result") or {}
                st.success(
                    f"Indexed {result.get('title', 'material')} into "
                    f"{result.get('chunk_count', 0)} chunks."
                )
                if st.button("Dismiss indexing status", key=f"dismiss_job_{job_id}"):
                    st.session_state.pop("active_ingestion_job_id", None)
                    st.rerun()
        elif job["status"] == "failed":
            st.error(job.get("error") or "Document processing failed.")
            if st.button("Dismiss failed job", key=f"dismiss_failed_job_{job_id}"):
                state_key = "active_preview_job_id" if job_kind == "preview" else "active_ingestion_job_id"
                st.session_state.pop(state_key, None)
                st.session_state.pop("material_preview_job_signature", None)
                st.rerun()

    render()


def _render_ingestion_progress(job_id, owner):
    _render_job_progress(job_id, owner, job_kind="index")


def render_material_manager():
    owner = st.session_state.get("user_id")
    role = st.session_state.get("role", "Student")
    if not is_configured():
        st.error("MySQL is not configured. Connect the EduAI database before adding materials.")
        return
    try:
        ensure_schema()
    except Exception as error:
        st.error(f"Could not connect to MySQL: {error}")
        return

    is_staff = role in {"Admin", "Teacher"}
    models = model_status()
    with st.container(border=True):
        st.markdown("#### Add study material")
        st.caption(
            "Teacher and admin uploads are shared with the course. Student uploads stay private to the uploader."
            if is_staff else
            "Your uploads are private to your account and can be used by your tutor."
        )
        st.caption(
            "Scanned PDFs and text in embedded PDF/DOCX figures are OCR-processed, including when a PDF page also has selectable text. "
            "A lightweight diagram check selects likely figure pages/images before the local vision model describes diagram types, labels, arrows, and relationships. "
            "All generated descriptions can be reviewed and corrected before indexing. "
            "PDF vector drawings are checked too; vision is never run on every page just because EDUAI_VISION_PDF_MODE=all is set."
        )
        if models["vision_enabled"] and not models["vision_ready"]:
            st.info(
                "Diagram understanding is not ready yet. Install Ollama, then run "
                "`.\\download_diagram_model.ps1` once. OCR will still extract readable labels."
            )
        elif not models["vision_enabled"]:
            st.caption("Diagram understanding is disabled in .env (EDUAI_ENABLE_DIAGRAM_VISION=false).")

        try:
            courses = catalog_values("Course")
            if not courses:
                st.info("Add a course, semester, and subject in Academic structure before uploading material.")
                return
            course = st.selectbox("Course", courses, index=None, placeholder="Select a course", key="material_course")
            semesters = catalog_values("Semester", course=course) if course else []
            semester = st.selectbox(
                "Semester", semesters, index=None, placeholder="Select a semester",
                key=f"material_semester_{course}", disabled=not semesters,
            )
            subjects = catalog_values("Subject", course=course, semester=semester) if course and semester else []
            subject = st.selectbox(
                "Subject", subjects, index=None, placeholder="Select a subject",
                key=f"material_subject_{course}_{semester}", disabled=not subjects,
            )
        except Exception as error:
            st.error(f"Could not load the academic structure: {error}")
            return

        if course and not semesters:
            st.info(f"No semesters are defined for {course}. Add them in Academic structure.")
        if course and semester and not subjects:
            st.info(f"No subjects are defined for {course} · {semester}. Add them in Academic structure.")
        type_column, title_column = st.columns(2)
        with type_column:
            document_type = st.selectbox("Material type", ["Study material", "Syllabus", "Assignment"], key="material_type")
        with title_column:
            title = st.text_input("Display title (optional)", key="material_title")
        uploaded = st.file_uploader(
            "Choose PDF, DOCX, TXT, or handwriting image",
            type=["pdf", "docx", "txt", "bmp", "jpeg", "jpg", "png", "tif", "tiff", "webp"],
            key="material_upload",
        )
        st.caption(
            "Extraction runs in the background. The progress display reports the current page or image, "
            "elapsed time, and an estimated time remaining; OCR and diagram-model startup can change the estimate."
        )

        signature = None
        file_bytes = None
        if uploaded is not None:
            file_bytes = uploaded.getvalue()
            signature = hashlib.sha256(uploaded.name.encode("utf-8") + file_bytes).hexdigest()
            if st.session_state.get("material_review_signature") != signature:
                st.session_state.pop("material_review_pages", None)
                st.session_state["material_review_signature"] = signature

        can_preview = bool(course and semester and subject and uploaded is not None)
        active_preview_job_id = st.session_state.get("active_preview_job_id")
        if st.button(
            "Extract text for review",
            disabled=not can_preview or bool(active_preview_job_id),
            key="extract_material_text",
        ):
            try:
                job_id = submit_document_preview(
                    uploaded.name,
                    file_bytes,
                    owner_eduai_id=owner,
                )
                st.session_state.active_preview_job_id = job_id
                st.session_state.material_preview_job_signature = signature
            except Exception as error:
                st.error(f"Could not start extraction: {error}")

        active_preview_job_id = st.session_state.get("active_preview_job_id")
        if active_preview_job_id:
            _render_job_progress(
                active_preview_job_id,
                owner,
                job_kind="preview",
                current_signature=signature,
            )

        extraction_message = st.session_state.pop("material_extraction_result_message", None)
        if extraction_message:
            st.success(extraction_message)
        statuses = st.session_state.pop("material_extraction_statuses", set())
        if "not_ready" in statuses:
            st.warning("Diagram descriptions were skipped because the local Ollama vision model is not ready. OCR labels are still included.")
        if "error" in statuses:
            st.warning("Some diagrams could not be analyzed. Their OCR text is still included; you can continue or try extraction again.")
        if "page_limit" in statuses:
            st.info(f"Only the configured maximum of {MAX_VISION_PAGES} diagram page(s) was analyzed.")

        pages = st.session_state.get("material_review_pages")
        if pages and st.session_state.get("material_review_signature") == signature:
            page_indices = list(range(len(pages)))
            selected_page = st.selectbox(
                "Page or text section to review", page_indices,
                format_func=lambda index: f"Page/section {index + 1} of {len(page_indices)}",
                key=f"review_page_{signature}",
            )
            text_key = f"material_review_text_{signature}_{selected_page}"
            st.session_state.setdefault(text_key, pages[selected_page]["text"])
            st.text_area(
                "Extracted text (editable)", key=text_key, height=220,
                help="Changes here are sent to chunking and embedding when you start indexing.",
            )
            if st.button("Index reviewed material", type="primary", key="index_reviewed_material"):
                edited_pages = []
                for index, page in enumerate(pages):
                    edited_pages.append({
                        "text": st.session_state.get(f"material_review_text_{signature}_{index}", page["text"]),
                        "metadata": page.get("metadata", {}),
                    })
                try:
                    job_id = submit_document_ingestion(
                        uploaded.name,
                        file_bytes,
                        owner_eduai_id=owner,
                        role=role,
                        course=course,
                        semester=semester,
                        subject=subject,
                        document_type=document_type,
                        title=title,
                        prepared_pages=edited_pages,
                    )
                    st.session_state.active_ingestion_job_id = job_id
                    st.success("Indexing started in the background. You can continue using the app.")
                except Exception as error:
                    st.error(f"Could not start indexing: {error}")

    active_job_id = st.session_state.get("active_ingestion_job_id")
    if active_job_id:
        _render_ingestion_progress(active_job_id, owner)

    st.markdown("#### Indexed material library")
    try:
        records = list_documents(owner, role)
    except Exception as error:
        st.error(f"Could not load the material library: {error}")
        return
    if not records:
        st.info("No documents have been indexed for this account or its courses yet.")
        return

    st.dataframe([
        {
            "Title": record["title"],
            "Type": record["document_type"],
            "Course": record["course"],
            "Semester": record["semester"],
            "Subject": record["subject"],
            "Access": "Shared" if record["visibility"] == "shared" else "Private",
            "Chunks": record["chunk_count"],
            "Added": record["created_at"],
        }
        for record in records
    ], hide_index=True, use_container_width=True)

    removable = [record for record in records if role == "Admin" or record["owner_eduai_id"] == str(owner)]
    if removable:
        with st.expander("Remove a document"):
            selected_id = st.selectbox(
                "Document",
                [record["document_id"] for record in removable],
                format_func=lambda document_id: next(
                    f"{record['title']} · {record['subject']}"
                    for record in removable if record["document_id"] == document_id
                ),
                key="remove_material_id",
            )
            confirmed = st.checkbox("I understand this removes the file and its searchable vectors.")
            if st.button("Remove material", disabled=not confirmed, type="secondary"):
                try:
                    delete_document(selected_id, owner, role)
                except Exception as error:
                    st.error(f"Could not remove this material: {error}")
                else:
                    st.success("Material and its vectors were removed.")
                    st.rerun()
