import streamlit as st

from database import ensure_schema
from education_data import catalog_values, list_documents
from ui import inject_css, page_header, sidebar


st.set_page_config(page_title="EduAI | My Courses", page_icon="🎓", layout="wide")
inject_css()
if not st.session_state.get("authenticated"):
    st.switch_page("pages/1_Login.py")
    st.stop()
sidebar()
page_header("Courses", "Browse courses and semesters saved in the EduAI curriculum.")

try:
    ensure_schema()
    courses = catalog_values("Course")
except Exception as error:
    st.error(f"Could not load the curriculum from MySQL: {error}")
    st.stop()

if not courses:
    st.info("No courses are available yet. An admin can add a course in Academic structure.")
else:
    course = st.selectbox("Course", courses)
    semesters = catalog_values("Semester", course=course)
    if semesters:
        semester = st.selectbox("Semester", semesters)
        subjects = catalog_values("Subject", course=course, semester=semester)
        materials = list_documents(
            st.session_state.user_id, st.session_state.get("role", "Student"),
            course=course, semester=semester,
        )
        columns = st.columns(3)
        columns[0].metric("Subjects", len(subjects))
        columns[1].metric("Indexed materials", len(materials))
        columns[2].metric("Course", course)
        if subjects:
            st.markdown("#### Subjects")
            st.write(" · ".join(subjects))
        else:
            st.info("No subjects have been added for this semester yet.")
    else:
        st.info("No semesters have been added for this course yet.")
