# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## О проекте

AI-платформа для корпоративного обучения (интерфейс на русском). Генерирует персонализированные курсы для стажёров на основе материалов компании через OpenAI. Стек: FastAPI-бэкенд (`backend/`) + Next.js 15 фронтенд (`frontend/`). Бывшее Streamlit-приложение удалено из репозитория.

## Команды

```bash
# Бэкенд (порт 8000)
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Фронтенд (порт 3000)
cd frontend
npm install
npm run dev
```

`OPENAI_API_KEY` задаётся в `backend/.env`. Фронтенд берёт адрес API из `NEXT_PUBLIC_API_URL` (fallback — `http://localhost:8000`).

## Архитектура

### Бэкенд (`backend/`)

**`main.py`** — единственная точка входа FastAPI: все эндпоинты, схемы, CORS, auth. Auth для MVP: Bearer-токен = `user_id` строкой (`get_current_user`), JWT — отдельная будущая задача. На логине стоит in-memory rate limit (10 попыток / 5 мин).

**`config.py`** — константы: `OPENAI_MODEL`, `EMBEDDING_MODEL`, `WHISPER_MODEL`, лимит загрузки файла. Имя модели менять только здесь и по согласованию.

**`ai/`** — все взаимодействия с OpenAI (через `client.responses.create`):
- `course_generator.py` — генерация курсов. Ключевое: `generate_course_by_parts()` (по частям материала), `analyze_training_programs()` (pre-generation анализ: один или несколько курсов), `generate_course_for_program()` (курс по конкретной программе), `consolidate_modules()` (если модулей > 30 — слить до 12–25). JSON из ответов парсится через `_parse_json_response()`, который кидает `CourseGenerationError` с человекочитаемым текстом.
- `mentor_chat.py` — AI-ментор (RAG по чанкам компании).
- `weakness_analyzer.py`, `retraining_generator.py`, `recommendations.py` — анализ слабых мест и доучивание.
- `embeddings.py` — эмбеддинги, `video_transcriber.py` — Whisper.

**`database/database.py`** — обёртка над SQLite без ORM, весь SQL здесь. Схема создаётся в `create_tables()` при старте: `CREATE TABLE IF NOT EXISTS` + список safe-ALTER'ов (try/except) + seed-миграции + индексы. Отдельных миграций нет. Таблицы: `users`, `companies`, `courses`, `course_assignments`, `company_materials`, `material_chunks` (эмбеддинги для RAG), `test_results`, `course_progress`, `course_generation_jobs`, `api_usage`.

**`utils/`** — `file_loader.py` (TXT/CSV/XLSX/DOCX/PDF), `text_search.py` (чанкование), `semantic_search.py`, `usage_tracker.py` (учёт затрат OpenAI, никогда не кидает исключения), `pricing.py`.

### Job-система генерации

Генерация курса — асинхронный job: `POST /courses/generate-job` (или `/courses/generate-multi`) создаёт запись в `course_generation_jobs` и запускает работу в thread pool (`loop.run_in_executor`). Фронт поллит `GET /courses/generate-job/{id}`. Поля: `status` (pending/running/done/error), `progress_done/total`, `error` (только ошибки), `status_message` (прогресс «курс N из M»). При старте сервера `fail_stale_jobs()` помечает оборванные рестартом jobs как error.

### Company isolation и роли

Каждый пользователь принадлежит компании (`users.company_id`), роли: `owner` / `admin` / `employee`. Все запросы фильтруются по `company_id` — не ломать. Employee видит только назначенные ему курсы (`course_assignments`) и свои. Хелперы доступа в `main.py`: `_require_admin_or_owner`, `_require_company_access`, `_check_course_access`.

### Cost tracking

Каждый вызов OpenAI записывается в `api_usage` через `record_openai_usage` / `record_embedding_usage` / `record_transcription_usage` (все принимают `company_id` — передавать всегда). `/admin/usage` агрегирует по компании. Не ломать.

### RAG-пайплайн

1. Загрузка материала (`POST /materials/upload`, лимит 50 МБ) → извлечение текста (`file_loader.py`; аудио/видео — Whisper) → чанкование → эмбеддинги → `material_chunks`.
2. Ментор и генерация достают релевантные чанки через `semantic_search.py` и передают их как контекст.

### Фронтенд (`frontend/`)

Next.js 15 App Router, все страницы — клиентские компоненты в `app/(app)/*/page.tsx`. `lib/api.ts` — axios-инстанс с Bearer-токеном из localStorage и редиректом на /login при 401. `lib/auth.ts` — user в localStorage. `lib/types.ts`, `lib/utils.ts` — общие типы и утилиты. См. `frontend/AGENTS.md` перед изменениями (версия Next.js отличается от привычной).

## Ограничения (согласовано с владельцем)

- Не менять AI-модель и prompts без согласования.
- Не ломать company isolation, job-flow, cost tracking.
- Auth (JWT + bcrypt) — отложенная отдельная задача, не трогать мимоходом.
