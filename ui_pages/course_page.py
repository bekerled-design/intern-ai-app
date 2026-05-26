import streamlit as st
from database.database import add_activity
from database.database import (
    save_module_progress,
    get_completed_modules
)
def generate_course(client, file_content):

    file_content = file_content[:12000]

    response = client.responses.create(
        model="gpt-4.1-mini",
    )
def show_course_page():

    st.header("Курс стажёра")

    if "course_data" not in st.session_state:
        st.info("Курс пока не создан.")
        return

    course_data = st.session_state["course_data"]
    course_id = st.session_state.get("current_course_id")
    completed_modules = []

    if (
        "user_id" in st.session_state
        and course_id
    ):

        completed_modules = get_completed_modules(
            st.session_state["user_id"],
            course_id
        )
    total_modules = len(course_data["modules"])

    progress = 0

    if total_modules > 0:
        progress = len(completed_modules) / total_modules

    st.subheader("Прогресс курса")

    st.progress(progress)

    st.write(f"Пройдено модулей: {len(completed_modules)} из {total_modules}")
    st.subheader(course_data["course_title"])

    st.header("Модули")

    for index, module in enumerate(course_data["modules"]):
        status = "✅" if index in completed_modules else "📘"
        st.markdown(
            f'''
            <div class="module-card">
                <h3>{status} {module["title"]}</h3>
                {module["description"]}
            </div>
            ''',
            unsafe_allow_html=True
        )

        if st.button(
            "Изучить модуль",
            key=f"open_module_{index}"
        ):
            st.session_state["opened_module"] = index
            if (
                index not in completed_modules
                and "user_id" in st.session_state
                and course_id
            ):

                save_module_progress(
                    st.session_state["user_id"],
                    course_id,
                    index
                )

                st.success("Модуль завершён")
                
                add_activity(
                        st.session_state["user_id"],
                        f"Завершил модуль: {module['title']}"
                    )
                st.rerun()

    if "opened_module" in st.session_state:

        opened_module = st.session_state["opened_module"]
        if opened_module >= len(course_data["modules"]):
            del st.session_state["opened_module"]
            st.rerun()

        module = course_data["modules"][opened_module]

        st.divider()
        st.header(f"📖 {module['title']}")
        st.write(module.get("content", module["description"]))

    st.header("Практическое задание")
    st.write(course_data["practical_task"])