import streamlit as st

from database import ensure_schema
from education_data import catalog_records
from material_ui import render_material_manager
from ui import inject_css, page_header, sidebar


st.set_page_config(page_title="EduAI | Teacher Dashboard", page_icon="🎓", layout="wide")
inject_css()
if not st.session_state.get("authenticated"):
    st.switch_page("pages/1_Login.py")
    st.stop()
if st.session_state.get("role") != "Teacher":
    destination = "pages/11_Admin_Dashboard.py" if st.session_state.get("role") == "Admin" else "app.py"
    st.switch_page(destination)
    st.stop()
sidebar()
page_header(f"Welcome, {st.session_state.get('user_name', 'Teacher')}", "Share course material for the AI tutor.")

try:
    ensure_schema()
    records = catalog_records()
except Exception as error:
    st.error(f"Could not load EduAI data from MySQL: {error}")
    st.stop()

class_tab, materials_tab = st.tabs(["Curriculum", "Share materials"])
with class_tab:
    subjects = [record for record in records if record["item_type"] == "Subject"]
    if subjects:
        st.dataframe([
            {"Course": row["course"], "Semester": row["semester"], "Subject": row["name"]}
            for row in subjects
        ], hide_index=True, use_container_width=True)
    else:
        st.info("No course subjects have been added to the curriculum yet. An admin can add them in Academic structure.")

with materials_tab:
    render_material_manager()
