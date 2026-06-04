"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { saveUser } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
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
      let res;
      try {
        res = await api.post("/auth/login", { username: username.trim(), password });
      } catch (err: unknown) {
        const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } };
        if (axiosErr?.response?.status === 404) {
          // Пользователь не найден — регистрируем
          res = await api.post("/auth/register", { username: username.trim(), password });
        } else if (axiosErr?.response?.status === 401) {
          setError("Неверный пароль");
          return;
        } else {
          throw err;
        }
      }
      saveUser(res.data);
      router.replace("/dashboard");
    } catch {
      setError("Ошибка входа. Попробуйте ещё раз.");
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

          {error && <p className="text-sm text-red-500">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white font-semibold py-3 rounded-[10px] transition-colors disabled:opacity-60"
          >
            {loading ? "Вход..." : "Войти"}
          </button>

          <p className="text-center text-xs text-[#9CA3AF]">Новый аккаунт создаётся автоматически при первом входе</p>
        </form>
      </div>
    </div>
  );
}
