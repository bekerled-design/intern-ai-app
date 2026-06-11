from config import OPENAI_MODEL


def analyze_weaknesses(client, weak_topics):
    if not weak_topics:
        return None

    topics_text = "\n".join(f"- {t}" for t in weak_topics)

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=f"""Ты — AI-наставник корпоративного обучения.

Стажёр допустил ошибки в тесте по следующим темам:

{topics_text}

Дай краткий персональный анализ (3-5 предложений):
1. Что именно вызывает затруднения
2. На что обратить особое внимание при повторении
3. Конкретный совет как лучше усвоить эти темы

Пиши напрямую стажёру, коротко и по делу."""
    )

    return response.output_text
