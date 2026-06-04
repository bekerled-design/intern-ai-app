import json

from ai.embeddings import create_embedding
from utils.semantic_search import search_similar_chunks
from database.database import get_material_chunks, get_ai_chat_history


def ask_ai_mentor(client, user_id, company_material, course_data, user_question):
    chunks = get_material_chunks(user_id)

    question_embedding_json = create_embedding(client, user_question)
    question_embedding = json.loads(question_embedding_json)

    similar_chunks = search_similar_chunks(
        user_question,
        question_embedding,
        chunks,
        limit=15,
    )

    context = ""
    for score, semantic_score, keyword_points, file_name, chunk_text in similar_chunks:
        context += f"""
Источник файла: {file_name}
Итоговая релевантность: {score:.3f}
Смысловая релевантность: {semantic_score:.3f}
Совпадения по словам: {keyword_points}

{chunk_text}

---
"""

    history = get_ai_chat_history(user_id)
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
Ты — AI-наставник компании.

Отвечай ТОЛЬКО на основе предоставленного контекста.

ВАЖНО:
- Не используй свои знания.
- Не придумывай информацию.
- Если ответа нет в контексте — так и скажи.
- Сначала проанализируй найденные материалы.
- Давай максимально точный ответ.
- Если найдено несколько источников — объедини информацию.
- Если в контексте есть точный ответ, обязательно используй его.
- Указывай, на каком фрагменте или документе основан ответ.

История прошлых вопросов стажёра:
{history_text}

Найденные фрагменты материалов:
{context}

Учебный курс:
{json.dumps(course_data, ensure_ascii=False)}

Вопрос стажёра:
{user_question}
""",
    )

    return response.output_text
