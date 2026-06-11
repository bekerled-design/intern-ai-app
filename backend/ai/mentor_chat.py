import json

from ai.embeddings import create_embedding
from utils.semantic_search import search_similar_chunks
from database.database import get_company_material_chunks, get_ai_chat_history
from utils.usage_tracker import record_openai_usage
from config import OPENAI_MODEL

# Hard cutoff: only skip LLM if there are literally no chunks at all or all scores
# are near zero. Rely on the prompt to handle "no information" cases.
_SIMILARITY_THRESHOLD = 0.05


def ask_ai_mentor(client, user_id, company_material, course_data, user_question, company_id=None):
    if company_id is not None:
        chunks = get_company_material_chunks(company_id)
    else:
        chunks = []

    if not chunks:
        return "В материалах компании пока нет данных для ответа."

    question_embedding_json = create_embedding(client, user_question, user_id=user_id)
    question_embedding = json.loads(question_embedding_json)

    similar_chunks = search_similar_chunks(
        user_question,
        question_embedding,
        chunks,
        limit=8,
    )

    if not similar_chunks:
        return "В загруженных материалах нет информации по этому вопросу."

    best_score, best_semantic, best_keywords, _, _ = similar_chunks[0]
    if best_semantic < _SIMILARITY_THRESHOLD and best_keywords == 0:
        return "В загруженных материалах нет точной информации по этому вопросу."

    context = ""
    for score, semantic_score, keyword_points, file_name, chunk_text in similar_chunks:
        context += f"Источник: {file_name}\n\n{chunk_text}\n\n---\n"

    history = get_ai_chat_history(user_id)
    history_text = ""
    for question, answer in history[-3:]:
        history_text += f"Вопрос: {question}\nОтвет: {answer}\n\n"

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=f"""Ты — AI-наставник компании.

Отвечай ТОЛЬКО на основе предоставленных фрагментов материалов.

КРИТИЧЕСКИ ВАЖНО:
- Отвечай только если фрагменты ПРЯМО содержат ответ.
- Если информация не найдена — скажи: "В материалах нет точной информации по этому вопросу."
- Не делай выводы из смежных тем.
- Не используй знания вне контекста.
- Указывай источник ответа.

История последних вопросов:
{history_text}
Найденные фрагменты:
{context}
Вопрос стажёра: {user_question}
""",
    )

    record_openai_usage(user_id, "mentor", OPENAI_MODEL, response, company_id=company_id)

    return response.output_text
