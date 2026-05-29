from database.database import save_test_result, save_weak_topic
import streamlit as st
from ai.weakness_analyzer import analyze_weaknesses
from database.database import save_test_result
from database.database import add_activity


def show_test_page(client):

    st.header("Тест по курсу")

    if "course_data" not in st.session_state:
        st.info("Сначала сгенерируйте курс.")
        return

    course_data = st.session_state["course_data"]
    test_questions = course_data["test"]

    user_answers = []

    for index, question in enumerate(test_questions):

        st.subheader(f"Вопрос {index + 1}")

        answer = st.radio(
            question["question"],
            question["options"],
            key=f"test_question_{index}"
        )

        user_answers.append({
            "module": question.get("module", "Без модуля"),
            "question": question["question"],
            "user_answer": answer,
            "correct_answer": question["correct_answer"]
        })
        
    if st.button(
        "Проверить тест",
        key="check_generated_test_button"
    ):

        if "user_id" not in st.session_state:
            st.error("Сначала войдите как стажёр в боковой панели.")
            st.stop()

        correct_count = 0
        wrong_answers = []

        for answer in user_answers:

            if answer["user_answer"] == answer["correct_answer"]:
                correct_count += 1
            else:
                wrong_answers.append(answer)
                save_weak_topic(
                        st.session_state["user_id"],
                        answer["module"]
                    )

        total = len(user_answers)
        score = int((correct_count / total) * 100)

        save_test_result(
            st.session_state["user_id"],
            score
        )
        add_activity(
            st.session_state["user_id"],
            f"Прошёл тест с результатом {score}%"
        )

        st.success(f"Результат: {correct_count} из {total}")
        st.progress(score / 100)
        st.write(f"Прогресс: {score}%")

        if wrong_answers:

            st.subheader("Ошибки")

            for wrong in wrong_answers:

                st.error(
                    f"""
        Модуль: {wrong['module']}

        Вопрос:
        {wrong['question']}

        Ваш ответ:
        {wrong['user_answer']}

        Правильный ответ:
        {wrong['correct_answer']}
        """
        )
            with st.spinner("ИИ анализирует слабые места стажёра..."):

                ai_feedback = analyze_weaknesses(
                    client,
                    wrong_answers
                )

                st.subheader("AI-рекомендации")
                st.write(ai_feedback)

        else:
            st.success("Все ответы правильные!")