import streamlit as st

from ai.retraining_generator import generate_retraining_course
from database.database import save_course
from database.database import create_notification
from database.database import get_user_activity
from ai.recommendations import generate_recommendations
from database.database import (
    get_all_users,
    get_user_courses,
    get_test_results,
    get_weak_topics,
)


def show_admin_page(client):
    st.markdown('<div class="page-title">Администратор</div>', unsafe_allow_html=True)

    users = get_all_users()

    if not users:
        st.info("Пользователей пока нет.")
        return

    for user in users:
        user_id  = user[0]
        username = user[1]

        # ── Бизнес-данные (порядок вызовов не изменён) ───────────────────
        courses       = get_user_courses(user_id)
        results       = get_test_results(user_id)
        average_score = 0
        if results:
            scores        = [r[0] for r in results]
            average_score = sum(scores) / len(scores)

        weak_topics     = get_weak_topics(user_id)
        recommendations = generate_recommendations(weak_topics)
        activity        = get_user_activity(user_id)

        initial = username[0].upper() if username else "U"

        # ── Слабые темы: строим HTML без отступов (иначе Markdown → code block) ──
        if weak_topics:
            tags_html = " ".join(
                '<span class="badge badge-yellow" '
                f'style="margin-right:4px;margin-bottom:4px;">{t}</span>'
                for t in weak_topics[-5:]
            )
            weak_html = (
                '<div style="margin-top:14px;padding-top:14px;border-top:1px solid #F3F4F6;">'
                '<div style="font-size:12px;font-weight:600;color:#374151;margin-bottom:8px;">Слабые темы</div>'
                f'<div>{tags_html}</div>'
                '</div>'
            )
        else:
            weak_html = (
                '<div style="margin-top:14px;padding-top:14px;border-top:1px solid #F3F4F6;">'
                '<div style="font-size:13px;color:#9CA3AF;">Слабых тем нет</div>'
                '</div>'
            )

        # ── Карточка пользователя — весь HTML одной строкой (без переносов с отступами) ──
        st.markdown(
            f'<div class="card" style="padding:24px 28px;margin-bottom:12px;">'
            f'<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px;">'
            f'<div style="display:flex;align-items:center;gap:12px;">'
            f'<div style="width:44px;height:44px;background:#EEF2FF;border-radius:50%;'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:18px;font-weight:700;color:#2563EB;flex-shrink:0;">{initial}</div>'
            f'<div>'
            f'<div style="font-weight:700;font-size:16px;color:#111827;">{username}</div>'
            f'<div style="font-size:12px;color:#6B7280;">Стажёр</div>'
            f'</div></div>'
            f'<div style="display:flex;gap:28px;text-align:center;">'
            f'<div><div style="font-size:22px;font-weight:800;color:#2563EB;">{len(courses)}</div>'
            f'<div style="font-size:11px;color:#6B7280;">курсов</div></div>'
            f'<div><div style="font-size:22px;font-weight:800;color:#10B981;">{len(results)}</div>'
            f'<div style="font-size:11px;color:#6B7280;">тестов</div></div>'
            f'<div><div style="font-size:22px;font-weight:800;color:#F59E0B;">{average_score:.0f}%</div>'
            f'<div style="font-size:11px;color:#6B7280;">средний балл</div></div>'
            f'</div></div>'
            f'{weak_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── AI-рекомендации ───────────────────────────────────────────────
        if recommendations:
            recs_html = "".join(
                f'<div style="font-size:13px;color:#374151;padding:3px 0;">✅ {rec}</div>'
                for rec in recommendations
            )
            st.markdown(
                '<div style="background:#F0FDF4;border:1px solid #A7F3D0;'
                'border-radius:14px;padding:16px 20px;margin-bottom:10px;">'
                '<div style="font-size:13px;font-weight:600;color:#065F46;margin-bottom:10px;">✨ AI-рекомендации</div>'
                f'{recs_html}</div>',
                unsafe_allow_html=True,
            )

        # ── Активность — без expander (иконка _arrow_right не грузится) ──
        if activity:
            act_items = "".join(
                f'<div style="font-size:13px;color:#6B7280;padding:5px 0;'
                f'border-bottom:1px solid #F9FAFB;">🕒 {created_at} — {action}</div>'
                for action, created_at in activity
            )
            st.markdown(
                '<div style="background:white;border:1px solid #E5E7EB;'
                'border-radius:12px;padding:14px 18px;margin-bottom:10px;">'
                '<div style="font-size:13px;font-weight:600;color:#374151;margin-bottom:10px;">'
                'Активность</div>'
                f'{act_items}</div>',
                unsafe_allow_html=True,
            )

        # ── Доп. обучение — без expander ─────────────────────────────────
        if weak_topics:
            st.markdown(
                '<div style="font-size:14px;font-weight:600;color:#374151;'
                'margin:12px 0 8px;">📚 Дополнительное обучение</div>',
                unsafe_allow_html=True,
            )
            col_date, col_btn = st.columns([2, 1])
            with col_date:
                due_date = st.date_input(
                    "Дедлайн",
                    key=f"deadline_{user_id}",
                )
            with col_btn:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button(
                    "Создать обучение",
                    key=f"retraining_{user_id}",
                    type="primary",
                    use_container_width=True,
                ):
                    if "company_material" not in st.session_state:
                        st.warning(
                            "Сначала загрузите материалы компании на странице Материалы."
                        )
                    else:
                        with st.spinner("ИИ создаёт дополнительное обучение..."):
                            retraining_course = generate_retraining_course(
                                client,
                                weak_topics[-5:],
                                st.session_state["company_material"],
                            )
                            course_id = save_course(
                                user_id,
                                retraining_course,
                                str(due_date),
                            )
                            create_notification(
                                user_id,
                                "Вам назначено дополнительное обучение.",
                            )
                            st.success(
                                f"Дополнительное обучение создано. ID: {course_id}"
                            )

        st.markdown(
            "<hr style='border-color:#F3F4F6;margin:16px 0 28px;'>",
            unsafe_allow_html=True,
        )
