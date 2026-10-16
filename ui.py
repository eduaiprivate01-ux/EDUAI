import html

import streamlit as st


def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Manrope:wght@500;600;700;800&display=swap');

    :root {
        --canvas: #f4f7fb;
        --surface: #ffffff;
        --ink: #111827;
        --muted: #526174;
        --line: #e2e8f0;
        --brand: #4f46e5;
        --brand-dark: #3730a3;
        --nav: #111827;
        --nav-hover: #202c40;
    }

    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'DM Sans', sans-serif;
    }

    .stApp, [data-testid="stAppViewContainer"] {
        background: var(--canvas);
        color: var(--ink);
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    [data-testid="stMain"] .block-container {
        max-width: 1440px;
        padding: 2.2rem 3.2rem 3rem;
    }

    [data-testid="stMain"] {
        color: var(--ink);
    }

    [data-testid="stMain"] [data-testid="stMarkdownContainer"] {
        color: var(--ink);
    }

    [data-testid="stMain"] [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMain"] [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMain"] [data-testid="stMarkdownContainer"] h3,
    [data-testid="stMain"] [data-testid="stMarkdownContainer"] h4 {
        color: #111827;
        font-family: 'Manrope', 'DM Sans', sans-serif;
        letter-spacing: -.025em;
    }

    [data-testid="stWidgetLabel"],
    [data-testid="stWidgetLabel"] * {
        color: #344054 !important;
        font-weight: 600 !important;
        opacity: 1 !important;
    }

    [data-testid="stMain"] [data-testid="stExpander"] summary,
    [data-testid="stMain"] [data-testid="stExpander"] summary * {
        color: var(--ink) !important;
        opacity: 1 !important;
    }

    .page-heading {
        margin: 0 0 1.7rem;
    }

    .page-eyebrow {
        margin-bottom: .4rem;
        color: #635bff;
        font-size: .72rem;
        font-weight: 800;
        letter-spacing: .14em;
        text-transform: uppercase;
    }

    .page-title {
        color: #111827;
        font-family: 'Manrope', 'DM Sans', sans-serif;
        font-size: clamp(1.8rem, 3vw, 2.35rem);
        font-weight: 800;
        letter-spacing: -.045em;
        line-height: 1.15;
    }

    .page-subtitle {
        max-width: 760px;
        margin-top: .55rem;
        color: var(--muted);
        font-size: 1rem;
        line-height: 1.55;
    }

    .section-title {
        margin: 1.7rem 0 .9rem;
        color: #182230;
        font-family: 'Manrope', 'DM Sans', sans-serif;
        font-size: 1.08rem;
        font-weight: 800;
        letter-spacing: -.02em;
    }

    .brand {
        display: flex;
        align-items: center;
        gap: 11px;
        margin: .25rem .25rem 1.8rem;
        color: #f8fafc;
        font-family: 'Manrope', sans-serif;
        font-size: 1.2rem;
        font-weight: 800;
        letter-spacing: -.03em;
    }

    .brand-mark {
        display: grid;
        width: 38px;
        height: 38px;
        place-items: center;
        border: 1px solid rgba(255,255,255,.18);
        border-radius: 12px;
        background: linear-gradient(145deg, #06b6d4 0%, #6366f1 55%, #8b5cf6 100%);
        color: #fff;
        font-size: 1rem;
        box-shadow: 0 7px 18px rgba(79,70,229,.28);
        transition: transform .18s ease, box-shadow .18s ease;
    }

    .brand-mark:hover {
        transform: translateY(-2px) rotate(-4deg);
        box-shadow: 0 10px 24px rgba(6,182,212,.34);
    }

    .brand-name span {
        color: #a5b4fc;
    }

    .brand-tagline {
        display: block;
        margin-top: -2px;
        color: #98a4b8;
        font-family: 'DM Sans', sans-serif;
        font-size: .68rem;
        font-weight: 500;
        letter-spacing: .015em;
    }

    [data-testid="stSidebar"] {
        background: var(--nav) !important;
        border-right: 1px solid #263247;
    }

    [data-testid="stSidebar"] > div:first-child {
        background: var(--nav);
        padding: 1.25rem .9rem 1rem;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #8f9bb0;
    }

    .nav-caption {
        margin: .3rem .65rem .5rem;
        color: #8390a5;
        font-size: .67rem;
        font-weight: 800;
        letter-spacing: .13em;
        text-transform: uppercase;
    }

    [data-testid="stSidebar"] a {
        margin: .12rem 0;
        border: 1px solid transparent;
        border-radius: 10px;
        color: #d5deeb !important;
        font-weight: 600;
        transition: background-color .16s ease, color .16s ease;
    }

    [data-testid="stSidebar"] a [data-testid^="stIcon"],
    [data-testid="stSidebar"] a svg,
    [data-testid="stSidebar"] a > div > span:first-child,
    [data-testid="stSidebar"] a > div > span:first-child * {
        color: #a5b4fc !important;
        fill: #a5b4fc !important;
        stroke: #a5b4fc !important;
        transition: color .16s ease, fill .16s ease, stroke .16s ease, transform .16s ease;
    }

    [data-testid="stSidebar"] a:hover {
        background: var(--nav-hover) !important;
        color: #ffffff !important;
    }

    [data-testid="stSidebar"] a:hover [data-testid^="stIcon"],
    [data-testid="stSidebar"] a:hover svg,
    [data-testid="stSidebar"] a:hover > div > span:first-child,
    [data-testid="stSidebar"] a:hover > div > span:first-child * {
        color: #67e8f9 !important;
        fill: #67e8f9 !important;
        stroke: #67e8f9 !important;
        transform: scale(1.08);
    }

    [data-testid="stSidebar"] a:focus-visible {
        outline: 2px solid #a5b4fc;
        outline-offset: 2px;
    }

    [data-testid="stSidebar"] a[aria-current="page"] {
        background: #282b55 !important;
        border-color: rgba(165,180,252,.2);
        color: #ffffff !important;
        box-shadow: inset 3px 0 0 #8b85ff;
    }

    [data-testid="stSidebar"] a[aria-current="page"] [data-testid^="stIcon"],
    [data-testid="stSidebar"] a[aria-current="page"] svg,
    [data-testid="stSidebar"] a[aria-current="page"] > div > span:first-child,
    [data-testid="stSidebar"] a[aria-current="page"] > div > span:first-child * {
        color: #ffffff !important;
        fill: #ffffff !important;
        stroke: #ffffff !important;
    }

    [data-testid="stSidebar"] div.stButton > button {
        min-height: 42px;
        border: 1px solid transparent;
        border-radius: 10px;
        background: transparent;
        color: #d5deeb !important;
        font-weight: 650;
        text-align: left;
        justify-content: flex-start;
    }

    [data-testid="stSidebar"] div.stButton > button:hover {
        border-color: #334155;
        background: var(--nav-hover) !important;
        color: #ffffff !important;
    }

    [data-testid="stSidebar"] div.stButton > button[kind="primary"] {
        border-color: rgba(165,180,252,.2);
        background: #282b55 !important;
        box-shadow: inset 3px 0 0 #8b85ff;
        color: #ffffff !important;
    }

    [data-testid="stSidebar"] div.stButton > button:focus-visible {
        outline: 2px solid #a5b4fc;
        outline-offset: 2px;
    }

    [data-testid="stSidebar"] hr {
        margin: 1.1rem 0;
        border-color: #2b374c;
    }

    [data-testid="stSidebar"] [data-testid="stWidgetLabel"],
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] * {
        color: #d5deeb !important;
    }

    [data-testid="stMain"] div.stButton > button,
    [data-testid="stMain"] div.stFormSubmitButton > button {
        min-height: 44px;
        border-radius: 10px;
        font-weight: 700;
        transition: transform .16s ease, box-shadow .16s ease, background .16s ease;
    }

    [data-testid="stMain"] div.stButton > button:hover,
    [data-testid="stMain"] div.stFormSubmitButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(16,24,40,.1);
    }

    [data-testid="stMain"] div.stButton > button[kind="primary"],
    [data-testid="stMain"] div.stFormSubmitButton > button[kind="primary"] {
        border-color: #4f46e5;
        background: #4f46e5;
        color: #ffffff;
    }

    [data-testid="stMain"] div.stButton > button:not([kind="primary"]),
    [data-testid="stMain"] div.stFormSubmitButton > button:not([kind="primary"]) {
        border-color: #d0d7e2;
        background: #ffffff;
        color: #1d2939;
    }

    [data-testid="stMain"] input,
    [data-testid="stMain"] textarea,
    [data-testid="stMain"] [data-baseweb="select"] > div {
        border-radius: 9px;
    }

    [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--line);
        border-radius: 16px;
        background: var(--surface);
        box-shadow: 0 4px 18px rgba(16,24,40,.035);
    }

    [data-testid="stMain"] [data-testid="stMetric"] {
        min-height: 106px;
        border: 1px solid var(--line);
        border-radius: 14px;
        background: #ffffff;
        padding: .9rem 1rem;
        box-shadow: 0 4px 16px rgba(16,24,40,.03);
    }

    [data-testid="stMain"] [data-testid="stMetricLabel"] {
        color: #526174;
        font-weight: 650;
    }

    [data-testid="stMain"] [data-testid="stMetricValue"] {
        color: #111827;
        font-family: 'Manrope', sans-serif;
        font-weight: 800;
    }

    [data-testid="stMain"] [data-testid="stDataFrame"],
    [data-testid="stMain"] [data-testid="stDataEditor"] {
        overflow: hidden;
        border: 1px solid var(--line);
        border-radius: 12px;
    }

    [data-testid="stMain"] [data-testid="stChatMessage"] {
        margin-bottom: .75rem;
        border: 1px solid var(--line);
        border-radius: 14px;
        background: #ffffff !important;
        padding: .9rem 1rem;
        box-shadow: 0 3px 12px rgba(16,24,40,.035);
    }

    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] * {
        color: #111827 !important;
    }

    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] a {
        color: #4338ca !important;
    }

    .hero-card {
        position: relative;
        display: flex;
        min-height: 190px;
        align-items: center;
        justify-content: space-between;
        overflow: hidden;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(255,255,255,.15);
        border-radius: 22px;
        background: linear-gradient(118deg, #252f70 0%, #4c46bd 56%, #7169ec 100%);
        padding: 2rem 2.2rem;
        color: #ffffff;
        box-shadow: 0 16px 36px rgba(63,65,158,.19);
    }

    .hero-card:after {
        position: absolute;
        top: -70px;
        right: -35px;
        width: 260px;
        height: 260px;
        border: 1px solid rgba(255,255,255,.14);
        border-radius: 50%;
        content: "";
        box-shadow: 0 0 0 28px rgba(255,255,255,.035), 0 0 0 58px rgba(255,255,255,.025);
    }

    .hero-card > div {
        z-index: 1;
    }

    .hero-card h2 {
        margin: .45rem 0;
        color: #ffffff !important;
        font-family: 'Manrope', sans-serif;
        font-size: clamp(1.45rem, 3vw, 2rem);
        font-weight: 800;
        letter-spacing: -.04em;
    }

    .hero-card p {
        max-width: 650px;
        margin: 0;
        color: #e4e7ff !important;
        line-height: 1.6;
    }

    .hero-eyebrow {
        color: #d4d6ff;
        font-size: .68rem;
        font-weight: 800;
        letter-spacing: .15em;
    }

    .hero-icon {
        margin-right: 1rem;
        color: #ffffff;
        font-size: 3.6rem;
        opacity: .9;
    }

    .stat-card, .subject-card, .activity-card {
        border: 1px solid var(--line);
        border-radius: 16px;
        background: #ffffff;
        padding: 1.1rem 1.2rem;
        box-shadow: 0 4px 16px rgba(16,24,40,.035);
    }

    .stat-card {
        min-height: 150px;
    }

    .stat-icon, .subject-icon {
        font-size: 1.35rem;
    }

    .stat-value {
        margin-top: .55rem;
        color: #111827;
        font-family: 'Manrope', sans-serif;
        font-size: 1.8rem;
        font-weight: 800;
        letter-spacing: -.04em;
    }

    .stat-label, .subject-code {
        color: #526174;
        font-size: .82rem;
        font-weight: 600;
    }

    .subject-card {
        min-height: 196px;
        transition: transform .16s ease, box-shadow .16s ease;
    }

    .subject-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 26px rgba(16,24,40,.08);
    }

    .subject-code {
        margin-top: .75rem;
        color: #667085;
        font-size: .74rem;
        letter-spacing: .06em;
        text-transform: uppercase;
    }

    .subject-name {
        min-height: 44px;
        margin: .4rem 0 1rem;
        color: #182230;
        font-size: .98rem;
        font-weight: 750;
        line-height: 1.35;
    }

    .progress-row {
        display: flex;
        justify-content: space-between;
        margin-bottom: .45rem;
        color: #667085;
        font-size: .75rem;
    }

    .progress-row b {
        color: #182230;
    }

    .progress-track {
        height: 7px;
        overflow: hidden;
        border-radius: 20px;
        background: #e9edf5;
    }

    .progress-fill {
        height: 100%;
        border-radius: 20px;
        background: linear-gradient(90deg, #4f46e5, #8b85ff);
    }

    .activity-card {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem 1.2rem;
    }

    .activity-icon {
        display: flex;
        width: 46px;
        height: 46px;
        flex: 0 0 46px;
        align-items: center;
        justify-content: center;
        border-radius: 13px;
        background: #eeedff;
        font-size: 1.25rem;
    }

    .activity-content {
        flex: 1;
    }

    .activity-title {
        color: #182230;
        font-weight: 750;
    }

    .activity-subtitle {
        margin-top: .2rem;
        color: #667085;
        font-size: .84rem;
    }

    .activity-action {
        color: #4f46e5;
        font-size: .84rem;
        font-weight: 750;
    }

    .login-wrap {
        max-width: 460px;
        margin: 1rem auto;
        border: 1px solid var(--line);
        border-radius: 22px;
        background: #ffffff;
        padding: 1.8rem 2rem;
        box-shadow: 0 16px 42px rgba(16,24,40,.08);
    }

    .login-brand {
        text-align: center;
        color: #111827;
        font-family: 'Manrope', sans-serif;
        font-size: 1.55rem;
        font-weight: 800;
    }

    .login-brand span {
        color: #4f46e5;
    }

    .login-title {
        margin-top: .8rem;
        text-align: center;
        color: #111827;
        font-family: 'Manrope', sans-serif;
        font-size: 1.55rem;
        font-weight: 800;
        letter-spacing: -.035em;
    }

    .login-subtitle {
        margin: .35rem 0 1rem;
        text-align: center;
        color: #526174;
    }

    .login-footer {
        margin-top: 1rem;
        text-align: center;
        color: #667085;
        font-size: .84rem;
    }

    [data-testid="stAlert"] {
        border-radius: 12px;
    }

    @media (max-width: 900px) {
        [data-testid="stMain"] .block-container {
            padding: 1.4rem 1.2rem 2.2rem;
        }

        .hero-card {
            min-height: 160px;
            padding: 1.4rem;
        }
    }

    @media (max-width: 600px) {
        .hero-icon {
            display: none;
        }

        .login-wrap {
            padding: 1.4rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)


def sidebar():
    with st.sidebar:
        st.markdown(
            '<div class="brand"><div class="brand-mark">E</div>'
            '<div>Edu<span>AI</span><small class="brand-tagline">Learning workspace</small></div></div>',
            unsafe_allow_html=True,
        )

        if st.session_state.get("role") == "Admin":
            st.markdown('<div class="nav-caption">Admin workspace</div>', unsafe_allow_html=True)
            sections = [
                ("overview", "Dashboard", "▦"),
                ("academic", "Academic structure", "⌂"),
                ("materials", "Syllabus & materials", "▤"),
                ("users", "User management", "♙"),
                ("ai", "AI quality", "✦"),
                ("history", "Change history", "◷"),
            ]
            current = st.session_state.get("admin_section", "overview")
            for section, label, icon in sections:
                if st.button(
                    f"{icon}  {label}",
                    key=f"admin_nav_{section}",
                    type="primary" if section == current else "secondary",
                    use_container_width=True,
                ):
                    st.session_state.admin_section = section
                    st.switch_page("pages/11_Admin_Dashboard.py")
                    st.stop()
            st.page_link(
                "pages/13_AI_Performance.py",
                label="Speed & efficiency",
                icon=":material/speed:",
                use_container_width=True,
            )
        elif st.session_state.get("role") == "Teacher":
            st.markdown('<div class="nav-caption">Teacher workspace</div>', unsafe_allow_html=True)
            st.page_link("pages/12_Teacher_Dashboard.py", label="Teacher dashboard", icon=":material/co_present:", use_container_width=True)
        else:
            st.markdown('<div class="nav-caption">Learning workspace</div>', unsafe_allow_html=True)
            pages = [
                ("app.py", "Dashboard", ":material/dashboard:"),
                ("pages/2_Courses.py", "My courses", ":material/school:"),
                ("pages/3_Subjects.py", "Subjects", ":material/menu_book:"),
                ("pages/4_Documents.py", "Documents", ":material/folder_open:"),
                ("pages/5_Syllabus.py", "Syllabus", ":material/description:"),
                ("pages/6_AI_Tutor.py", "AI tutor", ":material/auto_awesome:"),
                ("pages/7_History.py", "Chat history", ":material/history:"),
                ("pages/8_Practice.py", "Practice", ":material/edit_note:"),
                ("pages/9_Progress.py", "Progress", ":material/trending_up:"),
            ]
            for page, label, icon in pages:
                st.page_link(page, label=label, icon=icon, use_container_width=True)

        st.markdown("---")
        st.markdown('<div class="nav-caption">Account</div>', unsafe_allow_html=True)
        st.page_link("pages/10_Settings.py", label="Settings", icon=":material/settings:", use_container_width=True)
        if st.button("↪  Sign out", key="sidebar_logout", use_container_width=True):
            for key in (
                "authenticated", "user_id", "user_email", "user_name", "role", "admin_section",
                "active_chat_id", "loaded_chat_id", "chat_messages", "last_practice",
            ):
                st.session_state.pop(key, None)
            st.switch_page("pages/1_Login.py")


def page_header(title, subtitle=""):
    title = html.escape(str(title))
    subtitle = html.escape(str(subtitle))
    st.markdown(
        f'<div class="page-heading"><div class="page-eyebrow">EDUAI · LEARNING WORKSPACE</div>'
        f'<div class="page-title">{title}</div><div class="page-subtitle">{subtitle}</div></div>',
        unsafe_allow_html=True,
    )



