from ai.video_transcriber import transcribe_video
from ui_pages.admin_page import show_admin_page
from ai.embeddings import create_embedding
from database.database import save_material_chunk
from utils.text_search import split_text_into_chunks
from ui_pages.materials_page import show_materials_page
from database.database import material_exists
from ui_pages.courses_page import show_courses_page
from database.database import save_company_material, get_company_materials
from ui_pages.progress_page import show_progress_page
from ui_pages.mentor_page import show_mentor_page
from ui_pages.test_page import show_test_page
from ui_pages.course_page import show_course_page
from ui_pages.dashboard import show_dashboard
from database.database import get_course_by_id
from database.database import get_user_courses
from database.database import save_course
from database.database import create_user, get_user
from database.database import get_test_results
from database.database import save_test_result
from database.database import create_tables
from utils.file_loader import read_uploaded_file, save_uploaded_file
from ai.weakness_analyzer import analyze_weaknesses
from ai.mentor_chat import ask_ai_mentor
from ai.course_generator import generate_course
import json
import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

st.set_page_config(
    page_title="AI-платформа для стажёров",
    page_icon="🎓",
    layout="wide"
)
create_tables()
st.markdown("""
<style>
.main {
    background-color: #F7F8FA;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

.metric-card {
    background: white;
    padding: 24px;
    border-radius: 16px;
    border: 1px solid #E5E7EB;
    box-shadow: 0 4px 12px rgba(0,0,0,0.04);
}

.metric-title {
    color: #6B7280;
    font-size: 14px;
    margin-bottom: 8px;
}

.metric-value {
    color: #111827;
    font-size: 32px;
    font-weight: 700;
}

.section-card {
    background: white;
    color: #111827;
    padding: 24px;
    border-radius: 16px;
    border: 1px solid #E5E7EB;
    margin-bottom: 16px;
}

.section-card h2 {
    color: #111827;
}

.section-card h3 {
    color: #111827;
    margin-bottom: 8px;
}

.section-card p {
    color: #4B5563;
}
.section-card {
    background: white;
    color: #111827;
}
section[data-testid="stSidebar"] {
    background-color: #111827;
}

[data-testid="stSidebar"] {
    background-color: #111827 !important;
}

[data-testid="stSidebar"] * {
    color: white !important;
}
div[data-testid="stButton"] > button {
    background-color: #2563EB !important;
    color: white !important;
    border-radius: 12px !important;
    border: none !important;
    padding: 12px 20px !important;
    font-weight: 600 !important;
}

div[data-testid="stButton"] > button:hover {
    background-color: #1D4ED8 !important;
    color: white !important;
}
.course-card {
    background: white;
    color: #111827;
    padding: 22px;
    border-radius: 16px;
    border: 1px solid #E5E7EB;
    box-shadow: 0 4px 12px rgba(0,0,0,0.04);
    margin-bottom: 16px;
}

.course-card h3 {
    color: #111827;
    margin-bottom: 8px;
}

.course-card p {
    color: #4B5563;
    margin-bottom: 4px;
}
.module-card {
    background: white;
    color: #111827;
    padding: 20px;
    border-radius: 16px;
    border: 1px solid #E5E7EB;
    box-shadow: 0 4px 12px rgba(0,0,0,0.04);
    margin-bottom: 16px;
}

.module-card h3 {
    color: #111827;
    margin-bottom: 10px;
}

.module-card p {
    color: #4B5563;
    line-height: 1.6;
}
</style>
""", unsafe_allow_html=True)
st.title("AI-платформа для обучения стажёров")

st.write(
    "Прототип приложения, где компания загружает материалы, "
    "а искусственный интеллект создаёт учебный курс для стажёра."
)

st.sidebar.header("Авторизация")

username = st.sidebar.text_input("Логин")

password = st.sidebar.text_input(
    "Пароль",
    type="password"
)

if st.sidebar.button("Войти", key="login_button"):

    user = get_user(username, password)

    if user:

        st.session_state["user_id"] = user[0]
        st.session_state["username"] = username

        st.sidebar.success(f"Вы вошли как {username}")

    else:

        user_id = create_user(username, password)

        st.session_state["user_id"] = user_id
        st.session_state["username"] = username

        st.sidebar.success(f"Создан новый пользователь: {username}")


st.sidebar.divider()
if "user_id" in st.session_state:

    if st.sidebar.button("Выйти", key="logout_button"):

        st.session_state.clear()

        st.rerun()


if "page" not in st.session_state:
    st.session_state["page"] = "Главная"
    
if "user_id" not in st.session_state:

    st.warning("Войдите в аккаунт")

    st.stop()

page = st.sidebar.radio(
    "Навигация",
    [
        "Главная",
        "Курс",
        "Тест",
        "AI-помощник",
        "Прогресс",
        "Мои курсы",
        "Материалы",
        "Админ"
    ],
    index=[
        "Главная",
        "Курс",
        "Тест",
        "AI-помощник",
        "Прогресс",
        "Мои курсы",
        "Материалы",
        "Админ"
    ].index(st.session_state["page"])
)
if page != st.session_state["page"]:
    st.session_state["page"] = page
    st.rerun()



if "user_id" in st.session_state:

    saved_materials = get_company_materials(
        st.session_state["user_id"]
    )

    if saved_materials:

        combined_materials = ""

        for material in saved_materials:
            combined_materials += f"""

Файл: {material[0]}

{material[1]}

"""

        st.session_state["company_material"] = combined_materials


if page == "Главная":

    show_dashboard()


    st.markdown("""
<div class="section-card">
    <h3>Загрузка материалов компании</h3>
    <p>
        Загрузите внутренние документы,
        регламенты или инструкции для
        генерации AI-курса.
    </p>
</div>
""", unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
    "Загрузите текстовый файл компании",
        type=["txt", "csv", "xlsx", "docx", "pdf", "mp4", "mp3", "wav", "m4a", "webm"],
    accept_multiple_files=True
    )

    all_materials_text = ""

    if uploaded_files:

        all_materials_text = ""

        for uploaded_file in uploaded_files:

                if uploaded_file.name.lower().endswith(
                    (".mp4", ".mp3", ".wav", ".m4a", ".webm")
                ):
                    with st.spinner(f"Распознаю аудио/видео: {uploaded_file.name}..."):
                        try:
                            file_content = transcribe_video(client, uploaded_file)
                            st.text_area(
                                "Транскрипция аудио",
                                file_content,
                                height=400
                            )
                            if not file_content.strip():
                                st.warning("Не удалось распознать аудио.")
                                continue
                        except Exception as error:
                            st.error(f"Не удалось распознать файл {uploaded_file.name}")
                            st.code(str(error))
                            continue
                else:
                    file_content = read_uploaded_file(uploaded_file)

                save_uploaded_file(uploaded_file, file_content)

                if "user_id" in st.session_state:

                    if not material_exists(
                        st.session_state["user_id"],
                        uploaded_file.name
                    ):

                        save_company_material(
                            st.session_state["user_id"],
                            uploaded_file.name,
                            file_content
                        )

                        if len(file_content) > 150000:
                            file_content = file_content[:150000]

                        chunks = split_text_into_chunks(file_content)
                
                        with st.spinner(f"Создаю embeddings для файла: {uploaded_file.name}..."):
                            for chunk in chunks:
                                try:
                                    embedding = create_embedding(client, chunk)
                                except Exception:
                                    continue

                                save_material_chunk(
                                    st.session_state["user_id"],
                                    uploaded_file.name,
                                    chunk,
                                    embedding
                                )

                    all_materials_text += f"""

        Файл: {uploaded_file.name}

        {file_content}

        """

                st.success(f"Файл загружен: {uploaded_file.name}")


                st.session_state["company_material"] = all_materials_text
                st.session_state["current_upload_material"] = all_materials_text

        st.text_area(
            "Объединённые материалы",
            st.session_state["company_material"],
            height=300
        )
        material_for_course = st.session_state.get(
            "current_upload_material",
            ""
        )
        if st.button("Сгенерировать курс", key="generate_course_button"):

            with st.spinner("ИИ анализирует материал и создаёт курс..."):

                try:

                    course_data = generate_course(
                        client,
                        material_for_course
                    )

                    st.session_state["course_data"] = course_data

                    if "user_id" in st.session_state:

                        course_id = save_course(
                            st.session_state["user_id"],
                            course_data
                        )

                        st.session_state["current_course_id"] = course_id

                    st.session_state["page"] = "Курс"
                    st.success("Курс успешно сгенерирован")
                    st.rerun()

                except Exception as error:

                    st.error("Ошибка генерации курса")
                    st.code(str(error))
st.divider()

if page == "Курс":
    show_course_page()

st.divider()

if page == "Тест":
    show_test_page(client)

st.divider()

if page == "AI-помощник":
    show_mentor_page(client)

st.divider()

if page == "Прогресс":
    show_progress_page()

st.divider()

if page == "Мои курсы":
    show_courses_page()

if page == "Материалы":
    show_materials_page()

    st.divider()
if page == "Админ":
    show_admin_page(client)
    
    st.divider()