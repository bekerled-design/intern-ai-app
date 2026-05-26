import streamlit as st

from ai.retraining_generator import generate_retraining_course
from database.database import save_course
from database.database import create_notification
from database.database import get_user_activity
from ai.recommendations import (
    generate_recommendations
)

from database.database import (
    get_all_users,
    get_user_courses,
    get_test_results,
    get_weak_topics
)


def show_admin_page(client):

    st.header("Админ-панель")

    users = get_all_users()

    if not users:
        st.info("Пользователей пока нет.")
        return

    for user in users:

        user_id = user[0]
        username = user[1]

        courses = get_user_courses(user_id)

        results = get_test_results(user_id)

        average_score = 0

        if results:
            scores = [result[0] for result in results]
            average_score = sum(scores) / len(scores)

        with st.expander(f"👤 {username}"):
            weak_topics = get_weak_topics(user_id)

            if weak_topics:

                    st.subheader("Слабые темы")

                    for topic in weak_topics[-5:]:
                        st.write(f"- {topic}")

            else:
                st.info("Слабых тем пока нет.")
        recommendations = generate_recommendations(
        weak_topics
    )

        if recommendations:

            st.subheader("AI-рекомендации")

            for rec in recommendations:
                st.write(f"✅ {rec}")

            st.write(f"Курсов: {len(courses)}")

            st.write(f"Тестов пройдено: {len(results)}")

            st.write(
                f"Средний балл: {average_score:.1f}%"
            )
            activity = get_user_activity(user_id)

            if activity:

                st.subheader("Активность")

                for action, created_at in activity:

                    st.write(
                        f"🕒 {created_at} — {action}"
                    )
        if weak_topics:
            due_date = st.date_input(
                "Дедлайн доп. обучения",
                key=f"deadline_{user_id}"
            )
            if st.button(
    "Создать доп. обучение",
    key=f"retraining_{user_id}"
):

                if "company_material" not in st.session_state:
                    st.warning("Сначала загрузите материалы компании на Главной.")
                else:
                    with st.spinner("ИИ создаёт дополнительное обучение..."):

                        retraining_course = generate_retraining_course(
                            client,
                            weak_topics[-5:],
                            st.session_state["company_material"]
                        )

                        course_id = save_course(
                            user_id,
                            retraining_course,
                            str(due_date)
                        )

                        create_notification(
                            user_id,
                            "Вам назначено дополнительное обучение."
                        )

                        st.success(
                            f"Дополнительное обучение создано. ID курса: {course_id}"
                        )