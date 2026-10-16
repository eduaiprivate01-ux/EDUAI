import streamlit as st

from database import ensure_schema
from education_data import list_documents
from ui import inject_css, page_header, sidebar


st.set_page_config(page_title="EduAI | Syllabus", page_icon="🎓", layout="wide")
inject_css()
if not st.session_state.get("authenticated"):
    st.switch_page("pages/1_Login.py")
    st.stop()
sidebar()
page_header("Syllabus", "Browse syllabus files that have been indexed in EduAI.")

try:
    ensure_schema()
    syllabi = list_documents(
        st.session_state.user_id, st.session_state.get("role", "Student"),
        document_type="Syllabus",
    )
except Exception as error:
    st.error(f"Could not load syllabi from MySQL: {error}")
    st.stop()

if syllabi:
    courses = sorted({item["course"] for item in syllabi if item["course"]})
    selected_course = st.selectbox("Course", ["All courses"] + courses)
    selected = [item for item in syllabi if selected_course == "All courses" or item["course"] == selected_course]
    for item in selected:
        with st.container(border=True):
            st.markdown(f"#### {item['title']}")
            st.caption(" · ".join(value for value in [item["course"], item["semester"], item["subject"]] if value))
            st.write(f"{item['chunk_count']} searchable sections · Added {item['created_at']}")
else:
    st.info("No syllabus files have been indexed yet. Upload a syllabus from Documents.")
