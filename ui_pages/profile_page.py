import streamlit as st
from database.database import (
    get_test_results, get_user_courses,
    get_user_activity, get_weak_topics,
    get_completed_modules,
)


def show_profile_page():
    if "user_id" not in st.session_state:
        st.info("Войдите в аккаунт.")
        return

    user_id = st.session_state["user_id"]
    username = st.session_state.get("username", "Пользователь")
    initial = username[0].upper() if username else "U"

    st.markdown('<div class="page-title">Профиль</div>', unsafe_allow_html=True)

    # ── Карточка пользователя ─────────────────────────────────────────────
    st.markdown(f"""
    <div class="card">
        <div style="display:flex;align-items:center;gap:16px;">
            <div style="width:60px;height:60px;background:#EEF2FF;border-radius:50%;
                display:flex;align-items:center;justify-content:center;
                font-size:22px;font-weight:700;color:#2563EB;flex-shrink:0;">
                {initial}
            </div>
            <div>
                <div style="font-size:18px;font-weight:700;color:#111827;">
                    {username}
                </div>
                <div style="font-size:13px;color:#6B7280;margin-top:2px;">Стажёр</div>
                <div style="margin-top:8px;">
                    <span class="badge badge-blue">Активный стажёр</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Статистика ────────────────────────────────────────────────────────
    results = get_test_results(user_id)
    user_courses = get_user_courses(user_id)
    avg_score = 0.0
    if results:
        avg_score = sum(r[0] for r in results) / len(results)

    completed_count = 0
    current_course_id = st.session_state.get("current_course_id")
    course_data = st.session_state.get("course_data")
    if current_course_id and course_data:
        completed = get_completed_modules(user_id, current_course_id)
        completed_count = len(completed)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-value">{avg_score:.0f}%</div>'
            f'<div class="metric-label">Прогресс</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-value">{completed_count}</div>'
            f'<div class="metric-label">Завершено модулей</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-value">{len(results)}</div>'
            f'<div class="metric-label">Пройдено тестов</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-value">{len(user_courses)}</div>'
            f'<div class="metric-label">Курсов</div></div>',
            unsafe_allow_html=True,
        )

    # ── Вкладки ───────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["Прогресс", "Активность", "Слабые темы"])

    with tab1:
        if results:
            st.markdown('<div class="section-title">Общий прогресс</div>', unsafe_allow_html=True)
            st.progress(min(avg_score / 100, 1.0))
            st.markdown(
                f'<div style="text-align:right;font-size:13px;color:#6B7280;margin-top:4px;">'
                f'{avg_score:.0f}%</div>',
                unsafe_allow_html=True,
            )

            st.markdown('<div class="section-title">История тестов</div>', unsafe_allow_html=True)
            for i, r in enumerate(reversed(results)):
                score = r[0]
                c = (
                    "#10B981" if score >= 70 else
                    "#F59E0B" if score >= 50 else
                    "#EF4444"
                )
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:center;
                    padding:12px 0;border-bottom:1px solid #F3F4F6;">
                    <span style="color:#374151;font-size:14px;">
                        Тест {len(results) - i}
                    </span>
                    <span style="font-weight:700;color:{c};">{score}%</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Тесты ещё не проходились.")

    with tab2:
        activity = get_user_activity(user_id)
        if activity:
            for action, created_at in activity:
                st.markdown(f"""
                <div style="display:flex;gap:12px;padding:12px 0;
                    border-bottom:1px solid #F3F4F6;">
                    <div style="width:8px;height:8px;background:#2563EB;border-radius:50%;
                        margin-top:5px;flex-shrink:0;"></div>
                    <div>
                        <div style="font-size:14px;color:#111827;">{action}</div>
                        <div style="font-size:12px;color:#6B7280;margin-top:2px;">
                            {created_at}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Активности пока нет.")

    with tab3:
        weak_topics = get_weak_topics(user_id)
        if weak_topics:
            unique = list(dict.fromkeys(weak_topics))
            for topic in unique[-10:]:
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;
                    padding:10px 0;border-bottom:1px solid #F3F4F6;">
                    <span style="color:#EF4444;">⚠</span>
                    <span style="font-size:14px;color:#111827;">{topic}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align:center;padding:32px;color:#6B7280;">
                <div style="font-size:32px;margin-bottom:8px;">✓</div>
                <div>Слабых тем не обнаружено</div>
            </div>
            """, unsafe_allow_html=True)
