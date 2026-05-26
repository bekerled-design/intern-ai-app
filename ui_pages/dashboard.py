import streamlit as st
from database.database import get_test_results, get_user_courses
from database.database import get_notifications
from datetime import datetime
from database.database import get_overdue_courses
from database.database import mark_notification_as_read


def show_dashboard():

    st.title("Панель стажёра")

    if "username" not in st.session_state:
        st.info("Войдите как стажёр.")
        return

    st.markdown(
        f'<div class="section-card"><h2>Добро пожаловать, {st.session_state["username"]} 👋</h2><p>AI-платформа обучения стажёров</p></div>',
        unsafe_allow_html=True
    )
    notifications = get_notifications(
    st.session_state["user_id"]
)

    if notifications:

        st.subheader("Уведомления")

        for notification in notifications[:3]:

            notification_id = notification[0]
            message = notification[1]

            st.warning(message)

            if st.button(
                "Отметить как прочитанное",
                key=f"read_notification_{notification_id}"
            ):

                mark_notification_as_read(notification_id)

                st.rerun()

    today = datetime.now().date().isoformat()

    overdue_courses = get_overdue_courses(
        st.session_state["user_id"],
        today
    )

    if overdue_courses:

        st.subheader("Просроченные курсы")

        for course in overdue_courses:

            st.error(
            f"⚠️ {course[0]} — дедлайн был {course[1]}"
        )

    if "user_id" not in st.session_state:
        return

    results = get_test_results(st.session_state["user_id"])
    user_courses = get_user_courses(st.session_state["user_id"])

    total_courses = len(user_courses)
    total_tests = len(results)

    average_score = 0

    if results:
        scores = [result[0] for result in results]
        average_score = sum(scores) / len(scores)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-title">Курсов</div><div class="metric-value">{total_courses}</div></div>',
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f'<div class="metric-card"><div class="metric-title">Тестов</div><div class="metric-value">{total_tests}</div></div>',
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            f'<div class="metric-card"><div class="metric-title">Средний балл</div><div class="metric-value">{average_score:.1f}%</div></div>',
            unsafe_allow_html=True
        )

    st.divider()

    st.subheader("Общий прогресс")

    st.progress(min(average_score / 100, 1.0))