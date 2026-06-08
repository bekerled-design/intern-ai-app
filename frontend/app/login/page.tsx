"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { saveUser } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError("Введите логин и пароль");
      return;
    }
    setLoading(true);
    setError("");
    try {
      if (mode === "login") {
        const res = await api.post("/auth/login", { username: username.trim(), password });
        saveUser(res.data);
        router.replace("/dashboard");
      } else {
        const payload: Record<string, string> = { username: username.trim(), password };
        if (inviteCode.trim()) payload.invite_code = inviteCode.trim();
        const res = await api.post("/auth/register", payload);
        saveUser(res.data);
        router.replace("/dashboard");
      }
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } };
      const detail = axiosErr?.response?.data?.detail;
      if (axiosErr?.response?.status === 401) {
        setError("Неверный пароль");
      } else if (axiosErr?.response?.status === 404) {
        setError("Пользователь не найден");
      } else if (axiosErr?.response?.status === 400 && detail?.toLowerCase().includes("invite")) {
        setError("Неверный код приглашения. Проверьте код и попробуйте снова.");
      } else {
        setError(detail ?? "Ошибка. Попробуйте ещё раз.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F4F6FB]">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-[#2563EB] rounded-2xl flex items-center justify-center text-white text-3xl mx-auto mb-4">🎓</div>
          <h1 className="text-2xl font-bold text-[#111827]">Стажировка</h1>
          <p className="text-sm text-[#6B7280] mt-1">Платформа для обучения и развития стажёров</p>
        </div>

        {/* Mode toggle */}
        <div className="flex bg-[#F3F4F6] rounded-[12px] p-1 mb-4">
          <button
            type="button"
            onClick={() => { setMode("login"); setError(""); }}
            className={`flex-1 py-2 text-sm font-semibold rounded-[9px] transition-colors ${
              mode === "login" ? "bg-white text-[#111827] shadow-sm" : "text-[#6B7280]"
            }`}
          >
            Войти
          </button>
          <button
            type="button"
            onClick={() => { setMode("register"); setError(""); }}
            className={`flex-1 py-2 text-sm font-semibold rounded-[9px] transition-colors ${
              mode === "register" ? "bg-white text-[#111827] shadow-sm" : "text-[#6B7280]"
            }`}
          >
            Создать аккаунт
          </button>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-[#E5E7EB] shadow-sm p-8 flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium text-[#374151] mb-1">Логин</label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Введите логин"
              className="w-full border border-[#E5E7EB] rounded-[10px] px-3 py-3 text-sm text-[#111827] bg-white focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/10"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[#374151] mb-1">Пароль</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Введите пароль"
              className="w-full border border-[#E5E7EB] rounded-[10px] px-3 py-3 text-sm text-[#111827] bg-white focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/10"
            />
          </div>

          {mode === "register" && (
            <div>
              <label className="block text-sm font-medium text-[#374151] mb-1">
                Код приглашения компании{" "}
                <span className="text-[#9CA3AF] font-normal">(необязательно)</span>
              </label>
              <input
                value={inviteCode}
                onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
                placeholder="Например: ACME-7F3K"
                className="w-full border border-[#E5E7EB] rounded-[10px] px-3 py-3 text-sm text-[#111827] bg-white focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/10 font-mono tracking-widest"
              />
              <p className="text-xs text-[#9CA3AF] mt-1.5 leading-relaxed">
                {inviteCode.trim()
                  ? "Вы присоединитесь к существующей компании как сотрудник."
                  : "Оставьте пустым — будет создана новая компания, вы станете владельцем."}
              </p>
            </div>
          )}

          {error && <p className="text-sm text-red-500">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white font-semibold py-3 rounded-[10px] transition-colors disabled:opacity-60"
          >
            {loading
              ? mode === "login" ? "Вход..." : "Создание аккаунта..."
              : mode === "login" ? "Войти" : "Создать аккаунт"}
          </button>

          {mode === "login" && (
            <p className="text-center text-xs text-[#9CA3AF]">
              Нет аккаунта?{" "}
              <button
                type="button"
                onClick={() => { setMode("register"); setError(""); }}
                className="text-[#2563EB] font-medium hover:underline"
              >
                Создать
              </button>
            </p>
          )}
        </form>
      </div>
    </div>
  );
}
