import streamlit as st
from database.database import save_ai_chat_message
from ai.mentor_chat import ask_ai_mentor


def show_mentor_page(client):

    st.header("AI-помощник стажёра")

    user_question = st.text_input(
        "Задайте вопрос по материалам компании",
        placeholder="Например: как обрабатывать жалобы клиентов?"
    )

    if st.button(
        "Спросить AI",
        key="ask_ai_button"
    ):

        if "course_data" not in st.session_state:
            st.warning("Сначала сгенерируйте курс.")
            return

        if "company_material" not in st.session_state:
            st.warning("Сначала загрузите материалы компании.")
            return

        with st.spinner("ИИ анализирует материалы компании..."):

            ai_answer = ask_ai_mentor(
                client,
                st.session_state["company_material"],
                st.session_state["course_data"],
                user_question
            )

            st.subheader("Ответ AI")
            st.write(ai_answer)
            if "user_id" in st.session_state:

                save_ai_chat_message(
                    st.session_state["user_id"],
                    user_question,
                    ai_answer
                )