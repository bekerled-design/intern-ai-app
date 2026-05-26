import json
import streamlit as st
from database.database import get_user_courses, get_course_by_id
from datetime import datetime


def show_courses_page():

    st.header("Мои курсы")

    if "user_id" not in st.session_state:
        st.info("Войдите как стажёр.")
        return

    user_courses = get_user_courses(
        st.session_state["user_id"]
    )

    if not user_courses:
        st.info("У пользователя пока нет курсов.")
        return

    for course in user_courses:

        course_id = course[0]
        course_title = course[1]
        due_date = course[2]

        deadline_text = due_date if due_date else "Без дедлайна"
        is_overdue = False
        overdue_html = ""
        if due_date:

            deadline_date = datetime.strptime(
                due_date,
                "%Y-%m-%d"
            ).date()

            if deadline_date < datetime.now().date():
                is_overdue = True
            overdue_html = ""

            if is_overdue:

                overdue_html = (
                    "<p style='color:red;'>"
                    "⚠️ Дедлайн просрочен"
                    "</p>"
                )
            st.markdown(
                    f'''
                    <div class="course-card">
                        <h3>{course_title}</h3>
                        <p>Дедлайн: {deadline_text}</p>
                        {overdue_html}
                        <p>AI-сгенерированный курс</p>
                        <p>Нажмите кнопку ниже, чтобы открыть курс.</p>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
        if st.button(
            f"Открыть курс: {course_title}",
            key=f"open_course_{course_id}"
        ):

            saved_course = get_course_by_id(course_id)

            if saved_course:

                course_data = json.loads(saved_course[0])

                st.session_state["course_data"] = course_data
                st.session_state["current_course_id"] = course_id
                st.session_state["page"] = "Курс"

                st.rerun()