"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { getUser } from "@/lib/auth";
import { formatDateTime } from "@/lib/utils";

export default function ProfilePage() {
  const user = getUser();
  const [scores, setScores] = useState<number[]>([]);
  const [weakTopics, setWeakTopics] = useState<string[]>([]);
  const [activity, setActivity] = useState<{ action: string; created_at: string }[]>([]);
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [companyName, setCompanyName] = useState<string | null>(null);

  useEffect(() => {
    api.get("/tests/results").then((r) => setScores(r.data.scores ?? [])).catch(() => {});
    api.get("/tests/weak-topics").then((r) => {
      const topics = r.data.topics ?? [];
      setWeakTopics(topics);
      if (topics.length > 0) {
        setAnalysisLoading(true);
        api.get("/tests/analysis")
          .then((r) => setAnalysis(r.data.analysis ?? null))
          .catch(() => {})
          .finally(() => setAnalysisLoading(false));
      }
    }).catch(() => {});
    api.get("/activity").then((r) => setActivity(r.data ?? [])).catch(() => {});
    api.get("/company/me").then((r) => setCompanyName(r.data.name ?? null)).catch(() => {});
  }, []);

  const avgScore = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : null;
  const bestScore = scores.length ? Math.max(...scores) : null;
  const initial = user?.username?.[0]?.toUpperCase() ?? "U";
  const companyRole = user?.company_role;
  const isAdmin = companyRole === "owner" || companyRole === "admin" ||
                  user?.role === "admin" || user?.username?.toLowerCase() === "admin";
  const roleLabel = companyRole === "owner" ? "Владелец"
    : companyRole === "admin" ? "Администратор"
    : companyRole === "employee" ? "Сотрудник"
    : isAdmin ? "Администратор" : "Стажёр";

  return (
    <div>
      <h1 className="text-[22px] font-bold text-[#111827] mb-6">Профиль</h1>

      {/* User card */}
      <div className="bg-white rounded-2xl border border-[#E5E7EB] p-6 mb-6 flex items-center gap-5">
        <div className={`w-16 h-16 rounded-full flex items-center justify-center font-bold text-2xl shrink-0 ${isAdmin ? "bg-[#FEF3C7] text-[#D97706]" : "bg-[#EEF2FF] text-[#2563EB]"}`}>
          {initial}
        </div>
        <div>
          <div className="text-lg font-bold text-[#111827]">{user?.username}</div>
          <div className={`text-sm font-medium mt-0.5 ${isAdmin ? "text-[#D97706]" : "text-[#6B7280]"}`}>{roleLabel}</div>
          {companyName && (
            <div className="text-xs text-[#9CA3AF] mt-0.5">{companyName}</div>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-[14px] border border-[#E5E7EB] p-5 text-center">
          <div className="text-[26px] font-bold text-[#111827]">{scores.length}</div>
          <div className="text-xs text-[#6B7280] mt-1">Тестов пройдено</div>
        </div>
        <div className="bg-white rounded-[14px] border border-[#E5E7EB] p-5 text-center">
          <div className={`text-[26px] font-bold ${avgScore !== null ? (avgScore >= 70 ? "text-[#10B981]" : "text-[#EF4444]") : "text-[#111827]"}`}>
            {avgScore !== null ? `${avgScore}%` : "—"}
          </div>
          <div className="text-xs text-[#6B7280] mt-1">Средний балл</div>
        </div>
        <div className="bg-white rounded-[14px] border border-[#E5E7EB] p-5 text-center">
          <div className={`text-[26px] font-bold ${bestScore !== null ? (bestScore >= 70 ? "text-[#10B981]" : "text-[#EF4444]") : "text-[#111827]"}`}>
            {bestScore !== null ? `${bestScore}%` : "—"}
          </div>
          <div className="text-xs text-[#6B7280] mt-1">Лучший балл</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Weak topics + AI analysis */}
        <div className="flex flex-col gap-4">
          <div>
            <h2 className="text-[15px] font-semibold text-[#111827] mb-3">Темы для повторения</h2>
            <div className="bg-white rounded-2xl border border-[#E5E7EB] p-5">
              {weakTopics.length === 0 ? (
                <p className="text-sm text-[#6B7280]">Пока нет слабых тем</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {weakTopics.map((t) => (
                    <span key={t} className="bg-[#FEF3C7] text-[#92400E] text-xs font-medium px-3 py-1 rounded-full">{t}</span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {weakTopics.length > 0 && (
            <div>
              <h2 className="text-[15px] font-semibold text-[#111827] mb-3">🤖 AI-анализ ошибок</h2>
              <div className="bg-gradient-to-br from-[#EEF2FF] to-[#F8FAFF] rounded-2xl border border-[#C7D2FE] p-5">
                {analysisLoading ? (
                  <p className="text-sm text-[#6B7280]">Анализирую ошибки...</p>
                ) : analysis ? (
                  <p className="text-sm text-[#1E40AF] leading-relaxed whitespace-pre-wrap">{analysis}</p>
                ) : (
                  <p className="text-sm text-[#6B7280]">Не удалось загрузить анализ</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Activity */}
        <div>
          <h2 className="text-[15px] font-semibold text-[#111827] mb-3">Последние действия</h2>
          <div className="bg-white rounded-2xl border border-[#E5E7EB] p-5 flex flex-col gap-3">
            {activity.length === 0 ? (
              <p className="text-sm text-[#6B7280]">Активности пока нет</p>
            ) : (
              activity.map((a, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className="w-2 h-2 rounded-full bg-[#2563EB] mt-1.5 shrink-0" />
                  <div>
                    <div className="text-sm text-[#111827]">{a.action}</div>
                    <div className="text-xs text-[#9CA3AF] mt-0.5">{formatDateTime(a.created_at)}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
