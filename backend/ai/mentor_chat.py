import json

from ai.embeddings import create_embedding
from utils.semantic_search import search_similar_chunks
from database.database import get_material_chunks, get_ai_chat_history
from utils.usage_tracker import record_openai_usage

# Hard cutoff: only skip LLM if there are literally no chunks at all or all scores
# are near zero. Rely on the prompt to handle "no information" cases.
_SIMILARITY_THRESHOLD = 0.05


def ask_ai_mentor(client, user_id, company_material, course_data, user_question):
    chunks = get_material_chunks(user_id)

    question_embedding_json = create_embedding(client, user_question, user_id=user_id)
    question_embedding = json.loads(question_embedding_json)

    similar_chunks = search_similar_chunks(
        user_question,
        question_embedding,
        chunks,
        limit=5,
    )

    # Confidence gate: check if the best match is relevant enough
    if not similar_chunks:
        return "В загруженных материалах нет информации по этому вопросу."

    best_score, best_semantic, best_keywords, _, _ = similar_chunks[0]
    if best_semantic < _SIMILARITY_THRESHOLD and best_keywords == 0:
        return "В загруженных материалах нет точной информации по этому вопросу."

    context = ""
    for score, semantic_score, keyword_points, file_name, chunk_text in similar_chunks:
        context += f"""
Источник файла: {file_name}

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

КРИТИЧЕСКИ ВАЖНО:
- Отвечай только если контекст ПРЯМО содержит ответ на вопрос.
- Если контекст похож по общей теме, но не содержит точного ответа — скажи: "В материалах нет точной информации по этому вопросу."
- Не делай выводы из смежных тем.
- Не заменяй отсутствующий ответ общими рекомендациями.
- Не используй свои знания вне контекста.
- Не придумывай информацию.
- Лучше честно сказать "информации нет", чем дать нерелевантный ответ.
- Если найдено несколько источников — объедини информацию.
- Если в контексте есть точный ответ — обязательно используй его.
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

    record_openai_usage(user_id, "mentor", "gpt-4.1-mini", response)

    return response.output_text
