import streamlit as st
from database.database import save_ai_chat_message
from ai.mentor_chat import ask_ai_mentor


def show_mentor_page(client):

    # ── Стили страницы ────────────────────────────────────────────────────
    # st.chat_input встроенно закреплён внизу экрана — чат скроллится за ним.
    st.markdown("""
    <style>
    [data-testid="stMain"] .block-container { max-width: 880px !important; }
    /* Карточка ответа наставника (st.container border) */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 14px !important;
        border-color: #E5E7EB !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
        background: white !important;
    }
    /* Поле ввода chat_input — фон под ширину сайдбара */
    [data-testid="stBottomBlockContainer"] {
        background: #F4F6FB !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Hero (компактный) ─────────────────────────────────────────────────
    st.markdown("""
    <div style="background:linear-gradient(135deg,#EEF2FF 0%,#E0E7FF 100%);
        border:1.5px solid #C7D2FE;border-radius:18px;padding:20px 28px;
        margin-bottom:20px;display:flex;align-items:center;gap:16px;">
        <div style="width:48px;height:48px;background:#2563EB;border-radius:14px;
            display:flex;align-items:center;justify-content:center;
            font-size:24px;flex-shrink:0;
            box-shadow:0 6px 16px rgba(37,99,235,0.3);">🤖</div>
        <div>
            <div style="font-size:20px;font-weight:800;color:#1E3A8A;">
                AI-наставник
            </div>
            <div style="font-size:13px;color:#3730A3;line-height:1.5;">
                Задавайте вопросы по материалам курса, заданиям и регламентам компании
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Проверяем наличие данных
    has_course   = "course_data"      in st.session_state
    has_material = "company_material"  in st.session_state

    if not has_material:
        st.markdown("""
        <div class="card" style="text-align:center;padding:40px;">
            <div style="font-size:36px;margin-bottom:12px;">📄</div>
            <div style="font-size:15px;font-weight:600;color:#111827;margin-bottom:6px;">
                Материалы не загружены
            </div>
            <div style="font-size:13px;color:#6B7280;">
                Сначала загрузите материалы компании, чтобы наставник мог
                отвечать на вопросы по ним
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Загрузить материалы →", type="primary", key="mentor_goto_mats"):
            st.session_state["page"] = "Материалы"
            st.rerun()
        return

    # История чата в session state (только для отображения)
    if "mentor_history" not in st.session_state:
        st.session_state["mentor_history"] = []

    # ── Лента диалога ──────────────────────────────────────────────────────
    if st.session_state["mentor_history"]:
        col_title, col_clear = st.columns([3, 1])
        with col_title:
            st.markdown('<div class="section-title" style="margin-top:6px;">'
                        'Диалог</div>', unsafe_allow_html=True)
        with col_clear:
            if st.button("Очистить", key="clear_history", use_container_width=True):
                st.session_state["mentor_history"] = []
                st.rerun()

        for item in st.session_state["mentor_history"]:
            _render_qa(item["q"], item["a"])
    else:
        # Пустое состояние — подсказки
        st.markdown("""
        <div style="text-align:center;padding:40px 20px;color:#9CA3AF;">
            <div style="font-size:40px;margin-bottom:12px;">💬</div>
            <div style="font-size:14px;">
                Задайте первый вопрос наставнику — он найдёт ответ в материалах курса
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Поле ввода (st.chat_input закреплён внизу экрана) ─────────────────
    user_question = st.chat_input(
        "Спросите о материалах, задании или регламентах...",
        key="mentor_chat_input",
    )

    # ── Обработка вопроса ─────────────────────────────────────────────────
    if user_question and user_question.strip():
        if not has_course:
            st.warning("Сначала сгенерируйте курс на странице «Материалы», "
                       "чтобы наставник мог отвечать по вашей программе обучения.")
            return

        try:
            with st.spinner("Наставник анализирует материалы и готовит ответ..."):
                ai_answer = ask_ai_mentor(
                    client,
                    st.session_state["company_material"],
                    st.session_state["course_data"],
                    user_question.strip(),
                )
        except Exception as error:
            st.error("Не удалось получить ответ от наставника.")
            st.code(str(error))
            return

        # Сохраняем в БД
        if "user_id" in st.session_state:
            save_ai_chat_message(
                st.session_state["user_id"],
                user_question.strip(),
                ai_answer,
            )

        # Добавляем в историю UI
        st.session_state["mentor_history"].append({
            "q": user_question.strip(),
            "a": ai_answer,
        })
        st.rerun()


def _render_qa(question, answer):
    """Рендерит пару вопрос-ответ как сообщения чата. Markdown ответа сохраняется."""

    # Сообщение пользователя — пузырь справа (синий)
    st.markdown(f"""
    <div style="display:flex;justify-content:flex-end;margin-bottom:14px;">
        <div style="background:#2563EB;color:white;border-radius:16px 16px 4px 16px;
            padding:12px 18px;max-width:75%;font-size:14px;line-height:1.5;
            box-shadow:0 2px 6px rgba(37,99,235,0.2);">
            {question}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Ответ наставника — карточка слева с иконкой
    col_icon, col_msg = st.columns([1, 11])
    with col_icon:
        st.markdown("""
        <div style="width:34px;height:34px;background:#EEF2FF;border-radius:50%;
            display:flex;align-items:center;justify-content:center;
            font-size:17px;margin-top:4px;">🤖</div>
        """, unsafe_allow_html=True)
    with col_msg:
        with st.container(border=True):
            st.markdown(
                '<div style="font-size:11px;font-weight:700;color:#6B7280;'
                'letter-spacing:0.5px;margin-bottom:6px;">НАСТАВНИК</div>',
                unsafe_allow_html=True,
            )
            # Markdown ответа сохраняется (списки, заголовки, **жирный**)
            st.markdown(answer)

    st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)
