import asyncio
import json
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
    save_weak_topic,
    get_weak_topics,
    save_ai_chat_message,
    get_ai_chat_history,
    add_activity,
    get_user_activity,
)
from ai.course_generator import generate_course_lite, generate_course_by_parts
from ai.mentor_chat import ask_ai_mentor
from ai.embeddings import create_embedding
from ai.weakness_analyzer import analyze_weaknesses
from ai.video_transcriber import transcribe_video
from ai.retraining_generator import generate_retraining_course
from ai.recommendations import generate_recommendations
from utils.text_search import split_text_into_chunks
from utils.file_loader import read_uploaded_file

load_dotenv()

app = FastAPI(title="Intern AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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


class CourseGenerateRequest(BaseModel):
    mode: str  # "lite" | "detailed"
    material: str


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

def _role(username: str) -> str:
    return "admin" if username.lower() == "admin" else "intern"


@app.post("/auth/register")
def register(body: LoginRequest):
    if username_exists(body.username):
        user = get_user(body.username, body.password)
        if not user:
            raise HTTPException(status_code=401, detail="Неверный пароль")
        return {"token": str(user[0]), "user_id": user[0], "username": body.username, "role": _role(body.username)}
    user_id = create_user(body.username, body.password)
    return {"token": str(user_id), "user_id": user_id, "username": body.username, "role": _role(body.username)}


@app.post("/auth/login")
def login(body: LoginRequest):
    if not username_exists(body.username):
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user = get_user(body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Неверный пароль")
    user_id = user[0]
    return {"token": str(user_id), "user_id": user_id, "username": body.username, "role": _role(body.username)}


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
        except Exception as e:
            content = f"Ошибка транскрипции: {e}"
        finally:
            if _os.path.exists(tmp_path):
                _os.remove(tmp_path)
    else:
        content = read_uploaded_file(fake)

    if not material_exists(user_id, file.filename):
        save_company_material(user_id, file.filename, content)
        chunks = split_text_into_chunks(content[:500_000])
        for chunk in chunks:
            try:
                emb = create_embedding(client, chunk)
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


# ─── Course generation ────────────────────────────────────────────────────────

@app.post("/courses/generate")
def generate_course(body: CourseGenerateRequest, user_id: int = Depends(get_current_user)):
    if body.mode == "lite":
        course_data = generate_course_lite(client, body.material)
    else:
        course_data = generate_course_by_parts(client, body.material)
    course_id = save_course(user_id, course_data)
    add_activity(user_id, f"Сгенерировал курс: {course_data.get('course_title', '')}")
    return {"course_id": course_id, "course": course_data}


@app.get("/courses/generate-stream")
async def generate_course_stream(
    mode: str,
    user_id: int = Depends(get_current_user),
):
    materials = get_company_materials(user_id)
    if not materials:
        raise HTTPException(status_code=400, detail="Нет загруженных материалов")
    material = "".join(f"\n\nФайл: {m[0]}\n\n{m[1]}\n\n" for m in materials)

    async def event_stream():
        loop = asyncio.get_event_loop()
        progress_queue: asyncio.Queue = asyncio.Queue()

        def progress_callback(done, total):
            if total <= 0:
                return
            asyncio.run_coroutine_threadsafe(
                progress_queue.put({"done": done, "total": total}),
                loop,
            )

        async def run_generation():
            if mode == "lite":
                result = await loop.run_in_executor(
                    None, generate_course_lite, client, material
                )
            else:
                result = await loop.run_in_executor(
                    None, generate_course_by_parts, client, material, progress_callback
                )
            await progress_queue.put({"done": -1, "course": result})

        task = asyncio.create_task(run_generation())

        while True:
            try:
                msg = await asyncio.wait_for(progress_queue.get(), timeout=15)
            except asyncio.TimeoutError:
                if task.done():
                    if task.exception():
                        yield f"event: error\ndata: {json.dumps(str(task.exception()))}\n\n"
                    break
                # heartbeat — держим соединение живым пока GPT думает
                yield ": heartbeat\n\n"
                continue

            if "course" in msg:
                course_data = msg["course"]
                course_id = save_course(user_id, course_data)
                add_activity(user_id, f"Сгенерировал курс: {course_data.get('course_title', '')}")
                yield f"event: done\ndata: {json.dumps({'course_id': course_id, 'course': course_data}, ensure_ascii=False)}\n\n"
                break
            else:
                yield f"event: progress\ndata: {json.dumps(msg)}\n\n"

        if not task.done():
            await task

    return StreamingResponse(event_stream(), media_type="text/event-stream")


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
    return json.loads(row[0])


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
    for topic in body.weak_topics:
        save_weak_topic(user_id, topic)
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
    materials = get_company_materials(user_id)
    company_material = "".join(f"\n\nФайл: {m[0]}\n\n{m[1]}\n\n" for m in materials)

    answer = ask_ai_mentor(
        client,
        user_id,
        company_material,
        body.course_data or {},
        body.question,
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

@app.get("/admin/users")
def admin_users(user_id: int = Depends(get_current_user)):
    users = get_all_users()
    return [{"id": u[0], "username": u[1]} for u in users]


@app.get("/admin/users/{target_id}/weak-topics")
def admin_user_weak_topics(target_id: int, user_id: int = Depends(get_current_user)):
    topics = get_weak_topics(target_id)
    return {"topics": topics}


@app.post("/admin/users/{target_id}/retraining")
def admin_generate_retraining(target_id: int, user_id: int = Depends(get_current_user)):
    topics = get_weak_topics(target_id)
    if not topics:
        raise HTTPException(status_code=400, detail="У пользователя нет слабых тем")
    materials = get_company_materials(target_id)
    company_material = "".join(f"\n\nФайл: {m[0]}\n\n{m[1]}\n\n" for m in materials)
    if not company_material.strip():
        materials = get_company_materials(user_id)
        company_material = "".join(f"\n\nФайл: {m[0]}\n\n{m[1]}\n\n" for m in materials)
    course_data = generate_retraining_course(client, topics, company_material)
    course_id = save_course(target_id, course_data)
    add_activity(target_id, f"Назначено дополнительное обучение администратором")
    return {"course_id": course_id, "course": course_data}
