"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { getUser } from "@/lib/auth";

interface UserRow { id: number; username: string; role?: string }
interface OpRow { operation: string; calls: number; tokens: number; cost: number }
interface UserCostRow { username: string; user_id: number; calls: number; tokens: number; cost: number }
interface UsageSummary {
  total_tokens: number;
  total_estimated_cost_usd: number;
  by_operation: OpRow[];
  by_user: UserCostRow[];
}
interface CourseRow { id: number; title: string }
interface AssignmentMember { user_id: number; username: string; role: string; assigned: boolean }

export default function AdminPage() {
  const router = useRouter();
  const user = getUser();
  const companyRole = user?.company_role;
  const [users, setUsers] = useState<UserRow[]>([]);
  const [selectedUser, setSelectedUser] = useState<UserRow | null>(null);
  const [weakTopics, setWeakTopics] = useState<string[]>([]);
  const [loadingTopics, setLoadingTopics] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [genDone, setGenDone] = useState(false);
  const [error, setError] = useState("");
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [inviteCode, setInviteCode] = useState<string | null>(null);
  const [inviteCopied, setInviteCopied] = useState(false);
  const [inviteRegenerating, setInviteRegenerating] = useState(false);

  // Assignments state
  const [courses, setCourses] = useState<CourseRow[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<CourseRow | null>(null);
  const [assignMembers, setAssignMembers] = useState<AssignmentMember[]>([]);
  const [assignLoading, setAssignLoading] = useState(false);
  const [assignSaving, setAssignSaving] = useState(false);
  const [assignDraft, setAssignDraft] = useState<Record<number, boolean>>({});

  useEffect(() => {
    api.get("/admin/users").then((r) => setUsers(r.data)).catch(() => {});
    api.get("/admin/usage").then((r) => setUsage(r.data)).catch(() => {});
    api.get("/company/me").then((r) => {
      if (r.data.invite_code) setInviteCode(r.data.invite_code);
      if (r.data.company_id) {
        // Загружаем курсы компании через текущего пользователя
        api.get(`/users/${user?.user_id}/courses`).then((cr) => setCourses(cr.data)).catch(() => {});
      }
    }).catch(() => {});
  }, []);

  async function handleSelectCourse(course: CourseRow) {
    setSelectedCourse(course);
    setAssignDraft({});
    setAssignLoading(true);
    try {
      const r = await api.get(`/courses/${course.id}/assignments`);
      const members: AssignmentMember[] = r.data;
      setAssignMembers(members);
      const draft: Record<number, boolean> = {};
      members.forEach((m) => { draft[m.user_id] = m.assigned; });
      setAssignDraft(draft);
    } catch {
      setAssignMembers([]);
    } finally {
      setAssignLoading(false);
    }
  }

  async function handleSaveAssignments() {
    if (!selectedCourse) return;
    setAssignSaving(true);
    try {
      const toAssign = assignMembers.filter((m) => assignDraft[m.user_id] && !m.assigned).map((m) => m.user_id);
      const toUnassign = assignMembers.filter((m) => !assignDraft[m.user_id] && m.assigned).map((m) => m.user_id);

      if (toAssign.length > 0) {
        await api.post(`/courses/${selectedCourse.id}/assignments`, { user_ids: toAssign });
      }
      for (const uid of toUnassign) {
        await api.delete(`/courses/${selectedCourse.id}/assignments/${uid}`);
      }
      // Обновляем актуальное состояние
      await handleSelectCourse(selectedCourse);
    } catch {
      // silent
    } finally {
      setAssignSaving(false);
    }
  }

  async function handleCopyCode() {
    if (!inviteCode) return;
    await navigator.clipboard.writeText(inviteCode).catch(() => {});
    setInviteCopied(true);
    setTimeout(() => setInviteCopied(false), 2000);
  }

  async function handleRegenerateCode() {
    setInviteRegenerating(true);
    try {
      const r = await api.post("/company/invite-code/regenerate", {});
      setInviteCode(r.data.invite_code);
    } catch {
      // silent
    } finally {
      setInviteRegenerating(false);
    }
  }

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

  const isOwnerOrAdmin = companyRole === "owner" || companyRole === "admin";

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
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-semibold text-[#111827]">{u.username}</div>
                      <div className="text-xs text-[#9CA3AF]">ID: {u.id}</div>
                    </div>
                    {u.role && (
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0 ${
                        u.role === "owner" ? "bg-[#FEF3C7] text-[#92400E]" :
                        u.role === "admin" ? "bg-[#EEF2FF] text-[#2563EB]" :
                        "bg-[#F3F4F6] text-[#6B7280]"
                      }`}>
                        {u.role === "owner" ? "Владелец" : u.role === "admin" ? "Админ" : "Сотрудник"}
                      </span>
                    )}
                    {isSelected && <div className="ml-1 text-[#2563EB] text-sm">✓</div>}
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

      {/* Course assignments — owner/admin only */}
      {isOwnerOrAdmin && (
        <div className="mt-8">
          <h2 className="text-[15px] font-semibold text-[#111827] mb-3">Назначение курсов</h2>
          <div className="bg-white rounded-2xl border border-[#E5E7EB] p-6">
            {courses.length === 0 ? (
              <div className="text-sm text-[#9CA3AF]">Нет созданных курсов</div>
            ) : (
              <div className="flex gap-6">
                {/* Course list */}
                <div className="w-64 shrink-0">
                  <div className="text-xs font-semibold text-[#6B7280] uppercase tracking-wide mb-2">Курс</div>
                  <div className="flex flex-col gap-1">
                    {courses.map((c) => (
                      <button
                        key={c.id}
                        onClick={() => handleSelectCourse(c)}
                        className={`text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                          selectedCourse?.id === c.id
                            ? "bg-[#EEF2FF] text-[#2563EB] font-semibold"
                            : "text-[#374151] hover:bg-[#F3F4F6]"
                        }`}
                      >
                        {c.title}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Members checklist */}
                <div className="flex-1 min-w-0">
                  {!selectedCourse ? (
                    <div className="text-sm text-[#9CA3AF] pt-6">Выберите курс слева</div>
                  ) : assignLoading ? (
                    <div className="text-sm text-[#9CA3AF]">Загрузка...</div>
                  ) : (
                    <>
                      <div className="text-xs font-semibold text-[#6B7280] uppercase tracking-wide mb-2">
                        Сотрудники
                      </div>
                      <div className="flex flex-col gap-2 mb-4">
                        {assignMembers.length === 0 ? (
                          <div className="text-sm text-[#9CA3AF]">Нет сотрудников в компании</div>
                        ) : (
                          assignMembers.map((m) => (
                            <label key={m.user_id} className="flex items-center gap-3 cursor-pointer group">
                              <input
                                type="checkbox"
                                checked={assignDraft[m.user_id] ?? false}
                                onChange={(e) => setAssignDraft((prev) => ({ ...prev, [m.user_id]: e.target.checked }))}
                                className="w-4 h-4 rounded border-[#D1D5DB] text-[#2563EB] accent-[#2563EB]"
                              />
                              <span className="text-sm text-[#111827]">{m.username}</span>
                              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                                m.role === "owner" ? "bg-[#FEF3C7] text-[#92400E]" :
                                m.role === "admin" ? "bg-[#EEF2FF] text-[#2563EB]" :
                                "bg-[#F3F4F6] text-[#6B7280]"
                              }`}>
                                {m.role === "owner" ? "Владелец" : m.role === "admin" ? "Админ" : "Сотрудник"}
                              </span>
                            </label>
                          ))
                        )}
                      </div>
                      <button
                        onClick={handleSaveAssignments}
                        disabled={assignSaving}
                        className="bg-[#2563EB] text-white text-sm font-semibold px-5 py-2 rounded-[10px] hover:bg-[#1D4ED8] transition-colors disabled:opacity-60"
                      >
                        {assignSaving ? "Сохраняю..." : "Сохранить назначения"}
                      </button>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Invite block — owner/admin only */}
      {isOwnerOrAdmin && (
        <div className="mt-8">
          <h2 className="text-[15px] font-semibold text-[#111827] mb-3">Приглашение сотрудников</h2>
          <div className="bg-white rounded-2xl border border-[#E5E7EB] p-6">
            <p className="text-xs text-[#6B7280] mb-4">
              Передайте этот код сотруднику. При регистрации он введёт код и автоматически попадёт в вашу компанию.
            </p>
            {inviteCode ? (
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex-1 bg-[#F3F4F6] rounded-[10px] px-4 py-3 font-mono text-lg font-bold text-[#111827] tracking-widest text-center select-all">
                    {inviteCode}
                  </div>
                  <button
                    onClick={handleCopyCode}
                    className="px-4 py-3 bg-[#2563EB] text-white text-sm font-semibold rounded-[10px] hover:bg-[#1D4ED8] transition-colors whitespace-nowrap"
                  >
                    {inviteCopied ? "Скопировано!" : "Скопировать"}
                  </button>
                </div>
                <button
                  onClick={handleRegenerateCode}
                  disabled={inviteRegenerating}
                  className="text-xs text-[#6B7280] hover:text-[#374151] transition-colors text-left disabled:opacity-50"
                >
                  {inviteRegenerating ? "Генерирую новый код..." : "Сгенерировать новый код (старый перестанет работать)"}
                </button>
              </div>
            ) : (
              <div className="text-sm text-[#9CA3AF]">Загрузка кода...</div>
            )}
          </div>
        </div>
      )}

      {/* API Usage */}
      {usage && (
        <div className="mt-8">
          <h2 className="text-[15px] font-semibold text-[#111827] mb-3">Расходы API</h2>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="bg-white rounded-2xl border border-[#E5E7EB] p-5">
              <div className="text-xs text-[#6B7280] mb-1">Примерная стоимость</div>
              <div className="text-2xl font-bold text-[#111827]">${usage.total_estimated_cost_usd.toFixed(4)}</div>
              <div className="text-xs text-[#9CA3AF] mt-1">{usage.total_tokens.toLocaleString()} токенов всего</div>
            </div>
            <div className="bg-white rounded-2xl border border-[#E5E7EB] p-5">
              <div className="text-xs text-[#6B7280] mb-2">По операциям</div>
              {usage.by_operation.length === 0 ? (
                <div className="text-sm text-[#9CA3AF]">Нет данных</div>
              ) : (
                <div className="flex flex-col gap-1">
                  {usage.by_operation.map((op) => (
                    <div key={op.operation} className="flex justify-between text-sm">
                      <span className="text-[#374151]">{op.operation}</span>
                      <span className="text-[#6B7280]">${op.cost.toFixed(4)} ({op.calls} вызовов)</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
          {usage.by_user.length > 0 && (
            <div className="bg-white rounded-2xl border border-[#E5E7EB] p-5">
              <div className="text-xs text-[#6B7280] mb-2">Топ пользователей по расходу</div>
              <div className="flex flex-col gap-1">
                {usage.by_user.map((u) => (
                  <div key={u.user_id} className="flex justify-between text-sm">
                    <span className="text-[#374151]">{u.username}</span>
                    <span className="text-[#6B7280]">${u.cost.toFixed(4)} · {u.tokens.toLocaleString()} токенов</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
