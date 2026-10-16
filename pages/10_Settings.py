import streamlit as st

from ui import inject_css, page_header, sidebar


st.set_page_config(page_title="EduAI | Settings", page_icon="🎓", layout="wide")
inject_css()
if not st.session_state.get("authenticated"):
    st.switch_page("pages/1_Login.py")
    st.stop()
sidebar()
page_header("Account", "Review the account currently signed in to EduAI.")

with st.container(border=True):
    st.markdown("#### Account details")
    st.write(f"**Name:** {st.session_state.get('user_name', '—')}")
    st.write(f"**Email:** {st.session_state.get('user_email', '—')}")
    st.write(f"**Role:** {st.session_state.get('role', 'Student')}")
    st.write(f"**EduAI ID:** {st.session_state.get('user_id', '—')}")
