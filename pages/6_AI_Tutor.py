import uuid

import streamlit as st

from ai_pipeline import (
    TUTOR_LONG_EFFECTIVE_MAX_NEW_TOKENS,
    TUTOR_LONG_MAX_NEW_TOKENS,
    stream_answer,
)
from database import ensure_schema
from education_data import catalog_values, get_chat_messages, save_chat_feedback, save_chat_message
from ui import inject_css, page_header, sidebar


st.set_page_config(page_title="EduAI | AI Tutor", page_icon="🎓", layout="wide")
inject_css()
if not st.session_state.get("authenticated"):
    st.switch_page("pages/1_Login.py")
    st.stop()
sidebar()
page_header("AI tutor", "Continue a conversation, choose how detailed answers should be, and decide whether to use uploaded material only.")

try:
    ensure_schema()
except Exception as error:
    st.error(f"The tutor needs a working MySQL connection: {error}")
    st.stop()

try:
    courses = catalog_values("Course")
    course_options = ["All courses"] + courses
    selected_course = st.selectbox("Course", course_options, key="tutor_course")
    course = "" if selected_course == "All courses" else selected_course
    semesters = catalog_values("Semester", course=course) if course else []
    semester_options = ["All semesters"] + semesters
    selected_semester = st.selectbox(
        "Semester", semester_options, key=f"tutor_semester_{selected_course}",
        disabled=not semesters,
    )
    semester = "" if selected_semester == "All semesters" else selected_semester
    subjects = catalog_values("Subject", course=course, semester=semester) if course and semester else []
    subject_options = ["All subjects"] + subjects
    selected_subject = st.selectbox(
        "Subject", subject_options, key=f"tutor_subject_{selected_course}_{selected_semester}",
        disabled=not subjects,
    )
    subject = "" if selected_subject == "All subjects" else selected_subject
    context = {"course": course, "semester": semester, "subject": subject}
except Exception as error:
    st.error(f"Could not load the course filters: {error}")
    st.stop()

answer_columns = st.columns(2)
answer_style_label = answer_columns[0].selectbox(
    "Answer length",
    [
        "Detailed (about 300–450 words)",
        "Concise",
        "Long-form (about 1,150–2,000 words)",
    ],
    key="tutor_answer_style",
)
if answer_style_label.startswith("Long-form"):
    answer_style = "long_form"
elif answer_style_label.startswith("Detailed"):
    answer_style = "detailed"
else:
    answer_style = "concise"
knowledge_mode_label = answer_columns[1].selectbox(
    "Knowledge source",
    ["Course materials only", "General tutor (may use model knowledge)"],
    index=1,
    key="tutor_knowledge_mode",
)
knowledge_mode = "course_material" if knowledge_mode_label == "Course materials only" else "general"
if knowledge_mode == "general":
    st.caption(
        "General tutor mode uses matching course material when available and can fill gaps from "
        "the local model's knowledge. It does not browse the internet."
    )
else:
    st.caption("Course materials only mode will say when your indexed material does not cover a question.")
if answer_style == "long_form":
    if TUTOR_LONG_EFFECTIVE_MAX_NEW_TOKENS < TUTOR_LONG_MAX_NEW_TOKENS:
        st.caption(
            f"Long-form is active for new answers until you change the selection (up to "
            f"{TUTOR_LONG_EFFECTIVE_MAX_NEW_TOKENS:,} output tokens with the current context setting). "
            "Increase EDUAI_CONTEXT_WINDOW to 8192 for the full configured allowance."
        )
    else:
        st.caption(
            f"Long-form is active for new answers until you change the selection (up to "
            f"{TUTOR_LONG_EFFECTIVE_MAX_NEW_TOKENS:,} output tokens). It can take several minutes "
            "on this local CPU; actual length depends on the question and available course material."
        )

if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = str(uuid.uuid4())
if st.session_state.get("loaded_chat_id") != st.session_state.active_chat_id:
    st.session_state.chat_messages = get_chat_messages(
        st.session_state.active_chat_id, st.session_state.user_id,
    )
    st.session_state.loaded_chat_id = st.session_state.active_chat_id

if st.button("＋ New conversation"):
    st.session_state.active_chat_id = str(uuid.uuid4())
    st.session_state.loaded_chat_id = None
    st.rerun()

if not st.session_state.chat_messages:
    with st.container(border=True):
        st.markdown("#### Your materials power this tutor")
        st.write("Upload a PDF, DOCX, or TXT file in Documents. EduAI extracts and indexes its text before answering.")

for message in st.session_state.chat_messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        for citation in message.get("citations", []):
            page = f", page {citation['page']}" if citation.get("page") else ""
            st.caption(f"Source: {citation.get('title', 'Study material')}{page}")
        if message["role"] == "assistant" and message.get("message_id"):
            feedback_columns = st.columns([1, 1, 8])
            if feedback_columns[0].button("👍", key=f"helpful_{message['message_id']}", help="This answer was helpful"):
                save_chat_feedback(message["message_id"], st.session_state.user_id, "helpful")
                message["feedback"] = "helpful"
                st.rerun()
            if feedback_columns[1].button("👎", key=f"not_helpful_{message['message_id']}", help="This answer was not helpful"):
                save_chat_feedback(message["message_id"], st.session_state.user_id, "not_helpful")
                message["feedback"] = "not_helpful"
                st.rerun()
            if message.get("feedback"):
                feedback_columns[2].caption("Thanks, your feedback is saved.")

prompt = st.chat_input("Ask a study question or follow-up...")
if prompt:
    owner = st.session_state.user_id
    role = st.session_state.get("role", "Student")
    st.session_state.chat_messages.append({"role": "user", "content": prompt, "citations": []})
    save_chat_message(
        st.session_state.active_chat_id, owner, "user", prompt, context=context,
    )
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        try:
            chunks, citations, _performance_metrics = stream_answer(
                prompt, owner, role, context=context,
                history=st.session_state.chat_messages[:-1],
                answer_style=answer_style, knowledge_mode=knowledge_mode,
            )
            answer = st.write_stream(chunks)
            metric_parts = []
            if isinstance(_performance_metrics.get("response_words"), int):
                metric_parts.append(f"About {_performance_metrics['response_words']:,} words")
            if isinstance(_performance_metrics.get("retrieval_ms"), (int, float)):
                metric_parts.append(f"Fetching {_performance_metrics['retrieval_ms'] / 1000:.2f}s")
            if isinstance(_performance_metrics.get("first_output_ms"), (int, float)):
                metric_parts.append(
                    f"First output {_performance_metrics['first_output_ms'] / 1000:.1f}s"
                )
            if isinstance(_performance_metrics.get("generation_ms"), (int, float)):
                metric_parts.append(
                    f"Generation {_performance_metrics['generation_ms'] / 1000:.1f}s"
                )
            if isinstance(_performance_metrics.get("total_ms"), (int, float)):
                metric_parts.append(f"Total {_performance_metrics['total_ms'] / 1000:.1f}s")
            if metric_parts:
                st.caption(" · ".join(metric_parts))
            for citation in citations:
                page = f", page {citation['page']}" if citation.get("page") else ""
                st.caption(f"Source: {citation.get('title', 'Study material')}{page}")
            message_id = save_chat_message(
                st.session_state.active_chat_id, owner, "assistant", answer,
                citations=citations, context=context,
            )
            st.session_state.chat_messages.append({
                "message_id": message_id, "role": "assistant", "content": answer,
                "citations": citations, "feedback": None,
            })
            if message_id:
                feedback_columns = st.columns([1, 1, 8])
                if feedback_columns[0].button("👍", key=f"helpful_{message_id}", help="This answer was helpful"):
                    save_chat_feedback(message_id, owner, "helpful")
                    st.session_state.chat_messages[-1]["feedback"] = "helpful"
                    st.rerun()
                if feedback_columns[1].button("👎", key=f"not_helpful_{message_id}", help="This answer was not helpful"):
                    save_chat_feedback(message_id, owner, "not_helpful")
                    st.session_state.chat_messages[-1]["feedback"] = "not_helpful"
                    st.rerun()
        except Exception as error:
            st.error(f"The local tutor could not answer: {error}")
