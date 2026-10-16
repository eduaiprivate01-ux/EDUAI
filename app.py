import streamlit as st

from database import ensure_schema
from education_data import catalog_records, list_chat_sessions, list_documents, list_practice_sessions
from ui import inject_css, page_header, sidebar


st.set_page_config(
    page_title="EduAI | Dashboard", page_icon="🎓", layout="wide", initial_sidebar_state="expanded",
)
inject_css()
if not st.session_state.get("authenticated"):
    st.switch_page("pages/1_Login.py")
    st.stop()
if st.session_state.get("role") == "Admin":
    st.switch_page("pages/11_Admin_Dashboard.py")
    st.stop()
if st.session_state.get("role") == "Teacher":
    st.switch_page("pages/12_Teacher_Dashboard.py")
    st.stop()
sidebar()
page_header(f"Welcome, {st.session_state.get('user_name', 'Student')}", "Your EduAI workspace and indexed learning materials.")

try:
    ensure_schema()
    records = catalog_records()
    materials = list_documents(st.session_state.user_id, st.session_state.get("role", "Student"))
    chats = list_chat_sessions(st.session_state.user_id)
    practices = list_practice_sessions(st.session_state.user_id)
except Exception as error:
    st.error(f"Could not load your EduAI dashboard from MySQL: {error}")
    st.stop()

subjects = [row for row in records if row["item_type"] == "Subject"]
courses = sorted({row["name"] for row in records if row["item_type"] == "Course"})
st.markdown("<div class='section-title'>Your learning workspace</div>", unsafe_allow_html=True)
metrics = st.columns(4)
metrics[0].metric("Courses in catalog", len(courses))
metrics[1].metric("Subjects", len(subjects))
metrics[2].metric("Available materials", len(materials))
metrics[3].metric("Saved conversations", len(chats))

st.markdown("<div class='section-title'>Course subjects</div>", unsafe_allow_html=True)
if subjects:
    for start in range(0, len(subjects), 2):
        columns = st.columns(2)
        for column, row in zip(columns, subjects[start:start + 2]):
            with column:
                with st.container(border=True):
                    st.caption(f"{row['course']} · {row['semester']}")
                    st.markdown(f"#### {row['name']}")
else:
    st.info("No subjects have been added yet. An admin can set up the curriculum before you begin.")

st.markdown("<div class='section-title'>Recent practice</div>", unsafe_allow_html=True)
if practices:
    latest = practices[0]
    st.write(
        f"Latest set: {latest['question_count']} {latest['question_type']} question(s) · "
        f"{latest['subject']} · {latest['created_at']}"
    )
else:
    st.info("No practice sets have been generated yet. Add indexed material, then use Practice.")
