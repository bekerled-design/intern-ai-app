import pandas as pd
from docx import Document
from pypdf import PdfReader

def read_uploaded_file(uploaded_file):
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".txt") or file_name.endswith(".csv"):
        return read_text_file(uploaded_file)

    if file_name.endswith(".docx"):
        return read_docx_file(uploaded_file)

    if file_name.endswith(".xlsx"):
        return read_xlsx_file(uploaded_file)

    if file_name.endswith(".pdf"):
        return read_pdf_file(uploaded_file)
    
    if file_name.endswith((".mp4", ".mp3", ".wav", ".m4a", ".webm")):
        return "VIDEO_FILE"
    
    return "Неподдерживаемый формат файла"


def read_text_file(uploaded_file):
    file_bytes = uploaded_file.read()

    encodings = [
        "utf-8",
        "utf-8-sig",
        "cp1251",
        "windows-1251",
        "latin-1"
    ]

    for encoding in encodings:
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue

    return "Ошибка чтения текстового файла"


def read_docx_file(uploaded_file):
    document = Document(uploaded_file)
    text = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            text.append(paragraph.text)

    return "\n".join(text)


def read_xlsx_file(uploaded_file):
    dataframes = pd.read_excel(
        uploaded_file,
        sheet_name=None
    )

    text = []

    for sheet_name, df in dataframes.items():
        text.append(f"Лист: {sheet_name}")
        text.append(df.to_string(index=False))

    return "\n\n".join(text)


def read_pdf_file(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = []

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text.append(page_text)

    return "\n".join(text)


import os


def save_uploaded_file(uploaded_file, file_content):

    os.makedirs("data", exist_ok=True)

    file_path = os.path.join(
        "data",
        uploaded_file.name
    )

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(file_content)