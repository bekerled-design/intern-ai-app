import json
import streamlit as st

from ai.embeddings import create_embedding
from utils.semantic_search import search_similar_chunks
from database.database import (
    get_material_chunks,
    get_ai_chat_history
)

def ask_ai_mentor(client, company_material, course_data, user_question):

    chunks = get_material_chunks(
        st.session_state["user_id"]
    )

    question_embedding_json = create_embedding(
        client,
        user_question
    )

    question_embedding = json.loads(question_embedding_json)

    similar_chunks = search_similar_chunks(
        question_embedding,
        chunks,
        limit=5
    )

    context = ""

    for score, file_name, chunk_text in similar_chunks:

        context += f"""

Источник файла: {file_name}
Релевантность: {score:.3f}

{chunk_text}

---
"""

    history = []

    if "user_id" in st.session_state:

        history = get_ai_chat_history(
            st.session_state["user_id"]
        )

    history_text = ""

    for question, answer in history[-5:]:

        history_text += f"""

Вопрос стажёра:
{question}

Ответ AI:
{answer}

"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=f"""
Ты AI-наставник стажёра компании.

Отвечай только на основе найденных фрагментов материалов компании, учебного курса и истории общения.

Если информации нет в материалах — честно скажи:
"В материалах компании нет точной информации по этому вопросу."

История прошлых вопросов стажёра:
{history_text}

Найденные фрагменты материалов:
{context}

Учебный курс:
{json.dumps(course_data, ensure_ascii=False)}

Вопрос стажёра:
{user_question}
"""
    )

    return response.output_text