import streamlit as st
from ai.video_transcriber import transcribe_video
from ai.embeddings import create_embedding
from ai.course_generator import generate_course_by_parts, generate_course_lite
from database.database import (
    get_company_materials, delete_company_material,
    save_company_material, material_exists,
    save_material_chunk, save_course,
)
from utils.file_loader import read_uploaded_file, save_uploaded_file
from utils.text_search import split_text_into_chunks


def show_materials_page(client):
    st.markdown('<div class="page-title">Материалы компании</div>', unsafe_allow_html=True)

    if "user_id" not in st.session_state:
        st.info("Войдите в аккаунт.")
        return

    user_id = st.session_state["user_id"]

    # ── Загрузка файлов ───────────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:14px;color:#6B7280;margin-bottom:20px;max-width:620px;">
        Загрузите внутренние документы, регламенты или инструкции компании.
        ИИ проанализирует их и создаст персональный курс обучения.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">Загрузить файлы</div>', unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Загрузка файлов",
        type=["txt", "csv", "xlsx", "docx", "pdf", "mp4", "mp3", "wav", "m4a", "webm"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        all_text = ""
        for uf in uploaded_files:
            pkey = f"processed_{uf.name}_{uf.size}"

            if pkey in st.session_state:
                file_content = st.session_state[pkey]
            else:
                if uf.name.lower().endswith((".mp4", ".mp3", ".wav", ".m4a", ".webm")):
                    with st.spinner(f"Транскрибирую: {uf.name}..."):
                        try:
                            file_content = transcribe_video(client, uf)
                            if not file_content.strip():
                                st.warning(f"Не удалось распознать аудио: {uf.name}")
                                continue
                        except Exception as e:
                            st.error(f"Ошибка транскрипции: {uf.name}")
                            st.code(str(e))
                            continue
                else:
                    file_content = read_uploaded_file(uf)

                st.session_state[pkey] = file_content
                save_uploaded_file(uf, file_content)

                if not material_exists(user_id, uf.name):
                    save_company_material(user_id, uf.name, file_content)
                    chunks = split_text_into_chunks(file_content[:500_000])
                    with st.spinner(f"Создаю embeddings: {uf.name}..."):
                        for chunk in chunks:
                            try:
                                emb = create_embedding(client, chunk)
                            except Exception:
                                continue
                            save_material_chunk(user_id, uf.name, chunk, emb)

                st.success(f"✓ {uf.name}")

            all_text += f"\n\nФайл: {uf.name}\n\n{file_content}\n\n"

        if all_text:
            st.session_state["company_material"] = all_text
            st.session_state["current_upload_material"] = all_text

    # ── Генерация курса ───────────────────────────────────────────────────
    if st.session_state.get("company_material"):
        st.markdown(
            '<div class="section-title">Создать курс из материалов</div>',
            unsafe_allow_html=True,
        )

        mode = st.radio(
            "Режим генерации",
            ["Быстрый", "Подробный"],
            horizontal=True,
            key="gen_mode",
        )
        if mode == "Подробный":
            st.info("Подробный режим занимает несколько минут.")

        if st.button("Сгенерировать курс", type="primary", key="gen_course_btn"):
            material = st.session_state.get(
                "current_upload_material",
                st.session_state.get("company_material", ""),
            )
            try:
                with st.spinner("ИИ создаёт курс..."):
                    if mode == "Быстрый":
                        course_data = generate_course_lite(client, material)
                    else:
                        course_data = generate_course_by_parts(client, material)

                st.session_state["course_data"] = course_data
                course_id = save_course(user_id, course_data)
                st.session_state["current_course_id"] = course_id
                st.session_state["page"] = "Модули"
                st.success("Курс создан!")
                st.rerun()
            except Exception as e:
                st.error("Ошибка при генерации курса")
                st.code(str(e))

    # ── Список загруженных файлов ─────────────────────────────────────────
    st.markdown(
        '<div class="section-title">Загруженные файлы</div>',
        unsafe_allow_html=True,
    )

    materials = get_company_materials(user_id)

    if not materials:
        st.markdown("""
        <div class="card" style="text-align:center;padding:32px;color:#6B7280;">
            <div style="font-size:32px;margin-bottom:8px;">📄</div>
            <div>Файлы не загружены</div>
        </div>
        """, unsafe_allow_html=True)
        return

    _EXT_ICON = {
        "pdf": "📄", "docx": "📝", "doc": "📝",
        "xlsx": "📊", "xls": "📊", "csv": "📊",
        "txt": "📃", "mp3": "🎵", "wav": "🎵",
        "m4a": "🎵", "mp4": "🎬", "webm": "🎬",
    }

    st.markdown(
        f'<div style="font-size:13px;color:#6B7280;margin-bottom:12px;">'
        f'Загружено файлов: {len(materials)}</div>',
        unsafe_allow_html=True,
    )

    for i, mat in enumerate(materials):
        fname = mat[0]
        ext   = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
        icon  = _EXT_ICON.get(ext, "📄")

        col_info, col_btn = st.columns([6, 1])
        with col_info:
            st.markdown(f"""
            <div style="background:white;border:1px solid #E5E7EB;
                border-radius:12px;padding:14px 18px;
                display:flex;align-items:center;gap:12px;margin-bottom:8px;">
                <span style="font-size:22px;flex-shrink:0;">{icon}</span>
                <div>
                    <div style="font-weight:600;color:#111827;font-size:14px;">
                        {fname}
                    </div>
                    <div style="font-size:12px;color:#10B981;margin-top:2px;">
                        ✓ Загружен и обработан
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col_btn:
            if st.button("Удалить", key=f"del_mat_{i}", use_container_width=True):
                delete_company_material(user_id, fname)
                st.success(f"Файл «{fname}» удалён")
                st.rerun()
