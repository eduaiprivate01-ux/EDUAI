import streamlit as st

from ai_pipeline import generate_practice_set
from database import ensure_schema
from education_data import (
    adaptive_review_subjects,
    catalog_values,
    save_practice_attempt,
    save_practice_session,
)
from ui import inject_css, page_header, sidebar


st.set_page_config(page_title="EduAI | Practice", page_icon="🎓", layout="wide")
inject_css()
if not st.session_state.get("authenticated"):
    st.switch_page("pages/1_Login.py")
    st.stop()
sidebar()
page_header("Practice", "Generate questions from indexed course materials and schedule spaced review.")

try:
    ensure_schema()
    review_subjects = adaptive_review_subjects(st.session_state.user_id)
except Exception as error:
    st.error(f"Practice generation needs a working MySQL connection: {error}")
    st.stop()

due = [row for row in review_subjects if row["due"]]
if due:
    st.info("Review due: " + ", ".join(
        f"{row['subject']} ({row['course']} · {row['semester']})" for row in due[:5]
    ))

try:
    courses = catalog_values("Course")
    if not courses:
        st.info("An admin needs to add the course structure before practice sets can be created.")
        st.stop()
    course = st.selectbox("Course", courses, key="practice_course")
    semesters = catalog_values("Semester", course=course)
    if not semesters:
        st.info(f"No semesters are defined for {course} yet.")
        st.stop()
    semester = st.selectbox("Semester", semesters, key=f"practice_semester_{course}")
    subjects = catalog_values("Subject", course=course, semester=semester)
    if not subjects:
        st.info(f"No subjects are defined for {course} · {semester} yet.")
        st.stop()
    subject = st.selectbox("Subject", subjects, key=f"practice_subject_{course}_{semester}")
except Exception as error:
    st.error(f"Could not load the course structure: {error}")
    st.stop()

matching_reviews = [
    row for row in review_subjects
    if row["course"] == course and row["semester"] == semester and row["subject"] == subject
]
review_focus = ""
if matching_reviews:
    latest = matching_reviews[0]
    st.caption(
        f"Last score: {float(latest['accuracy']):.0%}. Next review: "
        f"{latest['next_review_at']:%d %b %Y %H:%M}."
    )
    if float(latest["accuracy"]) < 0.5:
        review_focus = "Focus on foundational concepts and common misconceptions because this subject needs review. "
    elif latest["due"]:
        review_focus = "This subject is due for spaced review. Reinforce previously covered core concepts. "

context = {"course": course, "semester": semester, "subject": subject}
with st.form("practice_setup"):
    type_column, count_column = st.columns(2)
    with type_column:
        question_type = st.selectbox("Question type", ["MCQ", "3-Mark", "5-Mark", "10-Mark"])
    with count_column:
        question_count = st.slider("Number of questions", 1, 10, 5)
    submitted = st.form_submit_button(
        "Generate from indexed material", type="primary", use_container_width=True,
    )

if submitted:
    st.session_state.pop("last_practice", None)
    try:
        with st.spinner("Retrieving course material and writing the practice set..."):
            content, citations = generate_practice_set(
                f"{review_focus}Create practice questions for {subject}",
                st.session_state.user_id,
                st.session_state.get("role", "Student"),
                context,
                question_type,
                question_count,
            )
        practice_id = save_practice_session(
            st.session_state.user_id, context, question_type, question_count, content, citations,
        )
        st.session_state.last_practice = {
            "practice_id": practice_id,
            "content": content,
            "citations": citations,
            "context": context,
            "question_count": question_count,
        }
    except Exception as error:
        st.error(f"Could not generate the practice set: {error}")

result = st.session_state.get("last_practice")
if result:
    st.markdown("#### Generated practice set")
    st.markdown(result["content"])
    for citation in result.get("citations", []):
        page = f", page {citation['page']}" if citation.get("page") else ""
        st.caption(f"Source: {citation.get('title', 'Study material')}{page}")

    if not result.get("scored"):
        st.caption("After attempting the questions, check the answer key above and record your score to schedule review.")
        with st.form(f"score_practice_{result['practice_id']}"):
            correct_count = st.number_input(
                "How many did you answer correctly?",
                min_value=0,
                max_value=int(result["question_count"]),
                value=0,
                step=1,
            )
            scored = st.form_submit_button("Save score and schedule review")
        if scored:
            try:
                schedule = save_practice_attempt(
                    st.session_state.user_id,
                    result["practice_id"],
                    result["context"],
                    correct_count,
                    result["question_count"],
                )
                result["scored"] = True
                st.session_state.last_practice = result
                st.success(
                    f"Score saved ({schedule['accuracy']:.0%}). Review this subject again in "
                    f"{schedule['interval_days']} day(s)."
                )
            except Exception as error:
                st.error(f"Could not save your score: {error}")
    else:
        st.success("Your score is saved. The next review interval adapts to your result.")
