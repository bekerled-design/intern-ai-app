import json
from utils.text_search import split_text_into_chunks, search_relevant_chunks

def generate_course(client, file_content):
    course_plan = generate_course_plan(
    client,
    file_content
)
    modules = []
    for module_plan in course_plan["modules_plan"]:

        module_content = generate_course_module(
            client,
            file_content,
            module_plan
        )
        modules.append({
            "title": module_plan["title"],
            "description": module_plan["description"],
            "content": module_content
        })
        all_tests = generate_course_tests(
        client,
        modules
    )

    course_data = {
        "course_title": course_plan["course_title"],
        "modules": modules,
        "test": all_tests,
        "practical_task": generate_practical_task(client, modules)
    }
    return course_data
    
def generate_course_lite(client, file_content):

    if len(file_content) > 250000:
        file_content = file_content[:250000]

    response = client.responses.create(
        model="gpt-4.1-mini",
        text={
            "format": {
                "type": "json_object"
            }
        },
        input=f"""
Ты — профессиональный AI-тренер корпоративного обучения.

Создай обучающий курс СТРОГО на основе предоставленного материала.

ВАЖНО:
- не придумывай темы
- не используй внешние знания
- не делай слишком краткий пересказ
- сохрани ключевые темы материала
- если материал большой, создай больше модулей
- каждый модуль должен быть понятным и полезным для новичка

Требования:
- 5–10 модулей
- 3–5 вопросов теста
- практическое задание
- ответ только в JSON

Верни JSON:

{{
    "course_title": "Название курса",
    "modules": [
        {{
            "title": "Название модуля",
            "description": "Краткое описание",
            "content": "Обучающий материал"
        }}
    ],
    "test": [
        {{
            "question": "Вопрос",
            "options": ["1", "2", "3", "4"],
            "correct_answer": "Правильный ответ",
            "module": "Название модуля"
        }}
    ],
    "practical_task": "Практическое задание"
}}

Материал:

{file_content}
"""
    )

    return json.loads(response.output_text)

def generate_course_plan(client, file_content):

    chunks = split_text_into_chunks(
        file_content,
        chunk_size=15000,
        overlap=1500
    )

    all_topics = []

    for chunk in chunks:

        chunk_topics = generate_chunk_plan(
            client,
            chunk
        )

        all_topics.extend(chunk_topics)

    response = client.responses.create(
        model="gpt-4.1-mini",
        text={
            "format": {
                "type": "json_object"
            }
        },
        input=f"""
Ты — AI-методист корпоративного обучения.

Ниже список тем, найденных во всех частях материала.

Твоя задача:
собрать из них единый логичный план курса.

Важно:
- объедини дублирующиеся темы
- сохрани все важные темы
- не выбрасывай темы без причины
- не добавляй темы, которых нет в списке
- расположи модули в логичном порядке
- каждая самостоятельная тема должна стать отдельным модулем

КОЛИЧЕСТВО МОДУЛЕЙ:

- Проанализируй весь материал.
- Выдели ВСЕ отдельные темы.
- Создай отдельный модуль для каждой темы.
- Не объединяй разные темы в один модуль.
- Если материал содержит 20 тем — создай 20 модулей.
- Если материал содержит 30 тем — создай 30 модулей.
- Не ограничивай количество модулей.
- Главная цель — покрыть максимальный объём материала.

ПРОВЕРКА ПОЛНОТЫ:

Перед возвратом ответа проверь:

1. Все ли темы из документа попали в план курса.
2. Не пропущены ли разделы документа.
3. Не потеряны ли примеры.
4. Не потеряны ли инструкции.
5. Не потеряны ли процедуры.
6. Не потеряны ли регламенты.

Если что-либо пропущено — добавь дополнительные модули.

Верни JSON:

{{
    "course_title": "Название курса",
    "modules_plan": [
        {{
            "title": "Название модуля",
            "description": "Что будет изучаться в модуле",
            "source_topic": "Какая тема легла в основу модуля"
        }}
    ]
}}

Найденные темы:

{json.dumps(all_topics, ensure_ascii=False)}
"""
    )

    raw_text = response.output_text
    course_plan = json.loads(raw_text)

    return course_plan

def get_module_context(file_content, module_plan):

    chunks = split_text_into_chunks(
        file_content,
        chunk_size=3000,
        overlap=500
    )

    search_query = (
        module_plan["title"]
        + " "
        + module_plan["description"]
        + " "
        + module_plan.get("source_topic", "")
    )

    relevant_chunks = search_relevant_chunks(
        search_query,
        chunks,
        limit=15
    )
    if not relevant_chunks:
        relevant_chunks = chunks[:5]

        return "\n\n---\n\n".join(relevant_chunks)
    context = "\n\n---\n\n".join(relevant_chunks)

    return context[:50000]

def generate_chunk_plan(client, chunk):

    response = client.responses.create(
        model="gpt-4.1-mini",
        text={
            "format": {
                "type": "json_object"
            }
        },
        input=f"""
Ты — AI-методист.

Проанализируй фрагмент материала и выдели из него важные темы для обучения.

Важно:
- не пиши модули полностью
- не создавай тесты
- не придумывай темы
- используй только данный фрагмент
- каждая отдельная тема должна быть отдельным пунктом

Верни JSON:

{{
    "topics": [
        {{
            "title": "Название темы",
            "description": "Что нужно изучить по этой теме",
            "source_topic": "Краткое описание исходной темы"
        }}
    ]
}}

Фрагмент материала:

{chunk}
"""
    )

    raw_text = response.output_text
    data = json.loads(raw_text)

    return data["topics"]

def generate_course_module(client, file_content, module_plan):
    
    module_context = get_module_context(
        file_content,
        module_plan
    )
    
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=f"""
Ты — профессиональный AI-тренер корпоративного обучения.

Создай подробный обучающий модуль.

ВАЖНО:

- Используй только информацию из предоставленного материала
- Не придумывай новые темы
- Не используй внешние знания
- Объясняй как новичку
- Не сокращай информацию
- Раскрывай тему максимально подробно

Название модуля:

{module_plan["title"]}

Описание модуля:

{module_plan["description"]}

Материал компании:

{module_context}

ВАЖНО:

Если в контексте недостаточно информации для полного раскрытия темы,
используй все найденные фрагменты максимально подробно.

Не придумывай информацию, отсутствующую в контексте.

Модуль должен содержать:

1. Что это такое
2. Зачем это нужно
3. Как это работает
4. Как применять на практике
5. Типичные ошибки
6. Практические примеры
7. Контрольные вопросы
8. Краткое закрепление материала

Верни только текст обучающего модуля.
"""
    )

    return response.output_text

def generate_course_tests(client, modules):

    modules_text = ""

    for module in modules:
        modules_text += f"""

Модуль: {module["title"]}

Описание:
{module["description"]}

Содержание:
{module["content"]}

---
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        text={
            "format": {
                "type": "json_object"
            }
        },
        input=f"""
Ты — AI-методист корпоративного обучения.

Создай тест по обучающему курсу.

ВАЖНО:
- вопросы должны проверять понимание материала
- не задавай слишком простые вопросы
- не используй внешние знания
- используй только содержание модулей
- варианты ответов должны быть реалистичными
- правильный ответ должен точно совпадать с одним из вариантов

Требования:
- минимум 5 вопросов на каждый модуль
- вопросы должны покрывать все модули курса
- вопросы должны проверять не запоминание фраз, а понимание

Верни JSON строго по структуре:

{{
    "test": [
       {{
            "question": "Вопрос",
            "options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
            "correct_answer": "Вариант 1",
            "topic": "Название темы или модуля"
        }}
    ]
}}

Курс:

{modules_text}
"""
    )

    raw_text = response.output_text
    test_data = json.loads(raw_text)

    return test_data["test"]

def generate_module_tests(client, module):

    response = client.responses.create(
        model="gpt-4.1-mini",
        text={
            "format": {
                "type": "json_object"
            }
        },
        input=f"""
Создай тест по модулю обучения.

ВАЖНО:

- Используй только информацию из модуля
- Не используй внешние знания
- Создай минимум 5 вопросов
- Проверяй понимание материала
- Не задавай слишком простые вопросы

Верни JSON:

{{
    "test": [
        {{
            "question": "Вопрос",
            "options": ["1","2","3","4"],
            "correct_answer": "1"
        }}
    ]
}}

Модуль:

Название:
{module["title"]}

Описание:
{module["description"]}

Содержание:
{module["content"]}
"""
    )

    raw_text = response.output_text
    data = json.loads(raw_text)

    return data["test"]

def generate_practical_task(client, modules):

    # Для практического задания достаточно заголовков и описаний модулей —
    # полный content слать не нужно (задание про применение знаний, а не пересказ).
    # Это убирает дублирующую отправку всего текста курса в API и экономит токены.
    modules_text = ""

    for module in modules:
        modules_text += f"""

Модуль: {module["title"]}

Описание:
{module["description"]}

---
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=f"""
Ты — AI-методист корпоративного обучения.

Создай одно подробное практическое задание по курсу.

ВАЖНО:
- используй только содержание модулей
- не используй внешние знания
- задание должно быть приближено к реальной работе
- задание должно проверять применение знаний, а не пересказ
- задание должно быть понятным для новичка

Структура задания:
1. Ситуация
2. Что нужно сделать
3. Требования к результату
4. Критерии успешного выполнения
5. Типичные ошибки, которых нужно избежать

Курс:

{modules_text}

Верни только текст практического задания.
"""
    )

    return response.output_text

def generate_part_modules(client, part_text, part_number):

    response = client.responses.create(
        model="gpt-4.1-mini",
        text={
            "format": {
                "type": "json_object"
            }
        },
        input=f"""
Ты — AI-тренер корпоративного обучения.

Создай обучающие модули только по этой части материала.

ВАЖНО:
- используй только эту часть материала
- не используй внешние знания
- не придумывай темы
- не делай краткий пересказ
- раскрывай темы подробно
- не создавай больше 4 модулей по одной части
- если тем мало — создай 1-2 модуля
- каждый модуль должен быть полноценным уроком, а не кратким описанием
- каждый модуль должен содержать несколько подробных абзацев
- не ограничивайся списком тезисов
- объясняй материал как преподаватель
- раскрывай причинно-следственные связи
- добавляй пошаговые инструкции, если они есть в материале
- добавляй практические примеры, если они следуют из материала
- сохраняй конкретные названия сервисов, инструментов и методик из материала
- если в материале есть цифры, примеры, кейсы или последовательности действий — обязательно включай их в урок

Каждый модуль в поле content должен иметь структуру:

1. Введение
2. Подробное объяснение темы
3. Как применять на практике
4. Пример из материала или практическая ситуация
5. Типичные ошибки
6. Краткий вывод

Не пиши короткий конспект. Пиши как полноценный урок для новичка.

Минимальный размер content:
- не менее 800 слов для важной темы
- не менее 500 слов для небольшой темы

Если информации достаточно, пиши максимально подробно.

Верни JSON:

{{
    "modules": [
        {{
            "title": "Название модуля",
            "description": "Краткое описание",
            "content": "Полноценный обучающий материал со структурой: введение, подробное объяснение, пошаговая инструкция, примеры, типичные ошибки, вывод"
        }}
    ]
}}

Часть материала №{part_number}:

{part_text}
"""
    )

    data = json.loads(response.output_text)

    return data["modules"]

def generate_course_by_parts(client, file_content, progress_callback=None):

    parts = split_text_into_chunks(
        file_content,
        chunk_size=20000,
        overlap=1500
    )
    total = len(parts)
    print(f"Всего частей: {total}")
    all_modules = []

    for index, part in enumerate(parts):
        print(f"Обрабатываю часть {index + 1} из {total}")
        if progress_callback:
            progress_callback(index, total)
        part_modules = generate_part_modules(
            client,
            part,
            index + 1
        )
        all_modules.extend(part_modules)

    if progress_callback:
        progress_callback(total, total)

    tests = generate_course_tests(
        client,
        all_modules
    )

    practical_task = generate_practical_task(
        client,
        all_modules
    )

    course_data = {
        "course_title": "Подробный курс по материалам",
        "modules": all_modules,
        "test": tests,
        "practical_task": practical_task
    }

    return course_data