import json
import streamlit as st
from database.database import get_user_courses, get_course_by_id
from datetime import datetime


def show_courses_page():
    st.markdown('<div class="page-title">Мои курсы</div>', unsafe_allow_html=True)

    if "user_id" not in st.session_state:
        st.info("Войдите в аккаунт.")
        return

    user_courses = get_user_courses(st.session_state["user_id"])

    if not user_courses:
        st.markdown("""
        <div class="card" style="text-align:center;padding:48px 24px;">
            <div style="font-size:40px;margin-bottom:16px;">📁</div>
            <div style="font-size:16px;font-weight:600;color:#111827;margin-bottom:8px;">
                Курсов пока нет
            </div>
            <div style="font-size:14px;color:#6B7280;">
                Загрузите материалы и создайте первый курс
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Загрузить материалы", type="primary", key="courses_goto_mats"):
            st.session_state["page"] = "Материалы"
            st.rerun()
        return

    for course in user_courses:
        course_id, course_title, due_date = course
        deadline_text = due_date if due_date else "Без дедлайна"
        is_overdue = False
        if due_date:
            try:
                dl = datetime.strptime(due_date, "%Y-%m-%d").date()
                is_overdue = dl < datetime.now().date()
            except Exception:
                pass

        badge = (
            '<span class="badge badge-yellow">Просрочен</span>'
            if is_overdue else
            '<span class="badge badge-blue">Активный</span>'
        )
        st.markdown(f"""
        <div class="card" style="margin-bottom:8px;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <div style="font-size:15px;font-weight:600;color:#111827;margin-bottom:6px;">
                        {course_title}
                    </div>
                    <div style="font-size:13px;color:#6B7280;">Дедлайн: {deadline_text}</div>
                </div>
                {badge}
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Открыть курс", key=f"open_course_{course_id}"):
            saved = get_course_by_id(course_id)
            if saved:
                course_data = json.loads(saved[0])
                st.session_state["course_data"] = course_data
                st.session_state["current_course_id"] = course_id
                st.session_state["page"] = "Модули"
                st.rerun()
