import json
import re
from utils.text_search import split_text_into_chunks, search_relevant_chunks
from utils.usage_tracker import record_openai_usage


def split_material_into_parts(text, chunk_size=10000, overlap=1000):
    """Split material respecting section headings when present, otherwise by size."""
    # Detect section headings: "Часть N", "Раздел N", "Модуль N", "Тема N",
    # numbered lines like "1.", "1)", or markdown headings "#"
    # Uppercase Cyrillic range А-Я plus Ё (U+0401) which sits outside А-Я in Unicode
    _UC = r"[А-ЯЁA-Z]"
    heading_pattern = re.compile(
        r"(?m)^(?:"
        r"#{1,3}\s.{5,}"
        r"|(?:ЧАСТЬ|РАЗДЕЛ|МОДУЛЬ|ТЕМА|CHAPTER|SECTION)\s+\d+\S*"
        r"|(?:Часть|Раздел|Модуль|Тема)\s+\d+\S*"
        rf"|\d+\.\s+{_UC}[А-ЯЁA-Z\s]{{4,}}"  # "1. ОБЯЗАННОСТИ МЕНЕДЖЕРА" — all-caps heading
        r")",
    )
    matches = list(heading_pattern.finditer(text))

    # Use heading-based split only if we find at least 2 headings
    if len(matches) >= 2:
        raw_parts = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            part = text[start:end].strip()
            if not part:
                continue
            # If a single section is very large, split it further
            if len(part) > chunk_size:
                sub_parts = split_text_into_chunks(part, chunk_size=chunk_size, overlap=overlap)
                raw_parts.extend(sub_parts)
            else:
                raw_parts.append(part)

        # Merge small sections so each part is at least 1500 chars.
        # This prevents 8 × 300-char sections that each spawn 2-3 modules.
        _MIN_PART = 1500
        parts = []
        buf = ""
        for p in raw_parts:
            if buf:
                buf += "\n\n" + p
            else:
                buf = p
            if len(buf) >= _MIN_PART:
                parts.append(buf)
                buf = ""
        if buf:
            if parts:
                parts[-1] += "\n\n" + buf
            else:
                parts.append(buf)

        if parts:
            return parts

    # Fallback: character-based split
    return split_text_into_chunks(text, chunk_size=chunk_size, overlap=overlap)

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

def _max_test_questions(module_count: int) -> int:
    """Target upper bound for test questions based on module count."""
    if module_count <= 5:
        return 12
    if module_count <= 10:
        return 20
    if module_count <= 20:
        return 30
    return 40


def _trim_tests_evenly(tests: list, max_q: int) -> list:
    """Trim test list to max_q, keeping even coverage across topics."""
    if len(tests) <= max_q:
        return tests

    # Group by topic field
    from collections import defaultdict
    by_topic = defaultdict(list)
    for q in tests:
        by_topic[q.get("topic", "")].append(q)

    result = []
    topics = list(by_topic.keys())
    # Round-robin across topics until we hit the limit
    i = 0
    while len(result) < max_q:
        topic = topics[i % len(topics)]
        if by_topic[topic]:
            result.append(by_topic[topic].pop(0))
        i += 1
        # Stop if all topics exhausted
        if all(not v for v in by_topic.values()):
            break
    return result


def generate_course_tests(client, modules, user_id=None, job_id=None, company_id=None):

    module_count = len(modules)
    max_questions = _max_test_questions(module_count)
    # Ask for a few more than the max so the LLM has room to distribute;
    # post-processing will trim the excess.
    target = max_questions + 5

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

Создай тест по обучающему курсу из {module_count} модулей.

КОЛИЧЕСТВО ВОПРОСОВ:
- Создай ровно {target} вопросов — не больше, не меньше.
- Не создавай одинаковое количество вопросов для каждого модуля.
- Распределяй вопросы по важности тем: важные и сложные модули получают 2–3 вопроса, простые — 1 вопрос.
- Главная цель — проверить понимание всего курса без перегрузки пользователя.

ТРЕБОВАНИЯ К ВОПРОСАМ:
- вопросы должны проверять понимание материала, а не запоминание фраз
- не задавай слишком простые вопросы
- не используй внешние знания — только содержание модулей
- варианты ответов должны быть реалистичными
- правильный ответ должен точно совпадать с одним из вариантов
- вопросы должны покрывать все ключевые темы курса

ПОКРЫТИЕ:
- каждая ключевая тема курса должна быть проверена хотя бы одним вопросом
- вспомогательные и вводные модули можно пропустить, если тема очевидна

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
""",
    )

    if user_id is not None:
        record_openai_usage(user_id, "course_tests", "gpt-4.1-mini", response,
                            related_job_id=job_id, company_id=company_id)

    raw_text = response.output_text
    test_data = json.loads(raw_text)
    tests = test_data["test"]

    # Post-processing: enforce hard cap with even topic distribution
    tests = _trim_tests_evenly(tests, max_questions)

    return tests

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

def generate_practical_task(client, modules, user_id=None, job_id=None, company_id=None):

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

    if user_id is not None:
        record_openai_usage(user_id, "course_practical", "gpt-4.1-mini", response,
                            related_job_id=job_id, company_id=company_id)

    return response.output_text

def generate_part_modules(client, part_text, part_number, user_id=None, job_id=None, company_id=None):

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

КОЛИЧЕСТВО МОДУЛЕЙ — главное правило:
- Обычно 2–4 модуля на одну часть.
- Максимум 6 модулей, даже если тем много.
- Минимум 1 модуль, если часть маленькая или содержит одну тему.
- Объединяй близкие подтемы в один логичный модуль.
- Не создавай отдельный модуль на каждый факт, правило или пункт списка.
- Один модуль = самостоятельный учебный блок (процесс, инструмент, принцип), а не отдельный абзац.
- Если часть содержит перечень мелких правил — объедини их в один модуль "Правила и стандарты X".

ВАЖНО:
- Используй только эту часть материала.
- Не используй внешние знания.
- Не придумывай темы.
- Раскрывай каждый модуль подробно — объясняй как преподаватель, а не как конспект.
- Сохраняй конкретные названия, цифры, примеры из материала.

Каждый модуль в поле content должен содержать:
1. Введение
2. Подробное объяснение
3. Как применять на практике
4. Типичные ошибки
5. Краткий вывод

Верни JSON:

{{
    "modules": [
        {{
            "title": "Название модуля",
            "description": "Краткое описание",
            "content": "Полноценный обучающий материал"
        }}
    ]
}}

Часть материала №{part_number}:

{part_text}
"""
    )

    if user_id is not None:
        record_openai_usage(user_id, "course_modules", "gpt-4.1-mini", response,
                            related_job_id=job_id, company_id=company_id)

    data = json.loads(response.output_text)

    return data["modules"]

def generate_course_by_parts(client, file_content, progress_callback=None, user_id=None, job_id=None, company_id=None):

    char_count = len(file_content)
    word_count = len(file_content.split())
    parts = split_material_into_parts(file_content, chunk_size=10000, overlap=1000)
    total = len(parts)

    import sys
    diag = f"[DIAG] chars={char_count} words={word_count} parts={total}"
    print(diag.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8"))

    all_modules = []

    for index, part in enumerate(parts):
        print(f"[GEN] part {index + 1}/{total}")
        if progress_callback:
            progress_callback(index, total)
        part_modules = generate_part_modules(
            client,
            part,
            index + 1,
            user_id=user_id,
            job_id=job_id,
            company_id=company_id,
        )
        all_modules.extend(part_modules)

    if progress_callback:
        progress_callback(total, total)

    if char_count < 30000 and len(all_modules) > 40:
        print(f"[WARNING] too many modules ({len(all_modules)}) for material size ({char_count} chars)")

    # ── Consolidation: если модулей > 30 — объединяем ────────────────────────
    if len(all_modules) > 30:
        print(f"[CONSOLIDATE] {len(all_modules)} modules → consolidating to 12–25")
        all_modules = consolidate_modules(client, all_modules)
        print(f"[CONSOLIDATE] after: {len(all_modules)} modules")

    tests = generate_course_tests(
        client,
        all_modules,
        user_id=user_id,
        job_id=job_id,
        company_id=company_id,
    )

    practical_task = generate_practical_task(
        client,
        all_modules,
        user_id=user_id,
        job_id=job_id,
        company_id=company_id,
    )

    titles_text = "\n".join(f"- {m['title']}" for m in all_modules[:20])
    try:
        title_resp = client.responses.create(
            model="gpt-4.1-mini",
            input=f"Придумай короткое (3-7 слов) название курса по этим модулям. Верни только название, без кавычек.\n\n{titles_text}"
        )
        course_title = title_resp.output_text.strip()
    except Exception:
        course_title = all_modules[0]["title"] if all_modules else "Курс обучения"

    course_data = {
        "course_title": course_title,
        "modules": all_modules,
        "test": tests,
        "practical_task": practical_task
    }

    return course_data


# ─── Module consolidation (защита от взрыва модулей) ─────────────────────────

def consolidate_modules(client, modules: list) -> list:
    """Merge micro-modules into 12–25 solid learning blocks."""
    titles_text = "\n".join(f"{i+1}. {m['title']}" for i, m in enumerate(modules))

    response = client.responses.create(
        model="gpt-4.1-mini",
        text={"format": {"type": "json_object"}},
        input=f"""Ты — AI-методист корпоративного обучения.

Ниже список из {len(modules)} учебных модулей. Это слишком много для одного курса.

Твоя задача: объединить микро-модули в более крупные учебные блоки.

ПРАВИЛА:
- Итоговое количество модулей: от 12 до 25.
- Объединяй только тематически близкие модули.
- Не удаляй важные темы — важные разделы должны быть сохранены.
- Один модуль = самостоятельный учебный блок (процесс, инструмент, принцип).
- Не объединяй несвязанные темы ради сокращения.
- Если тема уникальна — оставь её отдельным модулем.
- Не придумывай новые темы.

Верни JSON — список групп. Каждая группа станет одним модулем:

{{
  "groups": [
    {{
      "merged_title": "Название объединённого модуля",
      "source_indices": [1, 2, 3]
    }}
  ]
}}

Список модулей (номера 1-based):

{titles_text}
"""
    )

    data = json.loads(response.output_text)
    groups = data.get("groups", [])

    merged = []
    for g in groups:
        indices = [i - 1 for i in g.get("source_indices", []) if 1 <= i <= len(modules)]
        if not indices:
            continue
        primary = modules[indices[0]]
        combined_content = "\n\n---\n\n".join(
            f"## {modules[i]['title']}\n\n{modules[i]['content']}" for i in indices
        )
        combined_desc = "; ".join(modules[i]["description"] for i in indices)
        merged.append({
            "title": g["merged_title"],
            "description": combined_desc[:300],
            "content": combined_content,
        })

    # Fallback: если что-то пошло не так — вернуть первые 25 оригиналов
    if not merged:
        return modules[:25]

    return merged


# ─── Pre-generation analysis ──────────────────────────────────────────────────

def analyze_training_programs(
    client,
    materials: list[dict],
    user_id: int = None,
    company_id: int = None,
) -> dict:
    """
    Analyse company materials and recommend how many courses to create.

    materials: list of {"file_name": str, "content": str}

    Returns:
    {
      "recommended_mode": "single_course" | "multiple_courses",
      "warning": str | None,        # non-None when single but many modules expected
      "programs": [
        {
          "course_title": str,
          "target_role": str,
          "description": str,
          "source_files": [str, ...],
          "source_topics": [str, ...],
          "reason": str,
          "estimated_modules": int
        }
      ]
    }
    """
    # Build a compact summary for each file (first 3000 chars is enough for analysis)
    files_summary = ""
    for m in materials:
        preview = m["content"][:3000].strip()
        files_summary += f"\n\n=== Файл: {m['file_name']} ===\n{preview}\n"

    response = client.responses.create(
        model="gpt-4.1-mini",
        text={"format": {"type": "json_object"}},
        input=f"""Ты — AI-методист корпоративного обучения.

Ниже загруженные материалы компании. Твоя задача: проанализировать их и определить,
нужно ли создать один курс или несколько отдельных курсов.

ПРАВИЛА РАЗДЕЛЕНИЯ:
1. Если материалы относятся к разным ролям (например, аналитики и поддержка клиентов) — создай отдельный курс для каждой роли.
2. Если один файл является справочником шаблонов или примеров — НЕ делай из каждого шаблона отдельный курс. Это справочный раздел, он входит в один курс.
3. Если материалы относятся к одной роли и одному процессу — оставь один курс.
4. Если один курс ожидаемо будет содержать более 28 модулей — рекомендуй разделение.
5. Не придумывай курсы, которых нет в материалах.
6. Минимальный осмысленный курс — не менее 4 полноценных тем.

ОЦЕНКА КОЛИЧЕСТВА МОДУЛЕЙ:
- Подсчитай, сколько самостоятельных тем можно выделить в каждой группе материалов.
- Один модуль = одна тема, процесс, инструкция или принцип.
- Справочник из 20 шаблонов — это 1–2 модуля, не 20.

Верни JSON строго в этом формате:

{{
  "recommended_mode": "single_course" | "multiple_courses",
  "warning": null | "Текст предупреждения если один курс слишком большой",
  "programs": [
    {{
      "course_title": "Название курса",
      "target_role": "Для кого этот курс (роль или аудитория)",
      "description": "Что будет изучаться в этом курсе (2-3 предложения)",
      "source_files": ["имя_файла1.txt", "имя_файла2.pdf"],
      "source_topics": ["тема 1", "тема 2", "тема 3"],
      "reason": "Почему это отдельный курс или почему объединено в один",
      "estimated_modules": 12
    }}
  ]
}}

Материалы компании:

{files_summary}
"""
    )

    result = json.loads(response.output_text)

    if user_id is not None:
        record_openai_usage(user_id, "training_program_analysis", "gpt-4.1-mini", response,
                            company_id=company_id)

    # Нормализация: убедиться что поля есть
    result.setdefault("recommended_mode", "single_course")
    result.setdefault("warning", None)
    result.setdefault("programs", [])

    return result


def generate_course_for_program(
    client,
    all_materials: list[dict],
    program: dict,
    progress_callback=None,
    user_id=None,
    job_id=None,
    course_index: int = 0,
    total_courses: int = 1,
    company_id=None,
) -> dict:
    """
    Generate a single course using only the source_files specified in program.
    Falls back to all materials if source_files don't match.
    """
    source_files = set(program.get("source_files", []))

    if source_files:
        relevant = [m for m in all_materials if m["file_name"] in source_files]
    else:
        relevant = all_materials

    if not relevant:
        relevant = all_materials

    material_text = "".join(
        f"\n\nФайл: {m['file_name']}\n\n{m['content']}\n\n" for m in relevant
    )

    def scoped_progress(done, total):
        if progress_callback:
            # Translate local part progress to overall progress
            # Each course gets equal share of overall progress slots
            base = course_index * 100
            progress_callback(base + done, total_courses * (total or 1))

    course_data = generate_course_by_parts(
        client,
        material_text,
        scoped_progress,
        user_id=user_id,
        job_id=job_id,
        company_id=company_id,
    )

    # Override title with AI-suggested title if it looks generic
    suggested_title = program.get("course_title", "").strip()
    if suggested_title and len(suggested_title) > 4:
        course_data["course_title"] = suggested_title

    return course_data