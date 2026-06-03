import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from database.database import (
    create_tables, create_user, get_user,
    get_company_materials,
)
from ui_pages.dashboard import show_dashboard
from ui_pages.course_page import show_course_page
from ui_pages.test_page import show_test_page
from ui_pages.mentor_page import show_mentor_page
from ui_pages.profile_page import show_profile_page
from ui_pages.courses_page import show_courses_page
from ui_pages.materials_page import show_materials_page
from ui_pages.admin_page import show_admin_page

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(
    page_title="Стажировка",
    page_icon="🎓",
    layout="wide"
)

create_tables()

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
#MainMenu, footer,
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"] { display: none !important; }

.stApp { background-color: #F4F6FB; color: #111827; }

/* Тёмный цвет текста — только для текстовых тегов, не для div/span */
.stApp p, .stApp label, .stApp li,
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {
    color: #111827;
}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
    color: #111827;
}

.block-container {
    padding: 2rem 3rem !important;
    max-width: 1200px !important;
    margin: 0 auto !important;
}

/* ── Sidebar ─────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid #E5E7EB;
    min-width: 260px !important;
    max-width: 260px !important;
    width: 260px !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 1.5rem 1rem !important;
}
[data-testid="stSidebar"] button {
    background: transparent !important;
    color: #374151 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    box-shadow: none !important;
    width: 100% !important;
    text-align: left !important;
    justify-content: flex-start !important;
    display: flex !important;
    align-items: center !important;
}
[data-testid="stSidebar"] button:hover {
    background: #F3F4F6 !important;
    color: #111827 !important;
}
[data-testid="stSidebarCollapseButton"] { display: none !important; }

.nav-active {
    background: #EEF2FF;
    color: #2563EB;
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 2px;
    display: block;
}

/* ── Cards ───────────────────────────────────── */
.card {
    background: white;
    border-radius: 16px;
    border: 1px solid #E5E7EB;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    padding: 24px;
    margin-bottom: 16px;
}
.metric-card {
    background: white;
    border-radius: 14px;
    border: 1px solid #E5E7EB;
    box-shadow: 0 2px 6px rgba(0,0,0,0.04);
    padding: 20px 16px;
    text-align: center;
    margin-bottom: 12px;
}
.metric-value { font-size: 26px; font-weight: 700; color: #111827; }
.metric-label { font-size: 12px; color: #6B7280; margin-top: 4px; }

/* ── Badges ──────────────────────────────────── */
.badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}
.badge-blue   { background: #DBEAFE; color: #1E40AF; }
.badge-green  { background: #D1FAE5; color: #065F46; }
.badge-yellow { background: #FEF3C7; color: #92400E; }
.badge-gray   { background: #F3F4F6; color: #374151; }

/* ── Module status icons ─────────────────────── */
.module-status {
    width: 28px; height: 28px; border-radius: 50%;
    display: inline-flex; align-items: center;
    justify-content: center; font-size: 13px; flex-shrink: 0;
}
.status-done    { background: #D1FAE5; color: #10B981; }
.status-active  { background: #DBEAFE; color: #2563EB; }
.status-pending { background: #F3F4F6; color: #9CA3AF; }

/* ── Task cards ──────────────────────────────── */
.task-card {
    background: white;
    border-radius: 12px;
    border: 1px solid #E5E7EB;
    padding: 14px 16px;
    margin-bottom: 8px;
    display: flex;
    align-items: flex-start;
    gap: 12px;
}
.task-title { font-weight: 600; color: #111827; font-size: 14px; }
.task-meta  { font-size: 12px; color: #6B7280; margin-top: 2px; }

/* ── Progress bar ────────────────────────────── */
[data-testid="stProgress"] > div > div {
    background-color: #2563EB !important;
    border-radius: 4px;
}
[data-testid="stProgress"] > div {
    background-color: #E5E7EB;
    border-radius: 4px;
    height: 8px !important;
}

/* ── Text inputs ─────────────────────────────── */
.stTextInput > div > div > input {
    border-radius: 10px !important;
    border: 1.5px solid #E5E7EB !important;
    padding: 12px 14px !important;
    background: white !important;
    color: #111827 !important;
    font-size: 14px !important;
}
.stTextInput > label {
    color: #374151 !important;
    font-size: 14px !important;
    font-weight: 500 !important;
}

/* ── Primary button ──────────────────────────── */
button[kind="primary"] {
    background-color: #2563EB !important;
    color: white !important;
    border-radius: 10px !important;
    border: none !important;
    font-weight: 600 !important;
    box-shadow: none !important;
}
button[kind="primary"]:hover { background-color: #1D4ED8 !important; }

/* ── Radio options (A/B/C/D style) ──────────── */
.stRadio > div {
    gap: 8px !important;
    flex-direction: column !important;
}
.stRadio > div > label {
    background: white !important;
    border: 1.5px solid #E5E7EB !important;
    border-radius: 10px !important;
    padding: 14px 16px !important;
    cursor: pointer !important;
    font-size: 14px !important;
    color: #111827 !important;
    width: 100% !important;
    margin: 0 !important;
    transition: border-color 0.15s, background 0.15s !important;
}
.stRadio > div > label:hover {
    border-color: #2563EB !important;
    background: #EEF2FF !important;
}
.stRadio > div > label:has(input:checked) {
    border-color: #2563EB !important;
    background: #EEF2FF !important;
    color: #1E40AF !important;
    font-weight: 600 !important;
}

/* ── Expander ────────────────────────────────── */
[data-testid="stExpander"] {
    background: white;
    border: 1px solid #E5E7EB !important;
    border-radius: 12px !important;
    margin-bottom: 8px;
}

/* ── Page / section titles ───────────────────── */
.page-title {
    font-size: 22px;
    font-weight: 700;
    color: #111827;
    margin-bottom: 20px;
}
.section-title {
    font-size: 15px;
    font-weight: 600;
    color: #111827;
    margin: 16px 0 10px;
}

/* ── Font family ─────────────────────────────── */
.stApp, .stApp * {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
        'Inter', 'Helvetica Neue', sans-serif !important;
}

/* ── Card hover ──────────────────────────────── */
.card {
    transition: box-shadow 0.2s ease, transform 0.15s ease;
}
.card:hover {
    box-shadow: 0 4px 20px rgba(0,0,0,0.09) !important;
}

/* ── Lesson content typography ───────────────── */
.lesson-prose .stMarkdown p {
    font-size: 15px !important;
    line-height: 1.85 !important;
    color: #1F2937 !important;
    margin-bottom: 16px !important;
}
.lesson-prose .stMarkdown h1,
.lesson-prose .stMarkdown h2,
.lesson-prose .stMarkdown h3 {
    color: #111827 !important;
    font-weight: 700 !important;
    margin-top: 28px !important;
    margin-bottom: 12px !important;
}
.lesson-prose .stMarkdown ul,
.lesson-prose .stMarkdown ol {
    padding-left: 24px !important;
    margin-bottom: 16px !important;
}
.lesson-prose .stMarkdown li {
    margin-bottom: 8px !important;
    line-height: 1.7 !important;
    color: #1F2937 !important;
}
.lesson-prose .stMarkdown strong { color: #111827 !important; }
.lesson-prose .stMarkdown code {
    background: #F3F4F6 !important;
    padding: 2px 6px !important;
    border-radius: 4px !important;
    font-size: 13px !important;
    color: #1F2937 !important;
}

/* Global prose improvement */
[data-testid="stMain"] .stMarkdown p {
    font-size: 14px;
    line-height: 1.75;
    color: #374151;
}
[data-testid="stMain"] .stMarkdown li {
    line-height: 1.7;
    color: #374151;
}

/* ── Task card (amber highlight) ─────────────── */
.task-highlight {
    background: linear-gradient(135deg, #FFFBEB, #FEF3C7);
    border: 1.5px solid #F59E0B;
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 16px;
}

/* ── Mentor hero ─────────────────────────────── */
.mentor-hero {
    background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
    border-radius: 20px;
    padding: 36px 40px;
    color: white;
    margin-bottom: 24px;
}

/* ── Q&A bubble ──────────────────────────────── */
.qa-question {
    background: #EEF2FF;
    border-left: 3px solid #2563EB;
    border-radius: 0 12px 12px 0;
    padding: 16px 20px;
    margin-bottom: 16px;
}
.qa-answer {
    background: white;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

/* ── Lesson header ───────────────────────────── */
.lesson-header {
    background: white;
    border-bottom: 1px solid #E5E7EB;
    padding: 20px 0 16px;
    margin-bottom: 28px;
}

/* ── Breadcrumb ──────────────────────────────── */
.breadcrumb {
    font-size: 13px;
    color: #6B7280;
    margin-bottom: 8px;
}
.breadcrumb span { color: #2563EB; cursor: pointer; }

/* ── Bigger text area ────────────────────────── */
.stTextArea > div > div > textarea {
    border-radius: 12px !important;
    border: 1.5px solid #E5E7EB !important;
    font-size: 14px !important;
    line-height: 1.6 !important;
    padding: 14px !important;
    background: white !important;
    color: #111827 !important;
    resize: vertical !important;
}
.stTextArea > div > div > textarea:focus {
    border-color: #2563EB !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important;
}

/* ── Select box ──────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
    border-radius: 10px !important;
    border: 1.5px solid #E5E7EB !important;
}

/* ── Info/Warning/Error boxes ────────────────── */
[data-testid="stAlert"] {
    border-radius: 12px !important;
}

/* ── Spinner text ────────────────────────────── */
[data-testid="stSpinner"] { color: #2563EB !important; }

/* ── File uploader ───────────────────────────── */
[data-testid="stFileUploaderDropzone"] {
    border-radius: 12px !important;
    background: white !important;
    border: 2px dashed #C7D2FE !important;
    padding: 24px !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: #2563EB !important;
    background: #F8FAFF !important;
}

/* Прячем ВЕСЬ родной текст/иконку зоны инструкций, рисуем свой */
[data-testid="stFileUploaderDropzoneInstructions"] {
    color: transparent !important;
    position: relative !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] * {
    display: none !important;
}
[data-testid="stFileUploaderDropzoneInstructions"]::before {
    content: "Перетащите файлы сюда" !important;
    display: block !important;
    color: #6B7280 !important;
    font-size: 14px !important;
    font-weight: 500 !important;
}

/* Кнопка "Browse files" → наш синий стиль, свой текст */
[data-testid="stFileUploaderDropzone"] button {
    background: #2563EB !important;
    color: transparent !important;
    border: none !important;
    border-radius: 10px !important;
    box-shadow: none !important;
    position: relative !important;
    min-width: 150px !important;
    height: 40px !important;
}
[data-testid="stFileUploaderDropzone"] button:hover {
    background: #1D4ED8 !important;
}
[data-testid="stFileUploaderDropzone"] button > * {
    display: none !important;
}
[data-testid="stFileUploaderDropzone"] button::after {
    content: "Выбрать файлы" !important;
    color: white !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    position: absolute !important;
    top: 50% !important;
    left: 50% !important;
    transform: translate(-50%, -50%) !important;
    white-space: nowrap !important;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Login page
# ─────────────────────────────────────────────────────────────────────────────
def _show_login():
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown("""
        <div style="text-align:center;padding:40px 0 0;">
            <div style="width:60px;height:60px;background:#2563EB;border-radius:16px;
                display:inline-flex;align-items:center;justify-content:center;
                font-size:30px;color:white;margin-bottom:14px;">🎓</div>
            <div style="font-size:26px;font-weight:700;color:#111827;margin-bottom:6px;">
                Стажировка
            </div>
            <div style="font-size:14px;color:#6B7280;line-height:1.7;margin-bottom:32px;">
                Платформа для обучения<br>и развития стажёров в компании
            </div>
        </div>
        """, unsafe_allow_html=True)

        username = st.text_input("Логин", placeholder="Введите логин", key="li_username")
        password = st.text_input("Пароль", type="password", placeholder="Введите пароль", key="li_password")

        if st.button("Войти", use_container_width=True, type="primary", key="li_btn"):
            if not username.strip() or not password.strip():
                st.error("Введите логин и пароль")
                return
            user = get_user(username.strip(), password)
            if user:
                st.session_state["user_id"] = user[0]
                st.session_state["username"] = username.strip()
            else:
                uid = create_user(username.strip(), password)
                st.session_state["user_id"] = uid
                st.session_state["username"] = username.strip()
            st.session_state["page"] = "Главная"
            st.rerun()

        st.markdown("""
        <div style="text-align:center;margin-top:16px;font-size:13px;color:#9CA3AF;">
            Новый аккаунт создаётся автоматически при первом входе
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar navigation
# ─────────────────────────────────────────────────────────────────────────────
_NAV = [
    ("🏠", "Главная"),
    ("📚", "Модули"),
    ("📝", "Тест"),
    ("💬", "AI-наставник"),
    ("👤", "Профиль"),
    ("📁", "Мои курсы"),
    ("📄", "Материалы"),
    ("⚙️", "Администратор"),
]


def _show_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:10px;padding:4px 4px 24px;">
            <div style="width:36px;height:36px;background:#2563EB;border-radius:9px;
                display:flex;align-items:center;justify-content:center;
                font-size:18px;color:white;flex-shrink:0;">🎓</div>
            <span style="font-size:17px;font-weight:700;color:#111827;">Стажировка</span>
        </div>
        """, unsafe_allow_html=True)

        current = st.session_state.get("page", "Главная")
        for icon, name in _NAV:
            if current == name:
                st.markdown(
                    f'<div class="nav-active">{icon}&nbsp;&nbsp;{name}</div>',
                    unsafe_allow_html=True
                )
            else:
                if st.button(f"{icon}  {name}", key=f"nav_{name}", use_container_width=True):
                    st.session_state["page"] = name
                    st.rerun()

        st.markdown("<hr style='border-color:#E5E7EB;margin:16px 0;'>", unsafe_allow_html=True)

        uname = st.session_state.get("username", "")
        initial = uname[0].upper() if uname else "U"
        st.markdown(f"""
        <div style="padding:4px;">
            <div style="display:flex;align-items:center;gap:10px;">
                <div style="width:34px;height:34px;background:#EEF2FF;border-radius:50%;
                    display:flex;align-items:center;justify-content:center;
                    font-size:14px;color:#2563EB;font-weight:700;flex-shrink:0;">{initial}</div>
                <div>
                    <div style="font-size:13px;font-weight:600;color:#111827;">{uname}</div>
                    <div style="font-size:11px;color:#6B7280;">Стажёр</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Выйти", key="logout_btn", use_container_width=True):
            st.session_state.clear()
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
if "user_id" not in st.session_state:
    _show_login()
    st.stop()

# Load saved materials into session state (once per session)
if "company_material" not in st.session_state:
    saved = get_company_materials(st.session_state["user_id"])
    if saved:
        combined = "".join(f"\n\nФайл: {m[0]}\n\n{m[1]}\n\n" for m in saved)
        st.session_state["company_material"] = combined

_show_sidebar()

page = st.session_state.get("page", "Главная")

if page == "Главная":
    show_dashboard()
elif page == "Модули":
    show_course_page()
elif page == "Тест":
    show_test_page(client)
elif page == "AI-наставник":
    show_mentor_page(client)
elif page == "Профиль":
    show_profile_page()
elif page == "Мои курсы":
    show_courses_page()
elif page == "Материалы":
    show_materials_page(client)
elif page == "Администратор":
    show_admin_page(client)
