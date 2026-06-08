import asyncio
import json
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from openai import OpenAI
from pydantic import BaseModel

from database.database import (
    create_tables,
    create_user,
    get_user,
    username_exists,
    get_user_courses,
    get_course_by_id,
    save_course,
    get_company_materials,
    get_company_materials_by_company,
    save_company_material,
    delete_company_material,
    delete_material_chunks,
    material_exists,
    save_material_chunk,
    get_material_chunks,
    save_test_result,
    get_test_results,
    save_module_progress,
    get_completed_modules,
    get_all_users,
    delete_course,
    save_weak_topic,
    get_weak_topics,
    clear_weak_topics,
    save_ai_chat_message,
    get_ai_chat_history,
    add_activity,
    get_user_activity,
    create_notification,
    get_notifications,
    mark_notification_as_read,
    create_job,
    update_job_status,
    get_job,
    get_active_job,
    get_last_done_job,
    get_user_api_usage,
    get_total_api_usage,
    get_api_usage_summary_by_operation,
    get_api_usage_summary_by_user,
    # company layer
    create_company,
    get_company,
    get_user_company,
    get_company_users,
    set_user_company,
    set_user_role,
    get_user_role,
    get_company_id_for_user,
    set_material_company,
    get_course_company_id,
    get_api_usage_summary_by_operation_for_company,
    get_total_api_usage_for_company,
    get_api_usage_summary_by_user_for_company,
    # invite code layer
    get_company_by_invite_code,
    get_company_invite_code,
    regenerate_company_invite_code,
    generate_invite_code,
)
from ai.course_generator import generate_course_by_parts, split_material_into_parts
from ai.mentor_chat import ask_ai_mentor
from ai.embeddings import create_embedding
from ai.weakness_analyzer import analyze_weaknesses
from ai.video_transcriber import transcribe_video
from ai.retraining_generator import generate_retraining_course
from ai.recommendations import generate_recommendations
from utils.text_search import split_text_into_chunks
from utils.file_loader import read_uploaded_file
from utils.usage_tracker import record_transcription_usage
from utils.media_duration import get_media_duration_minutes

# Load .env from backend dir first, then from project root as fallback
load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

app = FastAPI(title="Intern AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://intern-ai-app.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=300.0,
    max_retries=2,
)

create_tables()


# ─── Auth (простой токен = user_id строкой, для MVP) ─────────────────────────
# В проде заменить на JWT (python-jose).

security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    try:
        return int(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ─── Schemas ──────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    invite_code: Optional[str] = None


class TestResultRequest(BaseModel):
    score: int
    weak_topics: list[str] = []


class MentorRequest(BaseModel):
    question: str
    course_data: Optional[dict] = None


class ModuleProgressRequest(BaseModel):
    course_id: int
    module_index: int


class AssignCourseRequest(BaseModel):
    user_id: int
    course_id: int


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ─── Auth endpoints ───────────────────────────────────────────────────────────

def _auth_response(user_id: int, username: str):
    """Build unified auth response with company_id and role."""
    row = get_user_company(user_id)
    company_id = row[0] if row else None
    role = row[2] if row else "employee"
    # Legacy compat: map owner/admin -> "admin", employee -> "intern"
    legacy_role = "admin" if role in ("owner", "admin") else "intern"
    return {
        "token": str(user_id),
        "user_id": user_id,
        "username": username,
        "role": legacy_role,
        "company_role": role,
        "company_id": company_id,
    }


@app.post("/auth/register")
def register(body: RegisterRequest):
    # Existing user: just log them in (backward compat)
    if username_exists(body.username):
        user = get_user(body.username, body.password)
        if not user:
            raise HTTPException(status_code=401, detail="Неверный пароль")
        return _auth_response(user[0], body.username)

    invite_code = (body.invite_code or "").strip().upper()

    if invite_code:
        # Join an existing company as employee
        company_row = get_company_by_invite_code(invite_code)
        if not company_row:
            raise HTTPException(status_code=400, detail="Неверный код приглашения")
        target_company_id = company_row[0]
        user_id = create_user(body.username, body.password)
        set_user_company(user_id, target_company_id)
        set_user_role(user_id, "employee")
    else:
        # Create a new company, user becomes owner
        user_id = create_user(body.username, body.password)
        new_code = generate_invite_code()
        company_id = create_company(f"Компания {body.username}", user_id, invite_code=new_code)
        set_user_company(user_id, company_id)
        set_user_role(user_id, "owner")

    return _auth_response(user_id, body.username)


@app.post("/auth/login")
def login(body: LoginRequest):
    if not username_exists(body.username):
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user = get_user(body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Неверный пароль")
    return _auth_response(user[0], body.username)


# ─── Materials endpoints ──────────────────────────────────────────────────────

@app.get("/materials")
def list_materials(user_id: int = Depends(get_current_user)):
    materials = get_company_materials(user_id)
    return [{"file_name": m[0]} for m in materials]


@app.post("/materials/upload")
async def upload_material(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user),
):
    class _FakeUpload:
        def __init__(self, name, data):
            self.name = name
            self._data = data

        def read(self):
            return self._data

        def seek(self, pos):
            pass

    raw = await file.read()
    fake = _FakeUpload(file.filename, raw)

    name_lower = file.filename.lower()
    if name_lower.endswith((".mp4", ".mp3", ".wav", ".m4a", ".webm")):
        import tempfile, os as _os
        suffix = "." + name_lower.rsplit(".", 1)[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name
        try:
            with open(tmp_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text",
                )
            content = str(transcript)
            duration_minutes = get_media_duration_minutes(tmp_path)
            record_transcription_usage(user_id, "whisper-1", duration_minutes=duration_minutes)
        except Exception as e:
            content = f"Ошибка транскрипции: {e}"
        finally:
            if _os.path.exists(tmp_path):
                _os.remove(tmp_path)
    else:
        content = read_uploaded_file(fake)

    if not material_exists(user_id, file.filename):
        save_company_material(user_id, file.filename, content)
        company_id = get_company_id_for_user(user_id)
        if company_id:
            set_material_company(user_id, file.filename, company_id)
        chunks = split_material_into_parts(content[:500_000], chunk_size=2000, overlap=200)
        for chunk in chunks:
            try:
                emb = create_embedding(client, chunk, user_id=user_id)
                save_material_chunk(user_id, file.filename, chunk, emb)
            except Exception:
                continue

    add_activity(user_id, f"Загрузил материал: {file.filename}")
    return {"file_name": file.filename, "status": "ok"}


@app.delete("/materials/{file_name}")
def delete_material(file_name: str, user_id: int = Depends(get_current_user)):
    delete_company_material(user_id, file_name)
    delete_material_chunks(user_id, file_name)
    return {"status": "deleted"}


# ─── Course generation (job-based) ───────────────────────────────────────────

def _run_generation_job(job_id: int, user_id: int, material: str, company_id=None):
    """Runs in a thread pool. Updates job status in DB throughout."""
    try:
        update_job_status(job_id, "running")

        def progress_callback(done, total):
            if total > 0:
                update_job_status(job_id, "running", progress_done=done, progress_total=total)

        course_data = generate_course_by_parts(client, material, progress_callback,
                                               user_id=user_id, job_id=job_id)
        course_id = save_course(user_id, course_data, company_id=company_id)
        add_activity(user_id, f"Сгенерировал курс: {course_data.get('course_title', '')}")
        update_job_status(job_id, "done", course_id=course_id,
                          progress_done=0, progress_total=0)
    except Exception as e:
        update_job_status(job_id, "error", error=str(e))


@app.post("/courses/generate-job")
async def start_generation_job(user_id: int = Depends(get_current_user)):
    materials = get_company_materials(user_id)
    if not materials:
        raise HTTPException(status_code=400, detail="Нет загруженных материалов")

    active = get_active_job(user_id)
    if active:
        return {"job_id": active[0]}

    company_id = get_company_id_for_user(user_id)
    material = "".join(f"\n\nФайл: {m[0]}\n\n{m[1]}\n\n" for m in materials)
    job_id = create_job(user_id, company_id=company_id)

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _run_generation_job, job_id, user_id, material, company_id)

    return {"job_id": job_id}


@app.get("/courses/generate-job/{job_id}")
def get_generation_job(job_id: int, user_id: int = Depends(get_current_user)):
    row = get_job(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job не найден")
    _, _, status, course_id, progress_done, progress_total, error = row
    return {
        "job_id": job_id,
        "status": status,
        "course_id": course_id,
        "progress_done": progress_done,
        "progress_total": progress_total,
        "error": error,
    }


@app.get("/courses/active-job")
def get_active_generation_job(user_id: int = Depends(get_current_user)):
    row = get_active_job(user_id)
    if not row:
        # Возвращаем последний done-job чтобы фронтенд мог восстановить current_course_id
        # если страница была закрыта пока генерация шла
        row = get_last_done_job(user_id)
    if not row:
        return {"job": None}
    _, _, status, course_id, progress_done, progress_total, error = row
    return {"job": {
        "job_id": row[0],
        "status": status,
        "course_id": course_id,
        "progress_done": progress_done,
        "progress_total": progress_total,
        "error": error,
    }}


# ─── Courses CRUD ─────────────────────────────────────────────────────────────

@app.get("/courses")
def list_courses(user_id: int = Depends(get_current_user)):
    courses = get_user_courses(user_id)
    result = []
    for c in courses:
        course_id = c[0]
        content = get_course_by_id(course_id)
        total = 0
        if content:
            try:
                data = json.loads(content[0])
                total = len(data.get("modules", []))
            except Exception:
                pass
        completed = get_completed_modules(user_id, course_id)
        result.append({"id": course_id, "title": c[1], "due_date": c[2], "total_modules": total, "completed_modules": len(completed)})
    return result


@app.get("/users/{target_user_id}/courses")
def list_user_courses(target_user_id: int, user_id: int = Depends(get_current_user)):
    courses = get_user_courses(target_user_id)
    result = []
    for c in courses:
        course_id = c[0]
        content = get_course_by_id(course_id)
        total = 0
        if content:
            try:
                data = json.loads(content[0])
                total = len(data.get("modules", []))
            except Exception:
                pass
        completed = get_completed_modules(target_user_id, course_id)
        result.append({"id": course_id, "title": c[1], "due_date": c[2], "total_modules": total, "completed_modules": len(completed)})
    return result


@app.get("/courses/{course_id}")
def get_course(course_id: int, user_id: int = Depends(get_current_user)):
    row = get_course_by_id(course_id)
    if not row:
        raise HTTPException(status_code=404, detail="Курс не найден")
    # Company isolation: course must belong to the same company as the requester.
    # Courses with NULL company_id (legacy) are accessible to any authenticated user.
    course_company = get_course_company_id(course_id)
    if course_company is not None:
        requester_company = get_company_id_for_user(user_id)
        if requester_company != course_company:
            raise HTTPException(status_code=403, detail="Нет доступа к этому курсу")
    return json.loads(row[0])


@app.delete("/courses/{course_id}")
def remove_course(course_id: int, user_id: int = Depends(get_current_user)):
    delete_course(user_id, course_id)
    return {"status": "deleted"}


@app.get("/courses/{course_id}/progress")
def course_progress(course_id: int, user_id: int = Depends(get_current_user)):
    completed = get_completed_modules(user_id, course_id)
    return {"completed_modules": completed}


@app.post("/courses/{course_id}/progress")
def save_progress(
    course_id: int,
    body: ModuleProgressRequest,
    user_id: int = Depends(get_current_user),
):
    save_module_progress(user_id, course_id, body.module_index)
    add_activity(user_id, f"Завершил модуль {body.module_index} курса {course_id}")
    return {"status": "ok"}


# ─── Tests ────────────────────────────────────────────────────────────────────

@app.post("/tests/result")
def submit_test_result(body: TestResultRequest, user_id: int = Depends(get_current_user)):
    save_test_result(user_id, body.score)
    if body.weak_topics:
        for topic in body.weak_topics:
            save_weak_topic(user_id, topic)
    else:
        clear_weak_topics(user_id)
    add_activity(user_id, f"Прошёл тест. Результат: {body.score}%")
    return {"status": "ok"}


@app.get("/tests/results")
def test_results(user_id: int = Depends(get_current_user)):
    results = get_test_results(user_id)
    return {"scores": [r[0] for r in results]}


@app.get("/tests/weak-topics")
def weak_topics(user_id: int = Depends(get_current_user)):
    topics = get_weak_topics(user_id)
    return {"topics": topics}


@app.get("/tests/analysis")
def weakness_analysis(user_id: int = Depends(get_current_user)):
    topics = get_weak_topics(user_id)
    if not topics:
        return {"analysis": None}
    analysis = analyze_weaknesses(client, topics)
    return {"analysis": analysis}


# ─── Mentor ───────────────────────────────────────────────────────────────────

@app.post("/mentor/ask")
def mentor_ask(body: MentorRequest, user_id: int = Depends(get_current_user)):
    company_id = get_company_id_for_user(user_id)
    if company_id is not None:
        _mats = get_company_materials_by_company(company_id)
        company_material = "".join(f"\n\nФайл: {m[0]}\n\n{m[1]}\n\n" for m in _mats)
    else:
        company_material = ""

    answer = ask_ai_mentor(
        client,
        user_id,
        company_material,
        body.course_data or {},
        body.question,
        company_id=company_id,
    )
    save_ai_chat_message(user_id, body.question, answer)
    return {"answer": answer}


@app.get("/mentor/history")
def mentor_history(user_id: int = Depends(get_current_user)):
    history = get_ai_chat_history(user_id)
    return [{"question": h[0], "answer": h[1]} for h in history]


# ─── Dashboard / Activity ─────────────────────────────────────────────────────

@app.get("/activity")
def activity(user_id: int = Depends(get_current_user)):
    log = get_user_activity(user_id)
    return [{"action": a[0], "created_at": a[1]} for a in log]


# ─── Admin ────────────────────────────────────────────────────────────────────

def _require_company_access(user_id: int, target_user_id: int):
    """Raise 403 if target_user is not in the same company as user_id."""
    my_company = get_company_id_for_user(user_id)
    their_company = get_company_id_for_user(target_user_id)
    if my_company is not None and their_company is not None and my_company != their_company:
        raise HTTPException(status_code=403, detail="Нет доступа к пользователям другой компании")


def _require_admin_or_owner(user_id: int):
    role = get_user_role(user_id)
    if role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Требуются права администратора")


@app.get("/admin/users")
def admin_users(user_id: int = Depends(get_current_user)):
    _require_admin_or_owner(user_id)
    company_id = get_company_id_for_user(user_id)
    users = get_all_users(company_id=company_id)
    return [{"id": u[0], "username": u[1], "role": u[2]} for u in users]


@app.get("/admin/users/{target_id}/weak-topics")
def admin_user_weak_topics(target_id: int, user_id: int = Depends(get_current_user)):
    _require_admin_or_owner(user_id)
    _require_company_access(user_id, target_id)
    topics = get_weak_topics(target_id)
    return {"topics": topics}


@app.post("/admin/users/{target_id}/retraining")
def admin_generate_retraining(target_id: int, user_id: int = Depends(get_current_user)):
    _require_admin_or_owner(user_id)
    _require_company_access(user_id, target_id)
    topics = get_weak_topics(target_id)
    if not topics:
        raise HTTPException(status_code=400, detail="У пользователя нет слабых тем")
    company_id = get_company_id_for_user(user_id)
    materials = get_company_materials(target_id)
    company_material = "".join(f"\n\nФайл: {m[0]}\n\n{m[1]}\n\n" for m in materials)
    if not company_material.strip():
        materials = get_company_materials(user_id)
        company_material = "".join(f"\n\nФайл: {m[0]}\n\n{m[1]}\n\n" for m in materials)
    course_data = generate_retraining_course(client, topics, company_material)
    course_id = save_course(target_id, course_data, company_id=company_id)
    add_activity(target_id, "Назначено дополнительное обучение администратором")
    create_notification(target_id, f"Администратор назначил вам дополнительный курс: «{course_data.get('course_title', 'Доп. обучение')}»")
    return {"course_id": course_id, "course": course_data}


# ─── API Usage ───────────────────────────────────────────────────────────────

@app.get("/admin/usage")
def admin_usage(user_id: int = Depends(get_current_user)):
    _require_admin_or_owner(user_id)
    company_id = get_company_id_for_user(user_id)
    if company_id is not None:
        total_tokens, total_cost = get_total_api_usage_for_company(company_id)
        by_op = [
            {"operation": r[0], "calls": r[1], "tokens": r[2], "cost": round(r[3] or 0, 6),
             "duration_minutes": round(r[4] or 0, 4)}
            for r in get_api_usage_summary_by_operation_for_company(company_id)
        ]
        by_user = [
            {"username": r[0] or f"user_{r[1]}", "user_id": r[1], "calls": r[2],
             "tokens": r[3], "cost": round(r[4] or 0, 6)}
            for r in get_api_usage_summary_by_user_for_company(company_id)
        ]
    else:
        # Fallback for legacy users without company
        total_tokens, total_cost = get_total_api_usage()
        by_op = [
            {"operation": r[0], "calls": r[1], "tokens": r[2], "cost": round(r[3] or 0, 6),
             "duration_minutes": round(r[4] or 0, 4)}
            for r in get_api_usage_summary_by_operation()
        ]
        by_user = [
            {"username": r[0] or f"user_{r[1]}", "user_id": r[1], "calls": r[2],
             "tokens": r[3], "cost": round(r[4] or 0, 6)}
            for r in get_api_usage_summary_by_user()
        ]
    return {
        "total_tokens": total_tokens or 0,
        "total_estimated_cost_usd": round(total_cost or 0, 6),
        "by_operation": by_op,
        "by_user": by_user,
    }


@app.get("/users/{target_user_id}/usage")
def user_usage(target_user_id: int, user_id: int = Depends(get_current_user)):
    rows = get_user_api_usage(target_user_id)
    records = [
        {
            "operation_type": r[0],
            "model": r[1],
            "input_tokens": r[2],
            "output_tokens": r[3],
            "total_tokens": r[4],
            "estimated_cost_usd": r[5],
            "created_at": r[6],
        }
        for r in rows
    ]
    total_cost = sum(r["estimated_cost_usd"] for r in records)
    return {
        "user_id": target_user_id,
        "total_estimated_cost_usd": round(total_cost, 6),
        "records": records,
    }


# ─── Company endpoints ───────────────────────────────────────────────────────

class RoleUpdateRequest(BaseModel):
    role: str  # "admin" or "employee"


@app.get("/company/me")
def company_me(user_id: int = Depends(get_current_user)):
    row = get_user_company(user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Компания не найдена")
    company_id, company_name, role = row
    users = get_company_users(company_id) if company_id else []
    # Expose invite_code only to owner/admin
    invite_code = None
    if role in ("owner", "admin") and company_id:
        invite_code = get_company_invite_code(company_id)
    return {
        "company_id": company_id,
        "name": company_name,
        "role": role,
        "users_count": len(users),
        "invite_code": invite_code,
    }


@app.post("/company/invite-code/regenerate")
def regenerate_invite_code(user_id: int = Depends(get_current_user)):
    _require_admin_or_owner(user_id)
    company_id = get_company_id_for_user(user_id)
    if not company_id:
        raise HTTPException(status_code=404, detail="Компания не найдена")
    new_code = regenerate_company_invite_code(company_id)
    return {"invite_code": new_code}


@app.get("/company/users")
def company_users(user_id: int = Depends(get_current_user)):
    _require_admin_or_owner(user_id)
    company_id = get_company_id_for_user(user_id)
    if not company_id:
        return []
    users = get_company_users(company_id)
    return [{"id": u[0], "username": u[1], "role": u[2]} for u in users]


@app.patch("/company/users/{target_id}/role")
def update_user_role(target_id: int, body: RoleUpdateRequest, user_id: int = Depends(get_current_user)):
    if get_user_role(user_id) != "owner":
        raise HTTPException(status_code=403, detail="Только владелец может менять роли")
    if target_id == user_id:
        raise HTTPException(status_code=400, detail="Нельзя изменить собственную роль")
    _require_company_access(user_id, target_id)
    allowed = {"admin", "employee"}
    if body.role not in allowed:
        raise HTTPException(status_code=400, detail=f"Допустимые роли: {allowed}")
    set_user_role(target_id, body.role)
    return {"status": "ok", "user_id": target_id, "role": body.role}


# ─── Notifications ────────────────────────────────────────────────────────────

@app.get("/notifications")
def list_notifications(user_id: int = Depends(get_current_user)):
    notes = get_notifications(user_id)
    return [{"id": n[0], "message": n[1]} for n in notes]


@app.post("/notifications/{note_id}/read")
def read_notification(note_id: int, user_id: int = Depends(get_current_user)):
    mark_notification_as_read(note_id)
    return {"status": "ok"}
