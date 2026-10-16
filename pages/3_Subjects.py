import streamlit as st

from database import ensure_schema
from education_data import catalog_values, list_documents
from ui import inject_css, page_header, sidebar


st.set_page_config(page_title="EduAI | Subjects", page_icon="🎓", layout="wide")
inject_css()
if not st.session_state.get("authenticated"):
    st.switch_page("pages/1_Login.py")
    st.stop()
sidebar()
page_header("Subjects", "Explore the subjects saved in your selected curriculum.")

try:
    ensure_schema()
    courses = catalog_values("Course")
except Exception as error:
    st.error(f"Could not load the curriculum from MySQL: {error}")
    st.stop()

if not courses:
    st.info("No subjects are available yet. An admin can add the curriculum in Academic structure.")
else:
    course = st.selectbox("Course", courses)
    semesters = catalog_values("Semester", course=course)
    if semesters:
        semester = st.selectbox("Semester", semesters)
        subjects = catalog_values("Subject", course=course, semester=semester)
        for subject in subjects:
            materials = list_documents(
                st.session_state.user_id, st.session_state.get("role", "Student"),
                course=course, semester=semester, subject=subject,
            )
            with st.container(border=True):
                st.caption(f"{course} · {semester}")
                st.markdown(f"#### {subject}")
                st.write(f"{len(materials)} indexed material(s)")
        if not subjects:
            st.info("No subjects have been saved for this semester yet.")
    else:
        st.info("No semesters have been added for this course yet.")
