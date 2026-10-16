import streamlit as st

from auth import authenticate_user, create_user_account
from database import ensure_schema, has_mysql_settings, is_configured
from ui import inject_css


st.set_page_config(page_title="EduAI | Login", page_icon="🎓", layout="centered")
inject_css()
st.session_state.setdefault("authenticated", False)

database_ready = False
if not has_mysql_settings() or not is_configured():
    st.error("MySQL is required for EduAI accounts. Configure host, port, user, password, and database first.")
else:
    try:
        ensure_schema()
        database_ready = True
    except Exception as error:
        st.error(f"Could not connect to the configured EduAI database: {error}")

center = st.columns([1, 1.35, 1])[1]
with center:
    with st.container(border=True):
        st.markdown('<div class="login-brand">Edu<span>AI</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="login-title">Welcome back</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Sign in or create your learning account.</div>', unsafe_allow_html=True)
        login_tab, register_tab = st.tabs(["Sign in", "Create account"])

        with login_tab:
            with st.form("login_form"):
                email = st.text_input("Email or EduAI ID", placeholder="EDU-1234ABCD or you@example.com")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button(
                    "Sign in", use_container_width=True, type="primary", disabled=not database_ready,
                )

        with register_tab:
            with st.form("registration_form"):
                new_name = st.text_input("Full name")
                new_email = st.text_input("Email", placeholder="you@example.com")
                new_password = st.text_input("Create password", type="password", help="Use at least 8 characters.")
                confirm_password = st.text_input("Confirm password", type="password")
                register = st.form_submit_button(
                    "Create account", use_container_width=True, disabled=not database_ready,
                )
            st.caption("Student accounts can be created here. Admins create teacher accounts from User management.")

if register and database_ready:
    name = new_name.strip()
    normalized_email = new_email.strip().lower()
    if not name or "@" not in normalized_email or "." not in normalized_email.rsplit("@", 1)[-1]:
        st.error("Enter your name and a valid email address.")
    elif len(new_password) < 8:
        st.error("Your password must contain at least 8 characters.")
    elif new_password != confirm_password:
        st.error("The passwords do not match.")
    else:
        try:
            eduai_id = create_user_account(normalized_email, name, new_password, "student")
        except ValueError as error:
            st.error(str(error))
        except Exception as error:
            st.error(f"Could not create the account: {error}")
        else:
            st.success(f"Account created. Your EduAI ID is **{eduai_id}**. Sign in with your email and password.")

if submitted and database_ready:
    if not email or not password:
        st.error("Enter both your email and password to continue.")
    else:
        try:
            user = authenticate_user(email, password)
        except Exception as error:
            st.error(f"Sign-in failed because the database is unavailable: {error}")
        else:
            if user:
                st.session_state.authenticated = True
                st.session_state.user_id = user["id"]
                st.session_state.user_email = user["email"]
                st.session_state.user_name = user["name"]
                st.session_state.role = user["role"]
                destination = {
                    "Teacher": "pages/12_Teacher_Dashboard.py",
                    "Admin": "pages/11_Admin_Dashboard.py",
                }.get(user["role"], "app.py")
                st.switch_page(destination)
            else:
                st.error("Email or password is incorrect, or the account is inactive.")
