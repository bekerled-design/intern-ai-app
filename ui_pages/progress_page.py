import streamlit as st
from database.database import get_test_results


def show_progress_page():

    st.header("Прогресс обучения")

    if "user_id" not in st.session_state:
        st.info("Войдите как стажёр, чтобы увидеть историю прогресса.")
        return

    results = get_test_results(
        st.session_state["user_id"]
    )

    if not results:
        st.info("Результатов пока нет.")
        return

    scores = [result[0] for result in results]

    average_score = sum(scores) / len(scores)
    best_score = max(scores)
    total_tests = len(scores)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-title">Средний результат</div><div class="metric-value">{average_score:.1f}%</div></div>',
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f'<div class="metric-card"><div class="metric-title">Лучший результат</div><div class="metric-value">{best_score}%</div></div>',
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            f'<div class="metric-card"><div class="metric-title">Пройдено тестов</div><div class="metric-value">{total_tests}</div></div>',
            unsafe_allow_html=True
        )

    st.divider()

    st.subheader("Общий прогресс")
    st.progress(min(average_score / 100, 1.0))

    st.divider()

    st.subheader("История тестов")

    for index, score in enumerate(scores):
        st.write(f"Тест {index + 1}: {score}%")