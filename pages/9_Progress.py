import streamlit as st

from database import ensure_schema
from education_data import (
    adaptive_review_subjects,
    list_chat_sessions,
    list_practice_attempts,
    list_practice_sessions,
)
from ui import inject_css, page_header, sidebar


st.set_page_config(page_title="EduAI | Progress", page_icon="🎓", layout="wide")
inject_css()
if not st.session_state.get("authenticated"):
    st.switch_page("pages/1_Login.py")
    st.stop()
sidebar()
page_header("Study activity", "Track self-scored practice and see which subjects are due for review.")

try:
    ensure_schema()
    practices = list_practice_sessions(st.session_state.user_id)
    chats = list_chat_sessions(st.session_state.user_id)
    attempts = list_practice_attempts(st.session_state.user_id)
    review_subjects = adaptive_review_subjects(st.session_state.user_id)
except Exception as error:
    st.error(f"Could not load study activity from MySQL: {error}")
    st.stop()

average_accuracy = (
    sum(float(row["accuracy"]) for row in attempts) / len(attempts) if attempts else 0.0
)
columns = st.columns(4)
columns[0].metric("Recent practice sets", len(practices))
columns[1].metric("Saved conversations", len(chats))
columns[2].metric("Scored attempts", len(attempts))
columns[3].metric("Average score", f"{average_accuracy:.0%}" if attempts else "—")

due = [row for row in review_subjects if row["due"]]
if due:
    st.markdown("#### Due for review")
    st.dataframe([
        {
            "Course": row["course"], "Semester": row["semester"], "Subject": row["subject"],
            "Last score": f"{float(row['accuracy']):.0%}", "Due since": row["next_review_at"],
        }
        for row in due
    ], hide_index=True, use_container_width=True)
elif review_subjects:
    st.success("No subjects are due for review right now.")
else:
    st.caption("Record a practice score to start your spaced-review schedule.")

if attempts:
    st.markdown("#### Recent scored attempts")
    st.dataframe([
        {
            "Course": row["course"], "Semester": row["semester"], "Subject": row["subject"],
            "Score": f"{row['correct_count']}/{row['total_questions']} ({float(row['accuracy']):.0%})",
            "Review interval": f"{row['interval_days']} day(s)",
            "Next review": row["next_review_at"], "Attempted": row["created_at"],
        }
        for row in attempts
    ], hide_index=True, use_container_width=True)

if practices:
    st.markdown("#### Recent practice sets")
    st.dataframe([
        {
            "Subject": row["subject"], "Type": row["question_type"],
            "Questions": row["question_count"], "Created": row["created_at"],
        }
        for row in practices
    ], hide_index=True, use_container_width=True)
else:
    st.info("No practice sets have been generated yet.")
