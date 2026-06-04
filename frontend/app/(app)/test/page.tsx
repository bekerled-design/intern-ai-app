"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { CourseData, TestQuestion } from "@/lib/types";

export default function TestPage() {
  const router = useRouter();
  const [course, setCourse] = useState<CourseData | null>(null);
  const [current, setCurrent] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [submitted, setSubmitted] = useState(false);
  const [score, setScore] = useState(0);
  const [wrongTopics, setWrongTopics] = useState<string[]>([]);
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);

  useEffect(() => {
    const id = localStorage.getItem("current_course_id");
    if (!id) { router.push("/courses"); return; }
    api.get(`/courses/${id}`).then((r) => setCourse(r.data)).catch(() => router.push("/courses"));
  }, []);

  async function handleSubmit(finalAnswers: Record<number, string>) {
    if (!course) return;
    const questions = course.test;
    let correct = 0;
    const weak: string[] = [];
    questions.forEach((q, i) => {
      if (finalAnswers[i] === q.correct_answer) {
        correct++;
      } else {
        const topic = q.topic ?? q.module ?? q.question.slice(0, 40);
        if (!weak.includes(topic)) weak.push(topic);
      }
    });
    const pct = Math.round((correct / questions.length) * 100);
    setScore(pct);
    setWrongTopics(weak);
    setSubmitted(true);
    await api.post("/tests/result", { score: pct, weak_topics: weak });
    if (weak.length > 0) {
      setAnalysisLoading(true);
      api.get("/tests/analysis")
        .then((r) => setAnalysis(r.data.analysis ?? null))
        .catch(() => {})
        .finally(() => setAnalysisLoading(false));
    }
  }

  function selectAnswer(opt: string) {
    if (!course) return;
    const updated = { ...answers, [current]: opt };
    setAnswers(updated);

    const isLast = current === course.test.length - 1;
    if (!isLast) {
      setTimeout(() => setCurrent((c) => c + 1), 300);
    }
  }

  if (!course) return <div className="text-[#6B7280] text-sm">Загрузка...</div>;

  const questions: TestQuestion[] = course.test ?? [];

  if (questions.length === 0) {
    return (
      <div className="max-w-xl">
        <h1 className="text-[22px] font-bold text-[#111827] mb-6">Тест</h1>
        <div className="bg-white rounded-2xl border border-[#E5E7EB] p-10 text-center text-[#6B7280] text-sm">
          <div className="text-4xl mb-3">📝</div>
          <div className="font-medium mb-2">Тест не сгенерирован</div>
          <p className="text-xs">В этом курсе нет тестовых вопросов</p>
        </div>
      </div>
    );
  }

  if (submitted) {
    const correctCount = Math.round(score * questions.length / 100);
    return (
      <div className="max-w-xl">
        <h1 className="text-[22px] font-bold text-[#111827] mb-6">Результаты теста</h1>
        <div className="bg-white rounded-2xl border border-[#E5E7EB] p-8 text-center mb-4">
          <div className={`text-6xl font-bold mb-2 ${score >= 70 ? "text-[#10B981]" : "text-[#EF4444]"}`}>{score}%</div>
          <div className="text-sm text-[#6B7280] mb-1">
            {score >= 70 ? "Отличный результат! 🎉" : "Есть над чем поработать 📚"}
          </div>
          <div className="text-xs text-[#9CA3AF]">
            Правильных ответов: {correctCount} из {questions.length}
          </div>
          {/* Score bar */}
          <div className="w-full bg-[#E5E7EB] rounded-full h-3 mt-4">
            <div
              className={`h-3 rounded-full transition-all ${score >= 70 ? "bg-[#10B981]" : "bg-[#EF4444]"}`}
              style={{ width: `${score}%` }}
            />
          </div>
        </div>

        {wrongTopics.length > 0 && (
          <div className="bg-[#FFF7ED] rounded-2xl border border-[#FED7AA] p-5 mb-4">
            <div className="text-sm font-semibold text-[#111827] mb-2">⚠️ Темы для повторения:</div>
            <div className="flex flex-wrap gap-2">
              {wrongTopics.map((t) => (
                <span key={t} className="bg-[#FEF3C7] text-[#92400E] text-xs font-medium px-3 py-1 rounded-full">{t}</span>
              ))}
            </div>
          </div>
        )}

        {wrongTopics.length > 0 && (
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-[#111827] mb-2">🤖 AI-анализ ошибок</h3>
            <div className="bg-gradient-to-br from-[#EEF2FF] to-[#F8FAFF] rounded-2xl border border-[#C7D2FE] p-5">
              {analysisLoading ? (
                <p className="text-sm text-[#6B7280]">Анализирую ошибки...</p>
              ) : analysis ? (
                <p className="text-sm text-[#1E40AF] leading-relaxed whitespace-pre-wrap">{analysis}</p>
              ) : null}
            </div>
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={() => router.push("/modules")}
            className="bg-[#2563EB] text-white font-semibold px-5 py-2.5 rounded-[10px] hover:bg-[#1D4ED8] transition-colors text-sm"
          >
            К модулям
          </button>
          <button
            onClick={() => { setSubmitted(false); setAnswers({}); setCurrent(0); setAnalysis(null); }}
            className="border border-[#E5E7EB] text-[#374151] font-medium px-5 py-2.5 rounded-[10px] hover:bg-[#F3F4F6] transition-colors text-sm"
          >
            Пройти снова
          </button>
        </div>
      </div>
    );
  }

  const q = questions[current];
  const isLast = current === questions.length - 1;
  const progressPct = Math.round((current / questions.length) * 100);

  return (
    <div className="max-w-2xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-[22px] font-bold text-[#111827]">Тест</h1>
        <span className="text-sm text-[#6B7280]">{current + 1} / {questions.length}</span>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-[#E5E7EB] rounded-full h-1.5 mb-8">
        <div
          className="bg-[#2563EB] h-1.5 rounded-full transition-all duration-300"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Question card */}
      <div className="bg-white rounded-2xl border border-[#E5E7EB] p-8">
        {q.topic && (
          <div className="text-xs font-medium text-[#6B7280] uppercase tracking-wide mb-3">{q.topic ?? q.module}</div>
        )}
        <div className="text-base font-semibold text-[#111827] mb-6 leading-relaxed">{q.question}</div>

        <div className="flex flex-col gap-3">
          {q.options.map((opt) => {
            const selected = answers[current] === opt;
            return (
              <button
                key={opt}
                onClick={() => selectAnswer(opt)}
                disabled={current in answers}
                className={`text-left px-5 py-4 rounded-xl border text-sm transition-all ${
                  selected
                    ? "bg-[#EEF2FF] border-[#2563EB] text-[#1E40AF] font-semibold shadow-sm"
                    : "bg-white border-[#E5E7EB] text-[#111827] hover:border-[#2563EB] hover:bg-[#F8FAFF] disabled:opacity-60"
                }`}
              >
                {opt}
              </button>
            );
          })}
        </div>
      </div>

      {/* Navigation */}
      <div className="flex justify-between mt-4">
        <button
          onClick={() => setCurrent((c) => Math.max(0, c - 1))}
          disabled={current === 0}
          className="text-sm text-[#6B7280] hover:text-[#111827] disabled:opacity-30 transition-colors px-3 py-1.5"
        >
          ← Назад
        </button>
        {isLast ? (
          <button
            onClick={() => handleSubmit(answers)}
            disabled={!(current in answers)}
            className="bg-[#2563EB] text-white font-semibold px-5 py-2 rounded-[10px] text-sm hover:bg-[#1D4ED8] transition-colors disabled:opacity-40"
          >
            Завершить тест
          </button>
        ) : (
          current in answers && (
            <button
              onClick={() => setCurrent((c) => c + 1)}
              className="text-sm font-medium text-[#2563EB] hover:underline px-3 py-1.5"
            >
              Следующий →
            </button>
          )
        )}
      </div>
    </div>
  );
}
