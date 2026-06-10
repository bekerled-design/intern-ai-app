import io
import pandas as pd
from docx import Document
from pypdf import PdfReader


def read_uploaded_file(uploaded_file):
    """Accept an object with .name and .read() -> bytes."""
    file_name = uploaded_file.name.lower()
    raw = uploaded_file.read()
    if isinstance(raw, str):
        raw = raw.encode("utf-8")

    if file_name.endswith(".txt") or file_name.endswith(".csv"):
        return _decode_text(raw)

    if file_name.endswith(".docx"):
        return _read_docx(raw)

    if file_name.endswith(".xlsx"):
        return _read_xlsx(raw)

    if file_name.endswith(".pdf"):
        return _read_pdf(raw)

    if file_name.endswith((".mp4", ".mp3", ".wav", ".m4a", ".webm")):
        return "VIDEO_FILE"

    return "Неподдерживаемый формат файла"


def _decode_text(raw: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp1251", "windows-1251", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return "Ошибка чтения текстового файла"


def _read_docx(raw: bytes) -> str:
    document = Document(io.BytesIO(raw))
    return "\n".join(p.text for p in document.paragraphs if p.text.strip())


def _read_xlsx(raw: bytes) -> str:
    dataframes = pd.read_excel(io.BytesIO(raw), sheet_name=None)
    parts = []
    for sheet_name, df in dataframes.items():
        parts.append(f"Лист: {sheet_name}")
        parts.append(df.to_string(index=False))
    return "\n\n".join(parts)


def _read_pdf(raw: bytes) -> str:
    reader = PdfReader(io.BytesIO(raw))
    pages = [p.extract_text() for p in reader.pages if p.extract_text()]
    return "\n".join(pages)


# legacy aliases used by old Streamlit code (kept for safety)
def read_text_file(uploaded_file):
    return _decode_text(uploaded_file.read())

def read_docx_file(uploaded_file):
    return _read_docx(uploaded_file.read())

def read_xlsx_file(uploaded_file):
    return _read_xlsx(uploaded_file.read())

def read_pdf_file(uploaded_file):
    return _read_pdf(uploaded_file.read())


import os

def save_uploaded_file(uploaded_file, file_content):
    os.makedirs("data", exist_ok=True)
    file_path = os.path.join("data", uploaded_file.name)
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(file_content)
