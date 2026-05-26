def analyze_weaknesses(client, wrong_answers):

    weak_topics = ""

    for wrong in wrong_answers:
        weak_topics += f"""
Вопрос:
{wrong['question']}

Неправильный ответ:
{wrong['user_answer']}

Правильный ответ:
{wrong['correct_answer']}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=f"""
Стажёр прошёл тест и допустил ошибки.

Проанализируй слабые места стажёра.

Верни:
1. Какие темы стажёр плохо понял
2. Что нужно повторить
3. 3 рекомендации по обучению
4. Одно дополнительное практическое задание

Ошибки стажёра:

{weak_topics}
"""
    )

    return response.output_text