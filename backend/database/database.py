import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "intern_ai.db")


def connect_db():
    connection = sqlite3.connect(DB_PATH)
    return connection


def create_tables():
    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    owner_user_id INTEGER,
    created_at TEXT
)
""")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password_hash TEXT,
    company_id INTEGER,
    role TEXT DEFAULT 'employee'
)
""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        course_title TEXT,
        content TEXT,
        due_date TEXT           
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS test_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        score INTEGER
    )
    """)
    cursor.execute("""
CREATE TABLE IF NOT EXISTS company_materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    file_name TEXT,
    content TEXT
)
""")
    cursor.execute("""
CREATE TABLE IF NOT EXISTS material_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    file_name TEXT,
    chunk_text TEXT,
    embedding TEXT
)
""")
    cursor.execute("""
CREATE TABLE IF NOT EXISTS course_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    course_id INTEGER,
    module_index INTEGER
)
""")
    # Idempotent unique index — protects against duplicate progress rows.
    # Works on existing DBs without a migration.
    cursor.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS uq_course_progress
    ON course_progress (user_id, course_id, module_index)
""")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS weak_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    topic TEXT
)
""")
    
    cursor.execute("""
CREATE TABLE IF NOT EXISTS ai_chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    question TEXT,
    answer TEXT
)
""")
    cursor.execute("""
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    message TEXT,
    is_read INTEGER DEFAULT 0
)
""")
    cursor.execute("""
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT,
    created_at TEXT
)
""")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS course_generation_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    status TEXT DEFAULT 'pending',
    course_id INTEGER,
    progress_done INTEGER DEFAULT 0,
    progress_total INTEGER DEFAULT 0,
    error TEXT,
    created_at TEXT
)
""")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS api_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    operation_type TEXT,
    model TEXT,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    estimated_cost_usd REAL DEFAULT 0,
    duration_minutes REAL DEFAULT 0,
    related_job_id INTEGER,
    related_course_id INTEGER,
    created_at TEXT
)
""")
    # ── Safe migrations for existing databases (no-op if column already exists) ──
    _safe_alters = [
        # duration_minutes was added in a prior migration
        "ALTER TABLE api_usage ADD COLUMN duration_minutes REAL DEFAULT 0",
        # company / role layer
        "ALTER TABLE users ADD COLUMN company_id INTEGER",
        "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'employee'",
        "ALTER TABLE company_materials ADD COLUMN company_id INTEGER",
        "ALTER TABLE material_chunks ADD COLUMN company_id INTEGER",
        "ALTER TABLE courses ADD COLUMN company_id INTEGER",
        "ALTER TABLE course_generation_jobs ADD COLUMN company_id INTEGER",
        "ALTER TABLE api_usage ADD COLUMN company_id INTEGER",
        # invite code layer
        "ALTER TABLE companies ADD COLUMN invite_code TEXT",
        # прогресс-сообщение job'а (раньше писалось в error — теперь отдельно)
        "ALTER TABLE course_generation_jobs ADD COLUMN status_message TEXT",
    ]
    for stmt in _safe_alters:
        try:
            cursor.execute(stmt)
        except Exception:
            pass

    connection.commit()

    # ── Seed: migrate existing users to a Default Company if needed ──────────
    cursor.execute("SELECT id FROM users WHERE company_id IS NULL LIMIT 1")
    if cursor.fetchone():
        # Create (or reuse) the default company
        cursor.execute("SELECT id FROM companies WHERE name = 'Default Company' LIMIT 1")
        row = cursor.fetchone()
        if row:
            default_company_id = row[0]
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO companies (name, owner_user_id, created_at) VALUES (?, ?, ?)",
                ("Default Company", None, now),
            )
            default_company_id = cursor.lastrowid

        # Assign all unassigned users to Default Company as employee
        cursor.execute(
            "UPDATE users SET company_id = ?, role = 'employee' WHERE company_id IS NULL",
            (default_company_id,),
        )
        # Make the first user the owner
        cursor.execute("SELECT id FROM users ORDER BY id ASC LIMIT 1")
        first_user = cursor.fetchone()
        if first_user:
            cursor.execute(
                "UPDATE users SET role = 'owner' WHERE id = ?",
                (first_user[0],),
            )
            cursor.execute(
                "UPDATE companies SET owner_user_id = ? WHERE id = ?",
                (first_user[0], default_company_id),
            )
        connection.commit()

    # ── Seed: migrate courses with company_id = NULL to their owner's company ──
    cursor.execute("SELECT id, user_id FROM courses WHERE company_id IS NULL")
    null_courses = cursor.fetchall()
    if null_courses:
        for course_id, course_user_id in null_courses:
            if course_user_id is not None:
                cursor.execute("SELECT company_id FROM users WHERE id = ?", (course_user_id,))
                u_row = cursor.fetchone()
                owner_company = u_row[0] if u_row else None
            else:
                owner_company = None
            if owner_company is None:
                # Fallback to Default Company
                cursor.execute("SELECT id FROM companies WHERE name = 'Default Company' LIMIT 1")
                dc = cursor.fetchone()
                owner_company = dc[0] if dc else None
            if owner_company is not None:
                cursor.execute(
                    "UPDATE courses SET company_id = ? WHERE id = ?",
                    (owner_company, course_id),
                )
        connection.commit()

    # ── Seed: migrate material_chunks with company_id = NULL ──────────────────
    cursor.execute("SELECT id, user_id FROM material_chunks WHERE company_id IS NULL")
    null_chunks = cursor.fetchall()
    if null_chunks:
        for chunk_id, chunk_user_id in null_chunks:
            if chunk_user_id is not None:
                cursor.execute("SELECT company_id FROM users WHERE id = ?", (chunk_user_id,))
                u_row = cursor.fetchone()
                chunk_company = u_row[0] if u_row else None
            else:
                chunk_company = None
            if chunk_company is not None:
                cursor.execute(
                    "UPDATE material_chunks SET company_id = ? WHERE id = ?",
                    (chunk_company, chunk_id),
                )
        connection.commit()

    # ── Seed: migrate company_materials with company_id = NULL ────────────────
    cursor.execute("SELECT id, user_id FROM company_materials WHERE company_id IS NULL")
    null_mats = cursor.fetchall()
    if null_mats:
        for mat_id, mat_user_id in null_mats:
            if mat_user_id is not None:
                cursor.execute("SELECT company_id FROM users WHERE id = ?", (mat_user_id,))
                u_row = cursor.fetchone()
                mat_company = u_row[0] if u_row else None
            else:
                mat_company = None
            if mat_company is not None:
                cursor.execute(
                    "UPDATE company_materials SET company_id = ? WHERE id = ?",
                    (mat_company, mat_id),
                )
        connection.commit()

    # ── Seed: generate invite_code for companies that don't have one ──────────
    cursor.execute("SELECT id FROM companies WHERE invite_code IS NULL")
    companies_without_code = cursor.fetchall()
    for (cid,) in companies_without_code:
        code = _generate_invite_code_value()
        # Ensure uniqueness in the unlikely collision case
        while True:
            cursor.execute("SELECT id FROM companies WHERE invite_code = ?", (code,))
            if not cursor.fetchone():
                break
            code = _generate_invite_code_value()
        cursor.execute("UPDATE companies SET invite_code = ? WHERE id = ?", (code, cid))
    if companies_without_code:
        connection.commit()

    # ── course_assignments table ──────────────────────────────────────────────
    cursor.execute("""
CREATE TABLE IF NOT EXISTS course_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    company_id INTEGER NOT NULL,
    assigned_by_user_id INTEGER,
    created_at TEXT,
    UNIQUE(course_id, user_id)
)
""")
    connection.commit()

    # ── Seed: backfill assignments for existing courses (creator only) ────────
    cursor.execute("""
        SELECT c.id, c.user_id, c.company_id
        FROM courses c
        WHERE c.user_id IS NOT NULL
          AND c.company_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM course_assignments ca
              WHERE ca.course_id = c.id AND ca.user_id = c.user_id
          )
    """)
    missing = cursor.fetchall()
    seeded = 0
    skipped = 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for (cid, uid, cmp_id) in missing:
        if not uid or not cmp_id:
            skipped += 1
            print(f"[seed assignments] skip course {cid}: user_id={uid} company_id={cmp_id}")
            continue
        cursor.execute(
            """INSERT OR IGNORE INTO course_assignments
               (course_id, user_id, company_id, assigned_by_user_id, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (cid, uid, cmp_id, uid, now),
        )
        seeded += 1
    if seeded or skipped:
        connection.commit()
        print(f"[seed assignments] processed={len(missing)} seeded={seeded} skipped={skipped}")

    # ── Индексы на часто фильтруемые поля ─────────────────────────────────────
    _indexes = [
        "CREATE INDEX IF NOT EXISTS idx_courses_user ON courses(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_courses_company ON courses(company_id)",
        "CREATE INDEX IF NOT EXISTS idx_assignments_user ON course_assignments(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_chunks_company ON material_chunks(company_id)",
        "CREATE INDEX IF NOT EXISTS idx_api_usage_company ON api_usage(company_id)",
        "CREATE INDEX IF NOT EXISTS idx_test_results_user ON test_results(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_jobs_user_status ON course_generation_jobs(user_id, status)",
    ]
    for stmt in _indexes:
        cursor.execute(stmt)
    connection.commit()

    connection.close()


def fail_stale_jobs():
    """Помечает зависшие pending/running jobs как error (вызывается при старте сервера)."""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
    UPDATE course_generation_jobs
    SET status = 'error',
        error = 'Сервер был перезапущен во время генерации. Запустите генерацию заново.',
        status_message = NULL
    WHERE status IN ('pending', 'running')
    """)
    failed = cursor.rowcount
    connection.commit()
    connection.close()
    if failed:
        print(f"[startup] помечено зависших jobs: {failed}")
    return failed

def save_test_result(user_id, score):

    connection = connect_db()

    cursor = connection.cursor()

    cursor.execute("""
    INSERT INTO test_results (user_id, score)
    VALUES (?, ?)
    """, (user_id, score))

    connection.commit()

    connection.close()

def get_test_results(user_id):

    connection = connect_db()

    cursor = connection.cursor()

    cursor.execute("""
    SELECT score FROM test_results
    WHERE user_id = ?
    """, (user_id,))

    results = cursor.fetchall()

    connection.close()

    return results    

def create_user(username, password):

    connection = connect_db()
    cursor = connection.cursor()

    password_hash = hash_password(password)

    cursor.execute("""
    INSERT INTO users (username, password_hash)
    VALUES (?, ?)
    """, (username, password_hash))

    connection.commit()

    user_id = cursor.lastrowid

    connection.close()

    return user_id

def username_exists(username):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    connection.close()
    return result is not None

def get_user(username, password):

    connection = connect_db()
    cursor = connection.cursor()

    password_hash = hash_password(password)

    cursor.execute("""
    SELECT id FROM users
    WHERE username = ? AND password_hash = ?
    """, (username, password_hash))

    user = cursor.fetchone()

    connection.close()

    return user



def save_course(user_id, course_data, due_date=None, company_id=None):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    INSERT INTO courses (
        user_id,
        course_title,
        content,
        due_date,
        company_id
    )
    VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        course_data["course_title"],
        json.dumps(course_data, ensure_ascii=False),
        due_date,
        company_id,
    ))

    connection.commit()

    course_id = cursor.lastrowid

    connection.close()

    return course_id

def delete_course(user_id, course_id):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    DELETE FROM courses
    WHERE id = ? AND user_id = ?
    """, (course_id, user_id))

    cursor.execute("""
    DELETE FROM course_progress
    WHERE course_id = ?
    """, (course_id,))

    connection.commit()
    connection.close()

def get_user_courses(user_id):

    connection = connect_db()

    cursor = connection.cursor()

    cursor.execute("""
    SELECT id, course_title, due_date
    FROM courses
    WHERE user_id = ?
    """, (user_id,))

    courses = cursor.fetchall()

    connection.close()

    return courses

def get_course_company_id(course_id: int):
    """Return company_id of a course, or None."""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT company_id FROM courses WHERE id = ?", (course_id,))
    row = cursor.fetchone()
    connection.close()
    return row[0] if row else None


def get_course_by_id(course_id):

    connection = connect_db()

    cursor = connection.cursor()

    cursor.execute("""
    SELECT content
    FROM courses
    WHERE id = ?
    """, (course_id,))

    course = cursor.fetchone()

    connection.close()

    return course

def save_company_material(user_id, file_name, content):
    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    INSERT INTO company_materials (user_id, file_name, content)
    VALUES (?, ?, ?)
    """, (user_id, file_name, content))

    connection.commit()
    connection.close()


def get_company_materials(user_id):
    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    SELECT file_name, content
    FROM company_materials
    WHERE user_id = ?
    """, (user_id,))

    materials = cursor.fetchall()

    connection.close()

    return materials


def get_company_materials_by_company(company_id: int):
    """Return all materials for a company (company-wide scope)."""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
    SELECT file_name, content
    FROM company_materials
    WHERE company_id = ?
    """, (company_id,))
    materials = cursor.fetchall()
    connection.close()
    return materials

def material_exists(user_id, file_name):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    SELECT id
    FROM company_materials
    WHERE user_id = ? AND file_name = ?
    """, (user_id, file_name))

    result = cursor.fetchone()

    connection.close()

    return result is not None

def delete_company_material(user_id, file_name):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    DELETE FROM company_materials
    WHERE user_id = ? AND file_name = ?
    """, (user_id, file_name))

    connection.commit()
    connection.close()

def save_material_chunk(user_id, file_name, chunk_text, embedding, company_id=None):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    INSERT INTO material_chunks (
        user_id,
        file_name,
        chunk_text,
        embedding,
        company_id
    )
    VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        file_name,
        chunk_text,
        embedding,
        company_id,
    ))

    connection.commit()
    connection.close()


def set_material_company(user_id: int, file_name: str, company_id: int):
    """Back-fill company_id on material and its chunks after upload."""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute(
        "UPDATE company_materials SET company_id = ? WHERE user_id = ? AND file_name = ?",
        (company_id, user_id, file_name),
    )
    cursor.execute(
        "UPDATE material_chunks SET company_id = ? WHERE user_id = ? AND file_name = ?",
        (company_id, user_id, file_name),
    )
    connection.commit()
    connection.close()

def get_material_chunks(user_id):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    SELECT file_name, chunk_text, embedding
    FROM material_chunks
    WHERE user_id = ?
    """, (user_id,))

    chunks = cursor.fetchall()

    connection.close()

    return chunks


def get_company_material_chunks(company_id: int):
    """Return all chunks for a company (company-wide RAG)."""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
    SELECT file_name, chunk_text, embedding
    FROM material_chunks
    WHERE company_id = ?
    """, (company_id,))
    chunks = cursor.fetchall()
    connection.close()
    return chunks


def delete_material_chunks(user_id, file_name):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    DELETE FROM material_chunks
    WHERE user_id = ? AND file_name = ?
    """, (user_id, file_name))

    connection.commit()
    connection.close()
def save_module_progress(
    user_id,
    course_id,
    module_index
):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO course_progress (
        user_id,
        course_id,
        module_index
    )
    VALUES (?, ?, ?)
    """, (
        user_id,
        course_id,
        module_index
    ))

    connection.commit()
    connection.close()


def get_completed_modules(
    user_id,
    course_id
):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    SELECT DISTINCT module_index
    FROM course_progress
    WHERE user_id = ?
    AND course_id = ?
    """, (
        user_id,
        course_id
    ))

    results = cursor.fetchall()

    connection.close()

    return [result[0] for result in results]

def get_all_users(company_id=None):
    connection = connect_db()
    cursor = connection.cursor()
    if company_id is not None:
        cursor.execute("SELECT id, username, role FROM users WHERE company_id = ? ORDER BY id ASC", (company_id,))
    else:
        cursor.execute("SELECT id, username, role FROM users ORDER BY id ASC")
    users = cursor.fetchall()
    connection.close()
    return users

def save_weak_topic(user_id, topic):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    SELECT id FROM weak_topics WHERE user_id = ? AND topic = ?
    """, (user_id, topic))
    if not cursor.fetchone():
        cursor.execute("""
        INSERT INTO weak_topics (user_id, topic) VALUES (?, ?)
        """, (user_id, topic))
        connection.commit()
    connection.close()

def get_weak_topics(user_id):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    SELECT topic
    FROM weak_topics
    WHERE user_id = ?
    """, (user_id,))

    results = cursor.fetchall()

    connection.close()

    return [result[0] for result in results]

def clear_weak_topics(user_id):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    DELETE FROM weak_topics
    WHERE user_id = ?
    """, (user_id,))

    connection.commit()
    connection.close()

def save_ai_chat_message(user_id, question, answer):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    INSERT INTO ai_chat_history (
        user_id,
        question,
        answer
    )
    VALUES (?, ?, ?)
    """, (
        user_id,
        question,
        answer
    ))

    connection.commit()
    connection.close()


def get_ai_chat_history(user_id):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    SELECT question, answer
    FROM ai_chat_history
    WHERE user_id = ?
    """, (user_id,))

    history = cursor.fetchall()

    connection.close()

    return history
def create_notification(user_id, message):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    INSERT INTO notifications (
        user_id,
        message
    )
    VALUES (?, ?)
    """, (
        user_id,
        message
    ))

    connection.commit()
    connection.close()


def get_notifications(user_id):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    SELECT id, message, is_read
    FROM notifications
    WHERE user_id = ?
    AND is_read = 0
    ORDER BY id DESC
    """, (user_id,))

    notifications = cursor.fetchall()

    connection.close()

    return notifications

def get_overdue_courses(user_id, today):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    SELECT course_title, due_date
    FROM courses
    WHERE user_id = ?
    AND due_date IS NOT NULL
    AND due_date < ?
    """, (user_id, today))

    courses = cursor.fetchall()

    connection.close()

    return courses

def mark_notification_as_read(notification_id):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    UPDATE notifications
    SET is_read = 1
    WHERE id = ?
    """, (notification_id,))

    connection.commit()
    connection.close()


def add_activity(user_id, action):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    INSERT INTO activity_log (
        user_id,
        action,
        created_at
    )
    VALUES (?, ?, ?)
    """, (
        user_id,
        action,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))

    connection.commit()
    connection.close()


def get_user_activity(user_id):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    SELECT action, created_at
    FROM activity_log
    WHERE user_id = ?
    ORDER BY id DESC
    LIMIT 10
    """, (user_id,))

    activity = cursor.fetchall()

    connection.close()

    return activity

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ─── Course generation jobs ───────────────────────────────────────────────────

def create_job(user_id, company_id=None):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
    INSERT INTO course_generation_jobs (user_id, status, company_id, created_at)
    VALUES (?, 'pending', ?, ?)
    """, (user_id, company_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    connection.commit()
    job_id = cursor.lastrowid
    connection.close()
    return job_id


def update_job_status(job_id, status, course_id=None, error=None, progress_done=None, progress_total=None, status_message=None):
    connection = connect_db()
    cursor = connection.cursor()
    fields = ["status = ?"]
    values = [status]
    if course_id is not None:
        fields.append("course_id = ?")
        values.append(course_id)
    if error is not None:
        fields.append("error = ?")
        values.append(error)
    if status_message is not None:
        fields.append("status_message = ?")
        values.append(status_message)
    if status == "done":
        # очищаем прогресс-сообщение и ошибку завершённого job'а
        fields.append("status_message = NULL")
        fields.append("error = NULL")
    if progress_done is not None:
        fields.append("progress_done = ?")
        values.append(progress_done)
    if progress_total is not None:
        fields.append("progress_total = ?")
        values.append(progress_total)
    values.append(job_id)
    cursor.execute(f"UPDATE course_generation_jobs SET {', '.join(fields)} WHERE id = ?", values)
    connection.commit()
    connection.close()


def get_job(job_id):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
    SELECT id, user_id, status, course_id, progress_done, progress_total, error, status_message
    FROM course_generation_jobs WHERE id = ?
    """, (job_id,))
    row = cursor.fetchone()
    connection.close()
    return row


def get_active_job(user_id):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
    SELECT id, user_id, status, course_id, progress_done, progress_total, error, status_message
    FROM course_generation_jobs
    WHERE user_id = ? AND status IN ('pending', 'running')
    ORDER BY id DESC LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()
    connection.close()
    return row


def get_last_done_job(user_id):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
    SELECT id, user_id, status, course_id, progress_done, progress_total, error, status_message
    FROM course_generation_jobs
    WHERE user_id = ? AND status = 'done' AND course_id IS NOT NULL
    ORDER BY id DESC LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()
    connection.close()
    return row


# ─── API Usage tracking ───────────────────────────────────────────────────────

def save_api_usage(user_id, operation_type, model, input_tokens, output_tokens,
                   total_tokens, estimated_cost_usd, duration_minutes=0.0,
                   related_job_id=None, related_course_id=None, company_id=None):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
    INSERT INTO api_usage (user_id, operation_type, model, input_tokens, output_tokens,
        total_tokens, estimated_cost_usd, duration_minutes, related_job_id, related_course_id, created_at, company_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, operation_type, model, input_tokens, output_tokens,
          total_tokens, estimated_cost_usd, duration_minutes or 0.0,
          related_job_id, related_course_id,
          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
          company_id))
    connection.commit()
    connection.close()


def get_user_api_usage(user_id):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
    SELECT operation_type, model, input_tokens, output_tokens, total_tokens,
           estimated_cost_usd, created_at
    FROM api_usage WHERE user_id = ? ORDER BY id DESC
    """, (user_id,))
    rows = cursor.fetchall()
    connection.close()
    return rows


def get_total_api_usage():
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
    SELECT SUM(total_tokens), SUM(estimated_cost_usd) FROM api_usage
    """)
    row = cursor.fetchone()
    connection.close()
    return row


def get_api_usage_summary_by_operation():
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
    SELECT operation_type, COUNT(*) as calls, SUM(total_tokens) as tokens,
           SUM(estimated_cost_usd) as cost, SUM(duration_minutes) as total_minutes
    FROM api_usage GROUP BY operation_type ORDER BY cost DESC
    """)
    rows = cursor.fetchall()
    connection.close()
    return rows


def get_api_usage_summary_by_user():
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
    SELECT u.username, a.user_id, COUNT(*) as calls,
           SUM(a.total_tokens) as tokens, SUM(a.estimated_cost_usd) as cost
    FROM api_usage a
    LEFT JOIN users u ON u.id = a.user_id
    GROUP BY a.user_id ORDER BY cost DESC
    """)
    rows = cursor.fetchall()
    connection.close()
    return rows


# ─── Company helpers ──────────────────────────────────────────────────────────

def create_company(name: str, owner_user_id: int, invite_code: str = None) -> int:
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO companies (name, owner_user_id, created_at, invite_code) VALUES (?, ?, ?, ?)",
        (name, owner_user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), invite_code),
    )
    connection.commit()
    company_id = cursor.lastrowid
    connection.close()
    return company_id


def get_company(company_id: int):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id, name, owner_user_id, created_at FROM companies WHERE id = ?",
        (company_id,),
    )
    row = cursor.fetchone()
    connection.close()
    return row


def get_user_company(user_id: int):
    """Return (company_id, company_name, role) for a user, or None."""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
    SELECT c.id, c.name, u.role
    FROM users u
    LEFT JOIN companies c ON c.id = u.company_id
    WHERE u.id = ?
    """, (user_id,))
    row = cursor.fetchone()
    connection.close()
    return row


def get_company_users(company_id: int):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
    SELECT id, username, role FROM users WHERE company_id = ? ORDER BY id ASC
    """, (company_id,))
    rows = cursor.fetchall()
    connection.close()
    return rows


def set_user_company(user_id: int, company_id: int):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute(
        "UPDATE users SET company_id = ? WHERE id = ?",
        (company_id, user_id),
    )
    connection.commit()
    connection.close()


def set_user_role(user_id: int, role: str):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute(
        "UPDATE users SET role = ? WHERE id = ?",
        (role, user_id),
    )
    connection.commit()
    connection.close()


def get_user_role(user_id: int) -> str:
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    connection.close()
    return row[0] if row else "employee"


# ─── Invite code helpers ──────────────────────────────────────────────────────

def _generate_invite_code_value() -> str:
    """Generate a short, readable 8-char invite code like ABCD-1234."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    part1 = "".join(secrets.choice(alphabet) for _ in range(4))
    part2 = "".join(secrets.choice(alphabet) for _ in range(4))
    return f"{part1}-{part2}"


def generate_invite_code() -> str:
    return _generate_invite_code_value()


def get_company_by_invite_code(invite_code: str):
    """Return (id, name, owner_user_id) for a company matching invite_code, or None."""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id, name, owner_user_id FROM companies WHERE invite_code = ?",
        (invite_code.strip().upper(),),
    )
    row = cursor.fetchone()
    connection.close()
    return row


def get_company_invite_code(company_id: int):
    """Return invite_code for a company, or None."""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT invite_code FROM companies WHERE id = ?", (company_id,))
    row = cursor.fetchone()
    connection.close()
    return row[0] if row else None


def set_company_invite_code(company_id: int, invite_code: str):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute(
        "UPDATE companies SET invite_code = ? WHERE id = ?",
        (invite_code, company_id),
    )
    connection.commit()
    connection.close()


def regenerate_company_invite_code(company_id: int) -> str:
    """Generate a fresh unique invite code for a company and persist it."""
    connection = connect_db()
    cursor = connection.cursor()
    while True:
        code = _generate_invite_code_value()
        cursor.execute(
            "SELECT id FROM companies WHERE invite_code = ? AND id != ?",
            (code, company_id),
        )
        if not cursor.fetchone():
            break
    cursor.execute(
        "UPDATE companies SET invite_code = ? WHERE id = ?",
        (code, company_id),
    )
    connection.commit()
    connection.close()
    return code


# ─── End invite code helpers ──────────────────────────────────────────────────

def get_company_id_for_user(user_id: int):
    """Return company_id for a user, or None."""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT company_id FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    connection.close()
    return row[0] if row else None


def get_api_usage_summary_by_operation_for_company(company_id: int):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
    SELECT operation_type, COUNT(*) as calls, SUM(total_tokens) as tokens,
           SUM(estimated_cost_usd) as cost, SUM(duration_minutes) as total_minutes
    FROM api_usage WHERE company_id = ?
    GROUP BY operation_type ORDER BY cost DESC
    """, (company_id,))
    rows = cursor.fetchall()
    connection.close()
    return rows


def get_total_api_usage_for_company(company_id: int):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
    SELECT SUM(total_tokens), SUM(estimated_cost_usd)
    FROM api_usage WHERE company_id = ?
    """, (company_id,))
    row = cursor.fetchone()
    connection.close()
    return row


def get_api_usage_summary_by_user_for_company(company_id: int):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
    SELECT u.username, a.user_id, COUNT(*) as calls,
           SUM(a.total_tokens) as tokens, SUM(a.estimated_cost_usd) as cost
    FROM api_usage a
    LEFT JOIN users u ON u.id = a.user_id
    WHERE a.company_id = ?
    GROUP BY a.user_id ORDER BY cost DESC
    """, (company_id,))
    rows = cursor.fetchall()
    connection.close()
    return rows


# ─── Course assignments ───────────────────────────────────────────────────────

def assign_course_to_user(course_id: int, user_id: int, company_id: int, assigned_by_user_id: int = None):
    connection = connect_db()
    cursor = connection.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """INSERT OR IGNORE INTO course_assignments
           (course_id, user_id, company_id, assigned_by_user_id, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (course_id, user_id, company_id, assigned_by_user_id, now),
    )
    connection.commit()
    connection.close()


def unassign_course_from_user(course_id: int, user_id: int, company_id: int):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute(
        "DELETE FROM course_assignments WHERE course_id = ? AND user_id = ? AND company_id = ?",
        (course_id, user_id, company_id),
    )
    connection.commit()
    connection.close()


def get_course_assignments(course_id: int, company_id: int):
    """Return list of user_ids assigned to a course within a company."""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT user_id FROM course_assignments WHERE course_id = ? AND company_id = ?",
        (course_id, company_id),
    )
    rows = cursor.fetchall()
    connection.close()
    return [r[0] for r in rows]


def get_assigned_courses_for_user(user_id: int, company_id: int):
    """Return list of course_ids assigned to a user within a company."""
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT course_id FROM course_assignments WHERE user_id = ? AND company_id = ?",
        (user_id, company_id),
    )
    rows = cursor.fetchall()
    connection.close()
    return [r[0] for r in rows]


def user_has_course_access(user_id: int, course_id: int) -> bool:
    """True if user created the course OR is assigned to it."""
    connection = connect_db()
    cursor = connection.cursor()
    # Created by user
    cursor.execute("SELECT id FROM courses WHERE id = ? AND user_id = ?", (course_id, user_id))
    if cursor.fetchone():
        connection.close()
        return True
    # Assigned
    cursor.execute(
        "SELECT id FROM course_assignments WHERE course_id = ? AND user_id = ?",
        (course_id, user_id),
    )
    result = cursor.fetchone() is not None
    connection.close()
    return result