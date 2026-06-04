"use client";
import { useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import { ChatMessage } from "@/lib/types";

export default function MentorPage() {
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.get("/mentor/history").then((r) => setHistory(r.data ?? [])).catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history]);

  async function handleAsk(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || loading) return;
    const q = question.trim();
    setQuestion("");
    setLoading(true);
    setHistory((prev) => [...prev, { question: q, answer: "" }]);
    try {
      const courseId = localStorage.getItem("current_course_id");
      let courseData = null;
      if (courseId) {
        const r = await api.get(`/courses/${courseId}`);
        courseData = r.data;
      }
      const r = await api.post("/mentor/ask", { question: q, course_data: courseData });
      setHistory((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = { question: q, answer: r.data.answer };
        return updated;
      });
    } catch {
      setHistory((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = { question: q, answer: "Произошла ошибка. Попробуйте ещё раз." };
        return updated;
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] min-h-[500px]">
      {/* Hero */}
      <div className="rounded-2xl bg-gradient-to-br from-[#0F172A] to-[#1E293B] text-white p-8 mb-6">
        <h1 className="text-xl font-bold mb-1">💬 AI-наставник</h1>
        <p className="text-sm text-[#94A3B8]">Задайте любой вопрос по материалам курса</p>
      </div>

      {/* Chat */}
      <div className="flex-1 overflow-y-auto flex flex-col gap-4 pb-4">
        {history.length === 0 && (
          <div className="text-center text-sm text-[#6B7280] mt-10">
            <div className="text-3xl mb-2">🤖</div>
            Задайте первый вопрос наставнику
          </div>
        )}
        {history.map((msg, i) => (
          <div key={i} className="flex flex-col gap-2">
            <div className="bg-[#EEF2FF] border-l-[3px] border-[#2563EB] rounded-r-xl px-5 py-4 text-sm text-[#1E40AF] font-medium max-w-2xl">
              {msg.question}
            </div>
            {msg.answer ? (
              <div className="bg-white border border-[#E5E7EB] rounded-xl px-5 py-4 text-sm text-[#1F2937] leading-relaxed max-w-3xl whitespace-pre-wrap shadow-sm">
                {msg.answer}
              </div>
            ) : (
              <div className="bg-white border border-[#E5E7EB] rounded-xl px-5 py-4 text-sm text-[#9CA3AF] max-w-3xl">
                Думаю...
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleAsk} className="flex gap-3 mt-4">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Введите вопрос..."
          disabled={loading}
          className="flex-1 border border-[#E5E7EB] rounded-xl px-4 py-3 text-sm text-[#111827] bg-white focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/10 disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="bg-[#2563EB] text-white font-semibold px-6 py-3 rounded-xl hover:bg-[#1D4ED8] transition-colors disabled:opacity-50"
        >
          {loading ? "..." : "Спросить"}
        </button>
      </form>
    </div>
  );
}
