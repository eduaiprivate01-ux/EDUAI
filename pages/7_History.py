import streamlit as st

from database import ensure_schema
from education_data import get_chat_messages, list_chat_sessions
from ui import inject_css, page_header, sidebar


st.set_page_config(page_title="EduAI | Chat history", page_icon="🎓", layout="wide")
inject_css()
if not st.session_state.get("authenticated"):
    st.switch_page("pages/1_Login.py")
    st.stop()
sidebar()
page_header("Chat history", "Continue one of your saved study conversations.")

try:
    ensure_schema()
    sessions = list_chat_sessions(st.session_state.user_id)
except Exception as error:
    st.error(f"Could not load chat history from MySQL: {error}")
    st.stop()

if not sessions:
    st.info("No conversations have been saved yet. Start a conversation with the AI tutor.")
else:
    labels = {
        item["session_id"]: (
            (item.get("title") or "Study conversation")[:90],
            item["updated_at"],
            item["message_count"],
        )
        for item in sessions
    }
    selected = st.selectbox(
        "Conversation",
        [item["session_id"] for item in sessions],
        format_func=lambda session_id: (
            f"{labels[session_id][0]} · {labels[session_id][1]} · {labels[session_id][2]} messages"
        ),
    )
    messages = get_chat_messages(selected, st.session_state.user_id)
    for message in messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            for citation in message.get("citations", []):
                page = f", page {citation['page']}" if citation.get("page") else ""
                st.caption(f"Source: {citation.get('title', 'Study material')}{page}")
    if st.button("Continue in AI tutor", type="primary"):
        st.session_state.active_chat_id = selected
        st.session_state.loaded_chat_id = None
        st.switch_page("pages/6_AI_Tutor.py")
