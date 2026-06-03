import streamlit as st
from database.database import save_test_result, save_weak_topic, add_activity
from ai.weakness_analyzer import analyze_weaknesses


def show_test_page(client):
    st.markdown('<div class="page-title">Тест</div>', unsafe_allow_html=True)

    if "course_data" not in st.session_state:
        st.markdown("""
        <div class="card" style="text-align:center;padding:48px 24px;">
            <div style="font-size:40px;margin-bottom:16px;">📝</div>
            <div style="font-size:16px;font-weight:600;color:#111827;margin-bottom:8px;">
                Тест недоступен
            </div>
            <div style="font-size:14px;color:#6B7280;">
                Сначала создайте курс из материалов компании
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Перейти к материалам", type="primary", key="test_goto_mats"):
            st.session_state["page"] = "Материалы"
            st.rerun()
        return

    questions = st.session_state["course_data"].get("test", [])
    total = len(questions)

    if total == 0:
        st.info("В курсе нет тестовых вопросов.")
        return

    # Инициализация состояния
    if "test_question_idx" not in st.session_state:
        st.session_state["test_question_idx"] = 0
        st.session_state["test_completed"] = False
        st.session_state["test_result_saved"] = False

    if st.session_state.get("test_completed"):
        _show_results(client, questions)
        return

    current_idx = st.session_state["test_question_idx"]

    if current_idx >= total:
        st.session_state["test_completed"] = True
        st.rerun()
        return

    # ── Прогресс ─────────────────────────────────────────────────────────
    pct = int(current_idx / total * 100)
    st.progress(pct / 100)
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;
        margin-bottom:20px;">
        <span style="font-size:13px;color:#6B7280;">
            Вопрос {current_idx + 1} из {total}
        </span>
        <span style="font-size:13px;font-weight:600;color:#2563EB;">{pct}%</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Карточка вопроса ──────────────────────────────────────────────────
    q = questions[current_idx]
    st.markdown(f"""
    <div class="card">
        <div style="font-size:16px;font-weight:600;color:#111827;line-height:1.6;">
            {q["question"]}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Варианты A/B/C/D ──────────────────────────────────────────────────
    options = q.get("options", [])[:4]
    labels = ["A", "B", "C", "D"]
    fmt = {opt: f"{labels[i]}  •  {opt}" for i, opt in enumerate(options)}

    selected = st.radio(
        "",
        options=options,
        format_func=lambda x: fmt.get(x, x),
        key=f"q_{current_idx}",
        index=None,
        label_visibility="collapsed",
    )

    # ── Навигация ─────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Пропустить вопрос", key="skip_q", use_container_width=True):
            st.session_state["test_question_idx"] += 1
            st.rerun()
    with col2:
        is_last = current_idx == total - 1
        label = "Завершить тест" if is_last else "Далее"
        if st.button(
            label, key="next_q",
            use_container_width=True,
            type="primary",
            disabled=(selected is None),
        ):
            st.session_state["test_question_idx"] += 1
            if is_last:
                st.session_state["test_completed"] = True
            st.rerun()


def _show_results(client, questions):
    st.markdown('<div class="page-title">Результаты теста</div>', unsafe_allow_html=True)

    correct_count = 0
    wrong_answers = []

    for i, q in enumerate(questions):
        user_ans = st.session_state.get(f"q_{i}")
        correct = q["correct_answer"]
        # «Быстрый» режим пишет поле "module", «Подробный» — "topic"
        topic_name = q.get("module") or q.get("topic") or "Общая тема"
        row = {
            "module": topic_name,
            "question": q["question"],
            "user_answer": user_ans or "Пропущен",
            "correct_answer": correct,
        }
        if user_ans == correct:
            correct_count += 1
        else:
            wrong_answers.append(row)

    total = len(questions)
    score = int(correct_count / total * 100) if total > 0 else 0

    # Сохраняем результат один раз
    if not st.session_state.get("test_result_saved"):
        if "user_id" in st.session_state:
            save_test_result(st.session_state["user_id"], score)
            add_activity(
                st.session_state["user_id"],
                f"Прошёл тест с результатом {score}%"
            )
            for wa in wrong_answers:
                save_weak_topic(st.session_state["user_id"], wa["module"])
        st.session_state["test_result_saved"] = True

    # ── Карточка результата ───────────────────────────────────────────────
    score_color = (
        "#10B981" if score >= 70 else
        "#F59E0B" if score >= 50 else
        "#EF4444"
    )
    st.markdown(f"""
    <div class="card" style="text-align:center;padding:36px 24px;">
        <div style="font-size:56px;font-weight:800;color:{score_color};">{score}%</div>
        <div style="font-size:15px;color:#6B7280;margin-top:10px;">
            Правильных ответов:
            <strong style="color:#111827;">{correct_count}</strong>
            из
            <strong style="color:#111827;">{total}</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.progress(score / 100)

    if wrong_answers:
        st.markdown('<div class="section-title">Разбор ошибок</div>', unsafe_allow_html=True)
        for wa in wrong_answers:
            st.markdown(f"""
            <div class="card" style="border-left:3px solid #EF4444;padding:16px 20px;">
                <div style="font-size:12px;color:#6B7280;margin-bottom:6px;">
                    Модуль: {wa['module']}
                </div>
                <div style="font-weight:600;color:#111827;font-size:14px;margin-bottom:10px;">
                    {wa['question']}
                </div>
                <div style="font-size:13px;color:#EF4444;margin-bottom:4px;">
                    ❌ Ваш ответ: {wa['user_answer']}
                </div>
                <div style="font-size:13px;color:#10B981;">
                    ✓ Правильный: {wa['correct_answer']}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with st.spinner("AI анализирует ошибки..."):
            feedback = analyze_weaknesses(client, wrong_answers)
        st.markdown('<div class="section-title">AI-рекомендации</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card">{feedback}</div>', unsafe_allow_html=True)
    else:
        st.success("🎉 Все ответы правильные! Отличный результат!")

    if st.button("Пройти тест заново", type="primary", key="retry_test"):
        for key in ["test_question_idx", "test_completed", "test_result_saved"]:
            st.session_state.pop(key, None)
        for i in range(len(questions)):
            st.session_state.pop(f"q_{i}", None)
        st.rerun()
