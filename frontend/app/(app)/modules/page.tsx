"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { CourseData } from "@/lib/types";

type Tab = "modules" | "task";

export default function ModulesPage() {
  const router = useRouter();
  const [course, setCourse] = useState<CourseData | null>(null);
  const [completed, setCompleted] = useState<number[]>([]);
  const [active, setActive] = useState<number | null>(null);
  const [courseId, setCourseId] = useState<number | null>(null);
  const [tab, setTab] = useState<Tab>("modules");

  useEffect(() => {
    const id = localStorage.getItem("current_course_id");
    if (!id) { router.push("/courses"); return; }
    const numId = Number(id);
    setCourseId(numId);
    api.get(`/courses/${numId}`).then((r) => setCourse(r.data)).catch(() => router.push("/courses"));
    api.get(`/courses/${numId}/progress`).then((r) => setCompleted(r.data.completed_modules ?? [])).catch(() => {});
  }, []);

  async function markDone(idx: number) {
    if (!courseId || completed.includes(idx)) return;
    await api.post(`/courses/${courseId}/progress`, { course_id: courseId, module_index: idx });
    setCompleted((prev) => [...prev, idx]);
  }

  if (!course) return <div className="text-[#6B7280] text-sm">Загрузка...</div>;

  const totalModules = course.modules.length;
  const doneCount = completed.length;
  const progressPct = totalModules ? Math.round((doneCount / totalModules) * 100) : 0;
  const allDone = doneCount === totalModules && totalModules > 0;

  return (
    <div>
      <h1 className="text-[22px] font-bold text-[#111827] mb-1">{course.course_title}</h1>
      <p className="text-sm text-[#6B7280] mb-4">{totalModules} модулей · {doneCount} завершено</p>

      {/* Progress bar */}
      <div className="bg-white rounded-xl border border-[#E5E7EB] p-4 mb-5 flex items-center gap-4">
        <div className="flex-1 bg-[#E5E7EB] rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all ${allDone ? "bg-[#10B981]" : "bg-[#2563EB]"}`}
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <span className={`text-sm font-semibold shrink-0 ${allDone ? "text-[#10B981]" : "text-[#111827]"}`}>
          {allDone ? "✓ Завершён" : `${progressPct}%`}
        </span>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-5 bg-[#F3F4F6] rounded-xl p-1 w-fit">
        <button
          onClick={() => setTab("modules")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === "modules" ? "bg-white text-[#111827] shadow-sm" : "text-[#6B7280] hover:text-[#111827]"
          }`}
        >
          📖 Модули
        </button>
        {course.practical_task && (
          <button
            onClick={() => setTab("task")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === "task" ? "bg-white text-[#111827] shadow-sm" : "text-[#6B7280] hover:text-[#111827]"
            }`}
          >
            🎯 Практическое задание
          </button>
        )}
      </div>

      {tab === "task" ? (
        <div className="rounded-2xl border-[1.5px] border-[#F59E0B] bg-gradient-to-br from-[#FFFBEB] to-[#FEF3C7] p-6 max-w-3xl">
          <h2 className="text-[15px] font-semibold text-[#111827] mb-4">🎯 Практическое задание</h2>
          <div className="text-sm text-[#374151] whitespace-pre-wrap leading-relaxed">{course.practical_task}</div>
        </div>
      ) : (
        <div className="flex gap-6">
          {/* Module list */}
          <div className="w-72 shrink-0 flex flex-col gap-2">
            {course.modules.map((m, i) => {
              const done = completed.includes(i);
              const isActive = active === i;
              return (
                <button
                  key={i}
                  onClick={() => setActive(isActive ? null : i)}
                  className={`flex items-center gap-3 px-3 py-3 rounded-xl border text-left transition-colors ${
                    isActive
                      ? "bg-[#EEF2FF] border-[#2563EB]"
                      : "bg-white border-[#E5E7EB] hover:bg-[#F9FAFB]"
                  }`}
                >
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs shrink-0 font-semibold ${
                    done ? "bg-[#D1FAE5] text-[#10B981]" : isActive ? "bg-[#DBEAFE] text-[#2563EB]" : "bg-[#F3F4F6] text-[#9CA3AF]"
                  }`}>
                    {done ? "✓" : i + 1}
                  </div>
                  <div className="text-sm font-medium text-[#111827] text-left leading-tight">{m.title}</div>
                </button>
              );
            })}

            <div className="mt-2 flex flex-col gap-2">
              <button
                onClick={() => router.push("/test")}
                className="bg-white border border-[#E5E7EB] rounded-xl px-3 py-3 text-sm font-medium text-[#374151] hover:bg-[#F3F4F6] transition-colors text-left flex items-center gap-3"
              >
                <span className="text-lg">📝</span> Пройти тест
              </button>
              <button
                onClick={() => router.push("/mentor")}
                className="bg-white border border-[#E5E7EB] rounded-xl px-3 py-3 text-sm font-medium text-[#374151] hover:bg-[#F3F4F6] transition-colors text-left flex items-center gap-3"
              >
                <span className="text-lg">💬</span> Спросить наставника
              </button>
            </div>
          </div>

          {/* Module content */}
          <div className="flex-1">
            {active === null ? (
              <div className="bg-white rounded-2xl border border-[#E5E7EB] p-10 text-center text-[#6B7280] text-sm">
                <div className="text-3xl mb-2">👈</div>
                Выберите модуль слева
              </div>
            ) : (
              <div className="bg-white rounded-2xl border border-[#E5E7EB] p-6">
                <h2 className="text-lg font-bold text-[#111827] mb-1">{course.modules[active].title}</h2>
                <p className="text-sm text-[#6B7280] mb-4">{course.modules[active].description}</p>
                <div className="prose prose-sm max-w-none text-[#1F2937] leading-relaxed whitespace-pre-wrap">
                  {course.modules[active].content}
                </div>
                {!completed.includes(active) && (
                  <button
                    onClick={() => markDone(active)}
                    className="mt-6 bg-[#2563EB] text-white font-semibold px-6 py-2.5 rounded-[10px] hover:bg-[#1D4ED8] transition-colors"
                  >
                    Отметить как завершённый
                  </button>
                )}
                {completed.includes(active) && (
                  <div className="mt-6 text-sm text-[#10B981] font-medium">✓ Модуль завершён</div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
