import streamlit as st
from database.database import (
    get_test_results, get_user_courses,
    get_notifications, mark_notification_as_read,
    get_overdue_courses, get_completed_modules,
)
from datetime import datetime


def _stat_card(icon, value, label, color):
    st.markdown(f"""
    <div style="background:white;border:1px solid #E5E7EB;border-radius:16px;
        padding:22px 16px;text-align:center;
        box-shadow:0 2px 8px rgba(0,0,0,0.04);height:100%;">
        <div style="font-size:26px;margin-bottom:10px;">{icon}</div>
        <div style="font-size:30px;font-weight:800;color:{color};
            margin-bottom:4px;line-height:1;">{value}</div>
        <div style="font-size:12px;color:#6B7280;margin-top:6px;">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def show_dashboard():
    if "user_id" not in st.session_state:
        return

    user_id   = st.session_state["user_id"]
    username  = st.session_state.get("username", "")

    # ── Данные ───────────────────────────────────────────────────────────
    results      = get_test_results(user_id)
    user_courses = get_user_courses(user_id)
    avg_score    = sum(r[0] for r in results) / len(results) if results else 0.0

    course_data       = st.session_state.get("course_data")
    current_course_id = st.session_state.get("current_course_id")

    completed_modules = []
    if course_data and current_course_id:
        completed_modules = get_completed_modules(user_id, current_course_id)

    modules         = course_data.get("modules", []) if course_data else []
    total_modules   = len(modules)
    completed_count = len(completed_modules)
    progress_pct    = int(avg_score)

    # Следующий незавершённый модуль
    next_module_idx = next(
        (i for i in range(total_modules) if i not in completed_modules),
        None,
    )

    # ── Уведомления ──────────────────────────────────────────────────────
    for notif in get_notifications(user_id)[:2]:
        notif_id, message, _ = notif
        c1, c2 = st.columns([14, 1])
        with c1:
            st.warning(f"🔔 {message}")
        with c2:
            if st.button("✕", key=f"notif_{notif_id}"):
                mark_notification_as_read(notif_id)
                st.rerun()

    # ── Hero ──────────────────────────────────────────────────────────────
    _hero_style = (
        "background:linear-gradient(135deg,#1E3A8A 0%,#2563EB 100%);"
        "border-radius:20px;padding:36px 40px;color:white;margin-bottom:28px;"
        "position:relative;overflow:hidden;"
    )
    _bg_icon = (
        '<div style="position:absolute;right:-10px;top:-10px;font-size:180px;'
        'opacity:0.05;pointer-events:none;line-height:1;">🎓</div>'
    )

    if user_courses:
        if progress_pct >= 70:
            hero_sub = "Отличный результат! Вы почти у цели 🏆"
        elif progress_pct >= 30:
            hero_sub = "Продолжайте в том же темпе — вы на правильном пути 💪"
        else:
            hero_sub = "Хорошее начало! Изучайте модули и двигайтесь вперёд 🚀"
        cta_label = "Продолжить обучение →"
        cta_page  = "Модули"

        # Все значения — обычные строки, без HTML внутри переменных
        mod_info       = f" • Модуль {completed_count}/{total_modules}" if total_modules else ""
        progress_label = f"Прогресс стажировки: {progress_pct}%{mod_info}"

        st.markdown(f"""
        <div style="{_hero_style}">
            {_bg_icon}
            <div style="font-size:12px;opacity:0.7;letter-spacing:1px;
                text-transform:uppercase;margin-bottom:8px;">Добро пожаловать</div>
            <div style="font-size:30px;font-weight:700;margin-bottom:6px;">
                Привет, {username}! 👋
            </div>
            <div style="font-size:15px;opacity:0.85;margin-bottom:24px;">{hero_sub}</div>
            <div style="background:rgba(255,255,255,0.25);border-radius:100px;
                height:8px;margin-bottom:8px;overflow:hidden;">
                <div style="background:white;height:8px;border-radius:100px;
                    width:{progress_pct}%;"></div>
            </div>
            <div style="font-size:13px;opacity:0.9;">{progress_label}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        hero_sub  = "Загрузите материалы компании и создайте свой первый курс"
        cta_label = "Начать обучение →"
        cta_page  = "Материалы"

        st.markdown(f"""
        <div style="{_hero_style}">
            {_bg_icon}
            <div style="font-size:30px;font-weight:700;margin-bottom:8px;">
                Привет, {username}! 👋
            </div>
            <div style="font-size:15px;opacity:0.85;">{hero_sub}</div>
        </div>
        """, unsafe_allow_html=True)

    col_cta, _ = st.columns([1, 4])
    with col_cta:
        if st.button(cta_label, type="primary", key="hero_cta", use_container_width=True):
            if next_module_idx is not None:
                st.session_state["lesson_mode"] = True
                st.session_state["current_lesson_idx"] = next_module_idx
            st.session_state["page"] = cta_page
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Статистика ────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _stat_card("📚", str(len(user_courses)),   "Курсов",           "#2563EB")
    with c2:
        _stat_card("📋", str(completed_count),      "Модулей пройдено", "#10B981")
    with c3:
        _stat_card("📝", str(len(results)),         "Тестов пройдено",  "#F59E0B")
    with c4:
        _stat_card("⭐", f"{avg_score:.0f}%",       "Средний балл",     "#8B5CF6")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Основной контент ──────────────────────────────────────────────────
    col_main, col_side = st.columns([3, 2])

    with col_main:
        st.markdown('<div class="section-title">Текущий курс</div>', unsafe_allow_html=True)

        if course_data:
            # Заголовок + прогресс-бар
            st.markdown(f"""
            <div class="card" style="padding:24px 28px;">
                <div style="display:flex;justify-content:space-between;
                    align-items:flex-start;margin-bottom:16px;">
                    <div>
                        <div style="font-size:11px;font-weight:600;color:#6B7280;
                            letter-spacing:0.5px;margin-bottom:4px;">АКТИВНЫЙ КУРС</div>
                        <div style="font-size:17px;font-weight:700;color:#111827;">
                            {course_data.get("course_title","Курс")}
                        </div>
                    </div>
                    <span class="badge badge-blue">Активный</span>
                </div>
                <div style="background:#EEF2FF;border-radius:100px;height:6px;
                    margin-bottom:6px;overflow:hidden;">
                    <div style="background:#2563EB;height:6px;border-radius:100px;
                        width:{progress_pct}%;"></div>
                </div>
                <div style="font-size:12px;color:#6B7280;margin-bottom:20px;">
                    Пройдено: {completed_count} из {total_modules} модулей
                </div>
            """, unsafe_allow_html=True)

            # Превью модулей (первые 5)
            for i, mod in enumerate(modules[:5]):
                done   = i in completed_modules
                active = not done and (i == 0 or (i - 1) in completed_modules)
                if done:
                    icon, color, bg, lbl = "✓", "#10B981", "#D1FAE5", "Завершено"
                elif active:
                    icon, color, bg, lbl = "▶", "#2563EB", "#DBEAFE", "В процессе"
                else:
                    icon, color, bg, lbl = "○", "#9CA3AF", "#F3F4F6", "Не начато"

                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:12px;
                    padding:10px 0;border-bottom:1px solid #F9FAFB;">
                    <div style="width:24px;height:24px;border-radius:50%;
                        background:{bg};color:{color};display:flex;
                        align-items:center;justify-content:center;
                        font-size:11px;font-weight:700;flex-shrink:0;">{icon}</div>
                    <div style="flex:1;font-size:14px;color:#374151;
                        white-space:nowrap;overflow:hidden;
                        text-overflow:ellipsis;">{mod['title']}</div>
                    <div style="font-size:12px;color:{color};white-space:nowrap;">
                        {lbl}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            if len(modules) > 5:
                st.markdown(
                    f'<div style="font-size:13px;color:#9CA3AF;text-align:center;'
                    f'padding:12px 0;">ещё {len(modules)-5} модулей</div>',
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

            if st.button("Перейти к модулям →", key="dash_mods", use_container_width=True):
                st.session_state["page"] = "Модули"
                st.rerun()
        else:
            st.markdown("""
            <div class="card" style="text-align:center;padding:52px 24px;">
                <div style="font-size:52px;margin-bottom:16px;">📚</div>
                <div style="font-size:16px;font-weight:600;color:#111827;
                    margin-bottom:8px;">Курс не создан</div>
                <div style="font-size:14px;color:#6B7280;">
                    Загрузите материалы и сгенерируйте персональный курс обучения
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Загрузить материалы →", key="dash_upload",
                         use_container_width=True, type="primary"):
                st.session_state["page"] = "Материалы"
                st.rerun()

    with col_side:
        # Просроченные
        today = datetime.now().date().isoformat()
        for c in get_overdue_courses(user_id, today):
            st.error(f"⚠️ Просрочен: {c[0]}")

        st.markdown('<div class="section-title">Ближайшие задачи</div>', unsafe_allow_html=True)

        if user_courses:
            for cid, ctitle, due_date in user_courses[-3:]:
                is_curr = cid == current_course_id
                badge_cls = "badge-blue" if is_curr else "badge-gray"
                badge_txt = "Активный" if is_curr else "Не начато"
                dl = f"до {due_date}" if due_date else "Без срока"
                st.markdown(f"""
                <div style="background:white;border:1px solid #E5E7EB;
                    border-radius:12px;padding:14px 16px;margin-bottom:8px;">
                    <div style="font-weight:600;color:#111827;font-size:13px;
                        margin-bottom:6px;white-space:nowrap;overflow:hidden;
                        text-overflow:ellipsis;">{ctitle}</div>
                    <div style="display:flex;justify-content:space-between;
                        align-items:center;">
                        <span style="font-size:12px;color:#6B7280;">{dl}</span>
                        <span class="badge {badge_cls}">{badge_txt}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align:center;padding:20px;color:#9CA3AF;font-size:13px;
                background:white;border-radius:12px;border:1px solid #F3F4F6;">
                Активных задач нет
            </div>
            """, unsafe_allow_html=True)

        # Карточка наставника
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#EEF2FF;border:1.5px solid #C7D2FE;
            border-radius:16px;padding:20px 24px;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                <div style="width:36px;height:36px;background:#2563EB;border-radius:10px;
                    display:flex;align-items:center;justify-content:center;
                    font-size:18px;flex-shrink:0;">🤖</div>
                <div style="font-weight:700;font-size:15px;color:#1E40AF;">
                    AI-наставник
                </div>
            </div>
            <div style="font-size:13px;color:#374151;line-height:1.6;">
                Задайте вопрос по материалам курса — получите мгновенный развёрнутый ответ
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Написать наставнику →", key="dash_mentor",
                     use_container_width=True):
            st.session_state["page"] = "AI-наставник"
            st.rerun()
