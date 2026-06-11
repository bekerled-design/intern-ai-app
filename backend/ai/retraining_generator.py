from config import OPENAI_MODEL
from ai.course_generator import _parse_json_response


def generate_retraining_course(client, weak_topics, company_material):

    weak_topics_text = "\n".join(weak_topics)

    response = client.responses.create(
        model=OPENAI_MODEL,
        text={
            "format": {
                "type": "json_object"
            }
        },
        input=f"""
Ты создаёшь дополнительный мини-курс для стажёра.

Причина: стажёр ошибся в тесте.

Слабые темы:
{weak_topics_text}

Материалы компании:
{company_material}

Верни JSON строго по структуре:

{{
  "course_title": "Дополнительное обучение",
  "modules": [
    {{
      "title": "Название мини-модуля",
      "description": "Краткое описание",
      "content": "Подробное объяснение темы"
    }}
  ],
  "test": [
    {{
      "question": "Вопрос",
      "options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
      "correct_answer": "Правильный вариант"
    }}
  ],
  "practical_task": "Практическое задание"
}}

Требования:
- Сделай 1–3 мини-модуля
- Объясни только слабые темы
- Используй материалы компании
- Не выдумывай правила компании
- Пиши простым языком
"""
    )

    return _parse_json_response(response, "курс доучивания")