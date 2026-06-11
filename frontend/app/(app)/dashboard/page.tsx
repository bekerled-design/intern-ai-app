"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { getUser } from "@/lib/auth";
import { Course } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

export default function DashboardPage() {
  const router = useRouter();
  const user = getUser();
  const [courses, setCourses] = useState<Course[]>([]);
  const [scores, setScores] = useState<number[]>([]);
  const [activity, setActivity] = useState<{ action: string; created_at: string }[]>([]);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    if (!user) return;
    const failLoad = () => setLoadError("Не удалось загрузить данные. Обновите страницу.");
    api.get(`/users/${user.user_id}/courses`).then((r) => setCourses(r.data)).catch(failLoad);
    api.get("/tests/results").then((r) => setScores(r.data.scores ?? [])).catch(failLoad);
    api.get("/activity").then((r) => setActivity(r.data ?? [])).catch(failLoad);
  }, []);

  const avgScore = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : null;
  const lastCourse = courses[0] ?? null;

  return (
    <div>
      {loadError && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600">
          {loadError}
        </div>
      )}

      {/* Hero */}
      <div className="rounded-2xl bg-gradient-to-br from-[#1E3A8A] to-[#2563EB] text-white p-8 mb-6 flex items-center justify-between">
        <div>
          <div className="text-sm text-[#BFDBFE] mb-1">Добро пожаловать 👋</div>
          <h1 className="text-2xl font-bold mb-2">{user?.username ?? "Стажёр"}</h1>
          <p className="text-sm text-[#93C5FD]">
            {courses.length === 0
              ? "Загрузите материалы и создайте первый курс"
              : `У вас ${courses.length} ${courses.length === 1 ? "курс" : courses.length < 5 ? "курса" : "курсов"}`}
          </p>
        </div>
        <div className="text-6xl opacity-20 select-none">🎓</div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-2xl border border-[#E5E7EB] p-5 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-[#EEF2FF] flex items-center justify-center text-2xl">📚</div>
          <div>
            <div className="text-[26px] font-bold text-[#111827] leading-none">{courses.length}</div>
            <div className="text-xs text-[#6B7280] mt-1">Курсов</div>
          </div>
        </div>
        <div className="bg-white rounded-2xl border border-[#E5E7EB] p-5 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-[#F0FDF4] flex items-center justify-center text-2xl">✅</div>
          <div>
            <div className="text-[26px] font-bold text-[#111827] leading-none">{scores.length}</div>
            <div className="text-xs text-[#6B7280] mt-1">Тестов пройдено</div>
          </div>
        </div>
        <div className="bg-white rounded-2xl border border-[#E5E7EB] p-5 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-[#FFF7ED] flex items-center justify-center text-2xl">🏆</div>
          <div>
            <div className={`text-[26px] font-bold leading-none ${avgScore !== null ? (avgScore >= 70 ? "text-[#10B981]" : "text-[#EF4444]") : "text-[#111827]"}`}>
              {avgScore !== null ? `${avgScore}%` : "—"}
            </div>
            <div className="text-xs text-[#6B7280] mt-1">Средний балл</div>
          </div>
        </div>
      </div>

      {/* Quick actions when no courses */}
      {courses.length === 0 && (
        <div className="bg-white rounded-2xl border border-[#E5E7EB] p-8 mb-6 text-center">
          <div className="text-4xl mb-3">🚀</div>
          <h2 className="text-[15px] font-semibold text-[#111827] mb-2">Начните обучение</h2>
          <p className="text-sm text-[#6B7280] mb-4">Загрузите документы компании, и ИИ создаст персональный курс</p>
          <button
            onClick={() => router.push("/materials")}
            className="bg-[#2563EB] text-white font-semibold px-6 py-2.5 rounded-[10px] hover:bg-[#1D4ED8] transition-colors text-sm"
          >
            Загрузить материалы
          </button>
        </div>
      )}

      {/* Continue learning banner */}
      {lastCourse && (
        <div
          className="bg-white rounded-2xl border border-[#E5E7EB] p-5 mb-6 flex items-center justify-between cursor-pointer hover:border-[#2563EB] hover:bg-[#F8FAFF] transition-colors"
          onClick={() => {
            localStorage.setItem("current_course_id", String(lastCourse.id));
            router.push("/modules");
          }}
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-[#EEF2FF] flex items-center justify-center text-2xl shrink-0">▶️</div>
            <div>
              <div className="text-xs text-[#6B7280] mb-0.5">Продолжить обучение</div>
              <div className="text-sm font-semibold text-[#111827]">{lastCourse.title}</div>
              {lastCourse.due_date && <div className="text-xs text-[#6B7280] mt-0.5">Срок: {lastCourse.due_date}</div>}
            </div>
          </div>
          <div className="text-[#9CA3AF] text-lg">›</div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        {/* Courses */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-[15px] font-semibold text-[#111827]">Мои курсы</h2>
            {courses.length > 3 && (
              <button onClick={() => router.push("/courses")} className="text-xs text-[#2563EB] hover:underline">Все</button>
            )}
          </div>
          {courses.length === 0 ? (
            <div className="bg-white rounded-2xl border border-[#E5E7EB] p-8 text-center text-[#6B7280] text-sm">
              <div className="text-3xl mb-2">📚</div>Курсов пока нет
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {courses.slice(0, 4).map((c) => (
                <button
                  key={c.id}
                  onClick={() => {
                    localStorage.setItem("current_course_id", String(c.id));
                    router.push("/modules");
                  }}
                  className="bg-white rounded-xl border border-[#E5E7EB] px-4 py-3 text-left hover:border-[#2563EB] hover:bg-[#EEF2FF] transition-colors flex items-center gap-3"
                >
                  <div className="w-8 h-8 rounded-lg bg-[#EEF2FF] flex items-center justify-center text-sm shrink-0">📖</div>
                  <div className="min-w-0">
                    <div className="text-sm font-semibold text-[#111827] truncate">{c.title}</div>
                    {c.due_date && <div className="text-xs text-[#6B7280]">Срок: {c.due_date}</div>}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Activity */}
        <div>
          <h2 className="text-[15px] font-semibold text-[#111827] mb-3">Последние действия</h2>
          {activity.length === 0 ? (
            <div className="bg-white rounded-2xl border border-[#E5E7EB] p-8 text-center text-[#6B7280] text-sm">
              <div className="text-3xl mb-2">📋</div>Активности пока нет
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {activity.slice(0, 5).map((a, i) => (
                <div key={i} className="bg-white rounded-xl border border-[#E5E7EB] px-4 py-3 flex items-start gap-3">
                  <div className="w-2 h-2 rounded-full bg-[#2563EB] mt-1.5 shrink-0" />
                  <div>
                    <div className="text-sm text-[#111827]">{a.action}</div>
                    <div className="text-xs text-[#9CA3AF] mt-0.5">{formatDateTime(a.created_at)}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
