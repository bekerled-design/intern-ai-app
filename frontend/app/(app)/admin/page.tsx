"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";

interface UserRow { id: number; username: string }

export default function AdminPage() {
  const router = useRouter();
  const [users, setUsers] = useState<UserRow[]>([]);
  const [selectedUser, setSelectedUser] = useState<UserRow | null>(null);
  const [weakTopics, setWeakTopics] = useState<string[]>([]);
  const [loadingTopics, setLoadingTopics] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [genDone, setGenDone] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/admin/users").then((r) => setUsers(r.data)).catch(() => {});
  }, []);

  async function selectUser(u: UserRow) {
    setSelectedUser(u);
    setWeakTopics([]);
    setGenDone(false);
    setError("");
    setLoadingTopics(true);
    try {
      const r = await api.get(`/admin/users/${u.id}/weak-topics`);
      setWeakTopics(r.data.topics ?? []);
    } catch {
      setError("Не удалось загрузить слабые темы");
    } finally {
      setLoadingTopics(false);
    }
  }

  async function handleGenerateRetraining() {
    if (!selectedUser) return;
    setGenerating(true);
    setError("");
    try {
      const r = await api.post(`/admin/users/${selectedUser.id}/retraining`, {});
      localStorage.setItem("current_course_id", String(r.data.course_id));
      setGenDone(true);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Ошибка генерации");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div>
      <h1 className="text-[22px] font-bold text-[#111827] mb-6">Администратор</h1>

      <div className="grid grid-cols-2 gap-6">
        {/* Users list */}
        <div>
          <h2 className="text-[15px] font-semibold text-[#111827] mb-3">
            Пользователи <span className="text-[#6B7280] font-normal text-xs">({users.length})</span>
          </h2>
          {users.length === 0 ? (
            <div className="bg-white rounded-2xl border border-[#E5E7EB] p-10 text-center text-sm text-[#6B7280]">
              <div className="text-3xl mb-2">👥</div>Нет пользователей
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {users.map((u) => {
                const isSelected = selectedUser?.id === u.id;
                return (
                  <button
                    key={u.id}
                    onClick={() => selectUser(u)}
                    className={`flex items-center gap-3 px-4 py-3 rounded-xl border text-left transition-colors ${
                      isSelected
                        ? "bg-[#EEF2FF] border-[#2563EB]"
                        : "bg-white border-[#E5E7EB] hover:bg-[#F9FAFB]"
                    }`}
                  >
                    <div className="w-8 h-8 rounded-full bg-[#2563EB] text-white flex items-center justify-center text-sm font-bold shrink-0">
                      {u.username[0]?.toUpperCase()}
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-[#111827]">{u.username}</div>
                      <div className="text-xs text-[#9CA3AF]">ID: {u.id}</div>
                    </div>
                    {isSelected && <div className="ml-auto text-[#2563EB] text-sm">✓</div>}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* User detail panel */}
        <div>
          {!selectedUser ? (
            <div className="bg-white rounded-2xl border border-[#E5E7EB] p-10 text-center text-sm text-[#6B7280]">
              <div className="text-3xl mb-2">👈</div>
              Выберите пользователя слева
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {/* User header */}
              <div className="bg-white rounded-2xl border border-[#E5E7EB] p-5">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-full bg-[#2563EB] text-white flex items-center justify-center font-bold">
                    {selectedUser.username[0]?.toUpperCase()}
                  </div>
                  <div>
                    <div className="text-sm font-bold text-[#111827]">{selectedUser.username}</div>
                    <div className="text-xs text-[#9CA3AF]">ID: {selectedUser.id}</div>
                  </div>
                </div>
                <button
                  onClick={() => {
                    localStorage.setItem("view_user_id", String(selectedUser.id));
                    localStorage.setItem("view_username", selectedUser.username);
                    router.push("/courses");
                  }}
                  className="text-sm text-[#2563EB] hover:underline font-medium"
                >
                  Просмотреть курсы →
                </button>
              </div>

              {/* Weak topics */}
              <div className="bg-white rounded-2xl border border-[#E5E7EB] p-5">
                <h3 className="text-sm font-semibold text-[#111827] mb-3">⚠️ Слабые темы</h3>
                {loadingTopics ? (
                  <div className="text-sm text-[#9CA3AF]">Загрузка...</div>
                ) : weakTopics.length === 0 ? (
                  <div className="text-sm text-[#6B7280]">Тестов ещё не проходил или ошибок нет</div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {weakTopics.map((t, i) => (
                      <span key={i} className="bg-[#FEF3C7] text-[#92400E] text-xs font-medium px-3 py-1 rounded-full">
                        {t}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Retraining */}
              <div className="bg-white rounded-2xl border border-[#E5E7EB] p-5">
                <h3 className="text-sm font-semibold text-[#111827] mb-1">🔄 Дополнительное обучение</h3>
                <p className="text-xs text-[#6B7280] mb-4">
                  ИИ создаст мини-курс по слабым темам стажёра и назначит его в его аккаунт
                </p>

                {error && <p className="text-sm text-red-500 mb-3">{error}</p>}

                {genDone ? (
                  <div className="text-sm text-[#10B981] font-medium">
                    ✓ Курс создан и назначен стажёру
                  </div>
                ) : (
                  <button
                    onClick={handleGenerateRetraining}
                    disabled={generating || weakTopics.length === 0}
                    className="bg-[#2563EB] text-white font-semibold px-5 py-2.5 rounded-[10px] hover:bg-[#1D4ED8] transition-colors disabled:opacity-50 text-sm"
                  >
                    {generating ? "Генерирую курс..." : "Создать доп. обучение"}
                  </button>
                )}

                {weakTopics.length === 0 && !loadingTopics && (
                  <p className="text-xs text-[#9CA3AF] mt-2">Нет слабых тем для генерации</p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
