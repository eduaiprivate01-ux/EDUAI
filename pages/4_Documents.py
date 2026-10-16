import streamlit as st

from material_ui import render_material_manager
from ui import inject_css, page_header, sidebar


st.set_page_config(page_title="EduAI | Documents", page_icon="🎓", layout="wide")
inject_css()
sidebar()
page_header("Documents", "Upload study resources and make them searchable by the AI tutor.")
render_material_manager()
