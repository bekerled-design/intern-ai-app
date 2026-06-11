"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { getUser } from "@/lib/auth";
import { Course } from "@/lib/types";

function formatDate(str: string | null) {
  if (!str) return null;
  const d = new Date(str);
  if (isNaN(d.getTime())) return str;
  return d.toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" });
}

export default function CoursesPage() {
  const router = useRouter();
  const user = getUser();
  const [courses, setCourses] = useState<Course[]>([]);
  const [viewUsername, setViewUsername] = useState<string | null>(null);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    if (!user) return;
    const viewId = localStorage.getItem("view_user_id");
    const viewName = localStorage.getItem("view_username");
    const targetId = viewId ? Number(viewId) : user.user_id;
    if (viewId && viewName) setViewUsername(viewName);
    api.get(`/users/${targetId}/courses`)
      .then((r) => setCourses(r.data))
      .catch(() => setLoadError("Не удалось загрузить курсы. Обновите страницу."));
  }, []);

  function openCourse(id: number) {
    localStorage.setItem("current_course_id", String(id));
    router.push("/modules");
  }

  async function handleDelete(e: React.MouseEvent, id: number) {
    e.stopPropagation();
    if (!confirm("Удалить курс? Это действие нельзя отменить.")) return;
    try {
      await api.delete(`/courses/${id}`);
      setCourses((prev) => prev.filter((c) => c.id !== id));
      if (localStorage.getItem("current_course_id") === String(id)) {
        localStorage.removeItem("current_course_id");
      }
    } catch {
      alert("Не удалось удалить курс");
    }
  }

  return (
    <div>
      {viewUsername && (
        <div className="flex items-center gap-2 mb-4 text-sm text-[#6B7280]">
          <button
            onClick={() => { localStorage.removeItem("view_user_id"); localStorage.removeItem("view_username"); router.push("/admin"); }}
            className="text-[#2563EB] hover:underline"
          >
            ← Назад в админку
          </button>
          <span>/ Курсы пользователя <span className="font-semibold text-[#111827]">{viewUsername}</span></span>
        </div>
      )}
      <h1 className="text-[22px] font-bold text-[#111827] mb-6">{viewUsername ? `Курсы: ${viewUsername}` : "Мои курсы"}</h1>

      {loadError && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600">
          {loadError}
        </div>
      )}

      {courses.length === 0 ? (
        <div className="bg-white rounded-2xl border border-[#E5E7EB] p-12 text-center text-[#6B7280] text-sm">
          <div className="text-4xl mb-3">📁</div>
          <div className="font-medium mb-2">Курсов пока нет</div>
          <p className="text-xs mb-5">Загрузите материалы и создайте первый курс</p>
          <button
            onClick={() => router.push("/materials")}
            className="bg-[#2563EB] text-white font-semibold px-5 py-2.5 rounded-[10px] hover:bg-[#1D4ED8] transition-colors text-sm"
          >
            Загрузить материалы
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {courses.map((c) => {
            const pct = c.total_modules > 0 ? Math.round((c.completed_modules / c.total_modules) * 100) : 0;
            const done = c.completed_modules === c.total_modules && c.total_modules > 0;
            return (
              <div key={c.id} className="relative group">
                <button
                  onClick={() => openCourse(c.id)}
                  className="w-full bg-white rounded-2xl border border-[#E5E7EB] p-5 text-left hover:border-[#2563EB] hover:shadow-md transition-all"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="text-2xl">📚</div>
                    {done && (
                      <span className="text-xs font-medium text-[#10B981] bg-[#D1FAE5] px-2 py-0.5 rounded-full">Завершён</span>
                    )}
                  </div>
                  <div className="text-[15px] font-semibold text-[#111827] group-hover:text-[#2563EB] transition-colors mb-1 leading-tight pr-6">{c.title}</div>
                  {c.due_date && (
                    <div className="text-xs text-[#9CA3AF] mb-3">Срок: {formatDate(c.due_date)}</div>
                  )}
                  {c.total_modules > 0 && (
                    <div className="mt-3">
                      <div className="flex justify-between text-xs text-[#6B7280] mb-1">
                        <span>Прогресс</span>
                        <span>{c.completed_modules} / {c.total_modules} модулей</span>
                      </div>
                      <div className="w-full bg-[#E5E7EB] rounded-full h-1.5">
                        <div
                          className={`h-1.5 rounded-full transition-all ${done ? "bg-[#10B981]" : "bg-[#2563EB]"}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  )}
                </button>
                {!viewUsername && (
                  <button
                    onClick={(e) => handleDelete(e, c.id)}
                    className="absolute top-3 right-3 w-7 h-7 flex items-center justify-center rounded-lg text-[#9CA3AF] hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all text-sm"
                    title="Удалить курс"
                  >
                    ✕
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
