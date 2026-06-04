import hashlib
import json
import os
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
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password_hash TEXT
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

    connection.commit()
    connection.close()

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



def save_course(user_id, course_data, due_date=None):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    INSERT INTO courses (
        user_id,
        course_title,
        content,
        due_date
    )
    VALUES (?, ?, ?, ?)
    """, (
        user_id,
        course_data["course_title"],
        json.dumps(course_data, ensure_ascii=False),
        due_date
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

def save_material_chunk(user_id, file_name, chunk_text, embedding):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    INSERT INTO material_chunks (
        user_id,
        file_name,
        chunk_text,
        embedding
    )
    VALUES (?, ?, ?, ?)
    """, (
        user_id,
        file_name,
        chunk_text,
        embedding
    ))

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
    INSERT INTO course_progress (
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
    SELECT module_index
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

def get_all_users():

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("""
    SELECT id, username
    FROM users
    """)

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

def create_job(user_id):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
    INSERT INTO course_generation_jobs (user_id, status, created_at)
    VALUES (?, 'pending', ?)
    """, (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    connection.commit()
    job_id = cursor.lastrowid
    connection.close()
    return job_id


def update_job_status(job_id, status, course_id=None, error=None, progress_done=None, progress_total=None):
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
    SELECT id, user_id, status, course_id, progress_done, progress_total, error
    FROM course_generation_jobs WHERE id = ?
    """, (job_id,))
    row = cursor.fetchone()
    connection.close()
    return row


def get_active_job(user_id):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
    SELECT id, user_id, status, course_id, progress_done, progress_total, error
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
    SELECT id, user_id, status, course_id, progress_done, progress_total, error
    FROM course_generation_jobs
    WHERE user_id = ? AND status = 'done' AND course_id IS NOT NULL
    ORDER BY id DESC LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()
    connection.close()
    return row