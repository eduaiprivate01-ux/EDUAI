import streamlit as st

from auth import create_user_account, delete_user_account, list_user_accounts
from ai_pipeline import model_status
from database import ensure_schema, is_configured
from education_data import (
    add_catalog_path,
    catalog_records,
    get_admin_metrics,
    get_feedback_metrics,
    list_admin_events,
    record_admin_event,
)
from material_ui import render_material_manager
from ui import inject_css, page_header, sidebar


st.set_page_config(page_title="EduAI | Admin Dashboard", page_icon="🎓", layout="wide")
inject_css()
if not st.session_state.get("authenticated"):
    st.switch_page("pages/1_Login.py")
    st.stop()
if st.session_state.get("role") != "Admin":
    st.switch_page("app.py")
    st.stop()
st.session_state.setdefault("admin_section", "overview")
sidebar()

if not is_configured():
    st.error("Configure the EduAI MySQL connection before using administration.")
    st.stop()
try:
    ensure_schema()
except Exception as error:
    st.error(f"Could not connect to MySQL: {error}")
    st.stop()


def record_change(action, target):
    record_admin_event(st.session_state.user_id, action, target)


def render_overview():
    page_header("Admin dashboard", "Manage the curriculum, materials, and EduAI accounts.")
    metrics = get_admin_metrics()
    columns = st.columns(4)
    columns[0].metric("Active accounts", metrics["active_users"])
    columns[1].metric("Courses", metrics["courses"])
    columns[2].metric("Indexed materials", metrics["materials"])
    columns[3].metric("Tutor questions", metrics["questions"])
    with st.container(border=True):
        st.markdown("#### Set up the AI knowledge base")
        st.write("Add courses, semesters, and subjects, then upload shared syllabi or study materials. The tutor searches their indexed text.")


def render_academic():
    page_header("Academic structure", "Create the course hierarchy used to organize study materials.")
    with st.form("academic_path_form", clear_on_submit=True):
        columns = st.columns(3)
        with columns[0]:
            course = st.text_input("Course")
        with columns[1]:
            semester = st.text_input("Semester")
        with columns[2]:
            subject = st.text_input("Subject")
        submitted = st.form_submit_button("Save curriculum path", type="primary", use_container_width=True)
    if submitted:
        try:
            added = add_catalog_path(course, semester, subject, st.session_state.user_id)
        except ValueError as error:
            st.error(str(error))
        except Exception as error:
            st.error(f"Could not save the curriculum path: {error}")
        else:
            record_change("Added curriculum path", f"{course} · {semester} · {subject}")
            st.success("Curriculum path saved." if added else "That curriculum path already exists.")

    records = catalog_records()
    st.markdown("#### Current curriculum")
    if records:
        st.dataframe([
            {
                "Type": row["item_type"], "Name": row["name"], "Course": row["course"],
                "Semester": row["semester"], "Subject": row["subject"],
            }
            for row in records
        ], hide_index=True, use_container_width=True)
    else:
        st.info("No curriculum paths have been saved yet.")


def render_materials():
    page_header("Syllabus & materials", "Upload shared files and index them for semantic search.")
    render_material_manager()


def render_users():
    page_header("User management", "Create and review persistent EduAI accounts.")
    with st.container(border=True):
        st.markdown("#### Add a teacher")
        with st.form("teacher_create_form"):
            name = st.text_input("Teacher full name")
            email = st.text_input("Teacher email", placeholder="teacher@example.com")
            password = st.text_input("Set initial password", type="password", help="Use at least 8 characters.")
            confirm_password = st.text_input("Confirm initial password", type="password")
            add_teacher = st.form_submit_button("Create teacher account", type="primary")

    if add_teacher:
        name, email = name.strip(), email.strip().lower()
        if not name or "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            st.error("Enter the teacher's name and a valid email address.")
        elif len(password) < 8:
            st.error("The password must contain at least 8 characters.")
        elif password != confirm_password:
            st.error("The passwords do not match.")
        else:
            try:
                eduai_id = create_user_account(email, name, password, role="teacher")
            except ValueError as error:
                st.error(str(error))
            except Exception as error:
                st.error(f"Could not create the teacher account: {error}")
            else:
                record_change("Created teacher account", email)
                st.success(f"Teacher account created. EduAI login ID: **{eduai_id}**.")

    st.markdown("#### Registered accounts")
    try:
        users = list_user_accounts()
    except Exception as error:
        st.error(f"Could not load accounts from MySQL: {error}")
        return
    if users:
        st.dataframe([{
            "EduAI ID": user["eduai_id"], "Name": user["display_name"],
            "Email": user["email"], "Role": user["role"].capitalize(),
            "Status": user["status"].capitalize(), "Created": user["created_at"],
        } for user in users], hide_index=True, use_container_width=True)
        deletable = [user for user in users if user["role"] in {"student", "teacher"}]
        if deletable:
            st.markdown("#### Delete a student or teacher account")
            selected_id = st.selectbox(
                "Account to delete",
                [user["eduai_id"] for user in deletable],
                format_func=lambda value: next(
                    f"{user['display_name']} · {user['role'].capitalize()} · {value}"
                    for user in deletable if user["eduai_id"] == value
                ),
            )
            confirmed = st.checkbox("I understand this permanently deletes the selected account.")
            if st.button("Delete selected account", disabled=not confirmed):
                try:
                    deleted = delete_user_account(selected_id)
                except Exception as error:
                    st.error(f"Could not delete the account: {error}")
                else:
                    if deleted:
                        record_change("Deleted user account", selected_id)
                        st.success(f"Deleted account {selected_id}.")
                        st.rerun()
    else:
        st.info("No accounts have been registered yet.")


def render_ai_quality():
    page_header("AI activity", "Live counts from saved tutor and document records.")
    metrics = get_admin_metrics()
    columns = st.columns(3)
    columns[0].metric("Tutor questions", metrics["questions"])
    columns[1].metric("Indexed materials", metrics["materials"])
    columns[2].metric("Active accounts", metrics["active_users"])
    models = model_status()
    feedback = get_feedback_metrics()
    st.markdown("#### Local models")
    model_columns = st.columns(5)
    model_columns[0].metric("MiniLM embeddings", "Ready" if models["embedding_ready"] else "Missing")
    model_columns[1].metric("Qwen 7B chat model", "Ready" if models["qwen_ready"] else "Missing")
    model_columns[2].metric("Handwriting OCR", "Ready" if models["ocr_ready"] else "Missing")
    reranker_status = (
        "Disabled" if not models["reranker_enabled"] else
        "Ready" if models["reranker_ready"] else "Not downloaded"
    )
    vision_status = (
        "Disabled" if not models["vision_enabled"] else
        "Ready" if models["vision_ready"] else "Setup needed"
    )
    model_columns[3].metric("Diagram vision", vision_status)
    model_columns[4].metric("Cross-Encoder reranker", reranker_status)
    st.caption(
        f"Qwen GPU layers configured: {models['gpu_layers']} (0 means CPU). "
        "To set up local diagram understanding, install Ollama and run .\\download_diagram_model.ps1 once. "
        "The configured diagram model is " + models["vision_model"] + ". "
        "To download the optional reranker once, run .\\download_reranker.ps1."
    )
    st.markdown("#### Answer feedback")
    feedback_columns = st.columns(3)
    feedback_columns[0].metric("Ratings", feedback["total"])
    feedback_columns[1].metric("Helpful", feedback["helpful"])
    feedback_columns[2].metric("Not helpful", feedback["not_helpful"])
    st.markdown("#### Retrieval evaluation")
    st.caption(
        "Label relevant document IDs in evaluation/rag_questions.jsonl, then run "
        "`..\\model\\.venv\\Scripts\\python.exe .\\evaluate_rag.py .\\evaluation\\rag_questions.jsonl`. "
        "The report includes Recall@k, Precision@k, and MRR."
    )


def render_history():
    page_header("Change history", "Review curriculum and account changes saved in MySQL.")
    events = list_admin_events()
    if events:
        st.dataframe([
            {
                "Time": event["created_at"], "Admin ID": event["admin_eduai_id"],
                "Action": event["action"], "Target": event["target"],
            }
            for event in events
        ], hide_index=True, use_container_width=True)
    else:
        st.info("No admin changes have been recorded yet.")


sections = {
    "overview": render_overview,
    "academic": render_academic,
    "materials": render_materials,
    "users": render_users,
    "ai": render_ai_quality,
    "history": render_history,
}
sections.get(st.session_state.admin_section, render_overview)()
