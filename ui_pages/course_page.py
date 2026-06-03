import streamlit as st
from database.database import (
    save_module_progress, get_completed_modules, add_activity,
)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
def show_course_page():
    if "course_data" not in st.session_state:
        _empty_state()
        return

    if st.session_state.get("lesson_mode"):
        _show_lesson()
    else:
        _show_module_list()


# ─────────────────────────────────────────────────────────────────────────────
# Empty state
# ─────────────────────────────────────────────────────────────────────────────
def _empty_state():
    st.markdown("""
    <div class="card" style="text-align:center;padding:64px 24px;">
        <div style="font-size:52px;margin-bottom:16px;">📚</div>
        <div style="font-size:18px;font-weight:700;color:#111827;margin-bottom:8px;">
            Курс не создан
        </div>
        <div style="font-size:14px;color:#6B7280;max-width:360px;margin:0 auto;">
            Загрузите материалы компании и создайте персональный курс обучения
        </div>
    </div>
    """, unsafe_allow_html=True)
    _, c, _ = st.columns([1, 1, 1])
    with c:
        if st.button("Загрузить материалы", type="primary",
                     key="course_goto_mats", use_container_width=True):
            st.session_state["page"] = "Материалы"
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Module list view
# ─────────────────────────────────────────────────────────────────────────────
def _show_module_list():
    course_data       = st.session_state["course_data"]
    course_id         = st.session_state.get("current_course_id")
    user_id           = st.session_state["user_id"]
    modules           = course_data.get("modules", [])
    total             = len(modules)
    completed_modules = get_completed_modules(user_id, course_id) if course_id else []
    done              = len(completed_modules)
    pct               = int(done / total * 100) if total else 0

    # ── Шапка ────────────────────────────────────────────────────────────
    st.markdown('<div class="page-title">Модули курса</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:white;border:1px solid #E5E7EB;border-radius:16px;
        padding:18px 24px;margin-bottom:16px;">
        <div style="display:flex;align-items:center;justify-content:space-between;
            gap:16px;margin-bottom:10px;">
            <div style="font-size:16px;font-weight:700;color:#111827;flex:1;
                min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                {course_data.get("course_title","Курс")}
            </div>
            <div style="font-size:13px;color:#6B7280;white-space:nowrap;">
                {done} из {total} модулей · <b style="color:#2563EB;">{pct}%</b>
            </div>
        </div>
        <div style="background:#EEF2FF;border-radius:100px;height:6px;overflow:hidden;">
            <div style="background:#2563EB;height:6px;border-radius:100px;
                width:{pct}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Кнопка продолжить ─────────────────────────────────────────────────
    next_idx = next((i for i in range(total) if i not in completed_modules), None)
    if next_idx is not None:
        col_btn, _ = st.columns([1, 3])
        with col_btn:
            if st.button("▶  Продолжить обучение", type="primary",
                         key="continue_btn", use_container_width=True):
                st.session_state["lesson_mode"] = True
                st.session_state["current_lesson_idx"] = next_idx
                st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Список модулей ────────────────────────────────────────────────────
    tab_all, tab_done = st.tabs(["Все модули", "Пройденные"])

    with tab_all:
        for idx, module in enumerate(modules):
            is_done   = idx in completed_modules
            prev_done = (idx == 0) or ((idx - 1) in completed_modules)
            is_active = not is_done and prev_done

            if is_done:
                s_cls, s_icon = "status-done",    "✓"
                badge = '<span class="badge badge-green">Завершено</span>'
            elif is_active:
                s_cls, s_icon = "status-active",  "▶"
                badge = '<span class="badge badge-blue">В процессе</span>'
            else:
                s_cls, s_icon = "status-pending", "○"
                badge = '<span class="badge badge-gray">Не начато</span>'

            col_card, col_btn2 = st.columns([5, 1])
            with col_card:
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:14px;
                    background:white;border:1px solid #E5E7EB;border-radius:14px;
                    padding:14px 20px;margin-bottom:8px;">
                    <div class="module-status {s_cls}"
                        style="font-size:14px;font-weight:700;">{s_icon}</div>
                    <div style="flex:1;min-width:0;">
                        <div style="font-weight:600;color:#111827;font-size:14px;
                            margin-bottom:2px;">{module['title']}</div>
                        <div style="font-size:12px;color:#6B7280;">
                            Модуль {idx+1} из {total}
                        </div>
                    </div>
                    {badge}
                </div>
                """, unsafe_allow_html=True)
            with col_btn2:
                if st.button("Открыть", key=f"open_{idx}", use_container_width=True):
                    st.session_state["lesson_mode"]        = True
                    st.session_state["current_lesson_idx"] = idx
                    st.rerun()

    with tab_done:
        done_list = [m for i, m in enumerate(modules) if i in completed_modules]
        if not done_list:
            st.markdown(
                '<div style="text-align:center;padding:32px;color:#9CA3AF;">'
                'Ещё нет завершённых модулей</div>',
                unsafe_allow_html=True,
            )
        for m in done_list:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:12px;
                background:white;border:1px solid #D1FAE5;border-radius:12px;
                padding:14px 20px;margin-bottom:6px;">
                <span style="color:#10B981;font-size:18px;font-weight:700;">✓</span>
                <span style="font-weight:600;color:#111827;font-size:14px;">{m['title']}</span>
            </div>
            """, unsafe_allow_html=True)

    # ── Практическое задание ──────────────────────────────────────────────
    practical = course_data.get("practical_task", "")
    if practical:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="task-highlight">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                <span style="font-size:22px;">📋</span>
                <div>
                    <div style="font-size:11px;font-weight:600;color:#92400E;
                        letter-spacing:0.5px;">ПРАКТИЧЕСКОЕ ЗАДАНИЕ</div>
                    <div style="font-size:16px;font-weight:700;color:#111827;">
                        Итоговое задание по курсу
                    </div>
                </div>
            </div>
            <hr style="border-color:#F59E0B;opacity:0.3;margin:12px 0;">
            <div style="font-size:14px;color:#374151;line-height:1.75;
                white-space:pre-wrap;">{practical}</div>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Lesson view
# ─────────────────────────────────────────────────────────────────────────────
def _show_lesson():
    course_data       = st.session_state["course_data"]
    course_id         = st.session_state.get("current_course_id")
    user_id           = st.session_state["user_id"]
    modules           = course_data.get("modules", [])
    total             = len(modules)
    idx               = st.session_state.get("current_lesson_idx", 0)
    completed_modules = get_completed_modules(user_id, course_id) if course_id else []

    if idx >= total:
        idx = 0
        st.session_state["current_lesson_idx"] = 0

    module = modules[idx]
    is_done = idx in completed_modules
    pct = int(len(completed_modules) / total * 100) if total else 0

    # ── Навигационная строка ──────────────────────────────────────────────
    col_back, col_info = st.columns([1, 4])
    with col_back:
        if st.button("← Все модули", key="back_to_list"):
            st.session_state.pop("lesson_mode", None)
            st.rerun()
    with col_info:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;padding-top:4px;">
            <span style="font-size:13px;color:#6B7280;">
                Урок {idx+1} из {total}
            </span>
            <div style="flex:1;background:#E5E7EB;border-radius:100px;
                height:6px;overflow:hidden;">
                <div style="background:#2563EB;height:6px;border-radius:100px;
                    width:{pct}%;"></div>
            </div>
            <span style="font-size:13px;font-weight:600;color:#2563EB;">{pct}%</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#E5E7EB;margin:16px 0 28px;'>",
                unsafe_allow_html=True)

    # ── Заголовок урока ───────────────────────────────────────────────────
    breadcrumb = course_data.get("course_title", "Курс")
    st.markdown(f"""
    <div style="margin-bottom:8px;">
        <span style="font-size:13px;color:#6B7280;">{breadcrumb}</span>
        <span style="font-size:13px;color:#9CA3AF;"> › Модуль {idx+1}</span>
    </div>
    <div style="font-size:26px;font-weight:700;color:#111827;margin-bottom:6px;">
        {module['title']}
    </div>
    """, unsafe_allow_html=True)

    if is_done:
        st.markdown('<span class="badge badge-green">✓ Завершено</span>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge badge-blue">В процессе</span>',
                    unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Контент урока ─────────────────────────────────────────────────────
    content = module.get("content") or module.get("description", "")

    # Рендерим контент напрямую — CSS в app.py стилизует .stMarkdown
    # Не используем split-div паттерн, он создаёт пустую карточку
    if content:
        st.markdown(content)

    # ── Практическое задание (на последнем уроке) ─────────────────────────
    practical = course_data.get("practical_task", "")
    if practical and idx == total - 1:
        st.markdown(f"""
        <div class="task-highlight">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                <span style="font-size:22px;">📋</span>
                <div>
                    <div style="font-size:11px;font-weight:600;color:#92400E;
                        letter-spacing:0.5px;">ПРАКТИЧЕСКОЕ ЗАДАНИЕ</div>
                    <div style="font-size:16px;font-weight:700;color:#111827;">
                        Итоговое задание по курсу
                    </div>
                </div>
            </div>
            <hr style="border-color:#F59E0B;opacity:0.3;margin:12px 0;">
            <div style="font-size:14px;color:#374151;line-height:1.75;
                white-space:pre-wrap;">{practical}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Навигация ─────────────────────────────────────────────────────────
    col_prev, col_done, col_next = st.columns([1, 2, 1])

    with col_prev:
        if idx > 0:
            if st.button("← Предыдущий", key="prev_lesson",
                         use_container_width=True):
                st.session_state["current_lesson_idx"] = idx - 1
                st.rerun()

    with col_done:
        if not is_done:
            if st.button("✓  Завершить урок", type="primary",
                         key="complete_lesson", use_container_width=True):
                if course_id:
                    save_module_progress(user_id, course_id, idx)
                    add_activity(user_id, f"Завершил модуль: {module['title']}")
                if idx < total - 1:
                    st.session_state["current_lesson_idx"] = idx + 1
                else:
                    # Последний урок — возвращаем на список
                    st.session_state.pop("lesson_mode", None)
                st.rerun()
        else:
            st.markdown(
                '<div style="text-align:center;padding:10px 0;font-size:14px;'
                'color:#10B981;font-weight:600;">✓ Урок завершён</div>',
                unsafe_allow_html=True,
            )

    with col_next:
        if idx < total - 1:
            if st.button("Следующий →", key="next_lesson",
                         use_container_width=True):
                st.session_state["current_lesson_idx"] = idx + 1
                st.rerun()
        elif is_done:
            if st.button("К списку модулей", key="finish_course",
                         use_container_width=True):
                st.session_state.pop("lesson_mode", None)
                st.rerun()
