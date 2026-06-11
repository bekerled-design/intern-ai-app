"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { Material } from "@/lib/types";

interface Job {
  job_id: number;
  status: "pending" | "running" | "done" | "error";
  course_id: number | null;
  progress_done: number;
  progress_total: number;
  error: string | null;
  status_message?: string | null;
}

interface Program {
  course_title: string;
  target_role: string;
  description: string;
  source_files: string[];
  source_topics: string[];
  reason: string;
  estimated_modules: number;
}

interface AnalysisResult {
  recommended_mode: "single_course" | "multiple_courses";
  warning: string | null;
  programs: Program[];
}

const AUDIO_VIDEO_EXT = ["mp4", "mp3", "wav", "m4a", "webm"];

const EXT_ICON: Record<string, string> = {
  pdf: "📄", docx: "📝", doc: "📝", xlsx: "📊", xls: "📊",
  csv: "📊", txt: "📃", mp3: "🎵", wav: "🎵", m4a: "🎵", mp4: "🎬", webm: "🎬",
};

function jobStatusLabel(job: Job): string {
  if (job.status === "pending") return "Подготовка...";
  if (job.status === "error") return `Ошибка: ${job.error ?? "неизвестная"}`;
  if (job.status === "done") return "Курс создан!";
  // Multi-course generation reports "курс N из M" via status_message
  // (fallback на error — для бэкенда старой версии)
  if (job.status === "running" && (job.status_message || job.error)) {
    return job.status_message ?? job.error ?? "";
  }
  if (job.progress_total > 0) {
    const current = Math.min(job.progress_done + 1, job.progress_total);
    return `Обрабатываю часть ${current} из ${job.progress_total}...`;
  }
  return "Генерирую курс...";
}

export default function MaterialsPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [materials, setMaterials] = useState<Material[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");

  // Analysis state
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);

  // Redirect on modules only if generation started here
  const startedHereRef = useRef(false);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback((jobId: number) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const r = await api.get(`/courses/generate-job/${jobId}`);
        const updated: Job = r.data;
        setJob(updated);
        if (updated.status === "done") {
          stopPolling();
          if (updated.course_id && startedHereRef.current) {
            localStorage.setItem("current_course_id", String(updated.course_id));
            startedHereRef.current = false;
            setTimeout(() => router.push("/modules"), 800);
          }
        } else if (updated.status === "error") {
          stopPolling();
          setError(updated.error ?? "Ошибка генерации");
        }
      } catch {
        stopPolling();
      }
    }, 3000);
  }, [router, stopPolling]);

  useEffect(() => {
    loadMaterials();
    api.get("/courses/active-job").then((r) => {
      const activeJob: Job | null = r.data.job;
      if (!activeJob) return;
      if (activeJob.status === "pending" || activeJob.status === "running") {
        setJob(activeJob);
        startPolling(activeJob.job_id);
      }
    }).catch(() => {});
    return () => stopPolling();
  }, []);

  async function loadMaterials() {
    try {
      const r = await api.get("/materials");
      setMaterials(r.data);
    } catch {
      setMaterials([]);
    }
  }

  async function handleUpload(files: FileList | null) {
    if (!files || files.length === 0) return;
    setUploading(true);
    setError("");
    setAnalysis(null); // сбрасываем анализ при новой загрузке
    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
        const isMedia = AUDIO_VIDEO_EXT.includes(ext);
        setUploadStatus(
          isMedia
            ? `Транскрибирую ${file.name} (это займёт минуту)...`
            : `Загружаю ${i + 1} из ${files.length}: ${file.name}`
        );
        const fd = new FormData();
        fd.append("file", file);
        await api.post("/materials/upload", fd);
      }
      setUploadStatus("Готово!");
      await loadMaterials();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки файла");
      setUploadStatus("");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function handleDelete(name: string) {
    try {
      await api.delete(`/materials/${encodeURIComponent(name)}`);
      setAnalysis(null);
      await loadMaterials();
    } catch {
      setError("Ошибка удаления файла");
    }
  }

  async function handleAnalyze() {
    setError("");
    setAnalysis(null);
    setAnalyzing(true);
    try {
      const r = await api.post("/courses/analyze-materials");
      setAnalysis(r.data);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Ошибка анализа материалов");
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleGenerateSingle() {
    setError("");
    try {
      const r = await api.post("/courses/generate-job");
      const newJob: Job = {
        job_id: r.data.job_id,
        status: "pending",
        course_id: null,
        progress_done: 0,
        progress_total: 0,
        error: null,
      };
      startedHereRef.current = true;
      setJob(newJob);
      startPolling(newJob.job_id);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Не удалось запустить генерацию");
    }
  }

  async function handleGenerateMulti(programs: Program[]) {
    setError("");
    try {
      const r = await api.post("/courses/generate-multi", { programs });
      const newJob: Job = {
        job_id: r.data.job_id,
        status: "pending",
        course_id: null,
        progress_done: 0,
        progress_total: 0,
        error: null,
      };
      startedHereRef.current = true;
      setJob(newJob);
      startPolling(newJob.job_id);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Не удалось запустить генерацию");
    }
  }

  const isGenerating = job !== null && (job.status === "pending" || job.status === "running");
  const progressPct = job && job.progress_total > 0
    ? Math.round((Math.min(job.progress_done + 1, job.progress_total) / job.progress_total) * 100)
    : 0;

  return (
    <div>
      <h1 className="text-[22px] font-bold text-[#111827] mb-2">Материалы компании</h1>
      <p className="text-sm text-[#6B7280] mb-6 max-w-lg">
        Загрузите внутренние документы, регламенты или инструкции. ИИ проанализирует их и создаст персональный курс обучения.
      </p>

      {/* Upload zone */}
      <div className="mb-6">
        <h2 className="text-[15px] font-semibold text-[#111827] mb-3">Загрузить файлы</h2>

        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".txt,.csv,.xlsx,.docx,.pdf,.mp4,.mp3,.wav,.m4a,.webm"
          style={{ display: "none" }}
          onChange={(e) => handleUpload(e.target.files)}
        />

        <div
          className="border-2 border-dashed border-[#C7D2FE] rounded-xl p-8 text-center bg-white hover:border-[#2563EB] hover:bg-[#F8FAFF] transition-colors"
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); handleUpload(e.dataTransfer.files); }}
        >
          <div className="text-[#6B7280] text-sm mb-4">Перетащите файлы сюда или нажмите кнопку</div>
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            className="bg-[#2563EB] text-white text-sm font-semibold px-6 py-2.5 rounded-[10px] hover:bg-[#1D4ED8] transition-colors disabled:opacity-60"
          >
            {uploading ? "Загрузка..." : "Выбрать файлы"}
          </button>
          {uploading && uploadStatus && (
            <div className="mt-3 text-sm text-[#374151]">{uploadStatus}</div>
          )}
        </div>

        {error && <p className="text-sm text-red-500 mt-3">{error}</p>}
      </div>

      {/* Generation block */}
      {materials.length > 0 && !isGenerating && job?.status !== "done" && (
        <div className="bg-white rounded-2xl border border-[#E5E7EB] p-6 mb-6">
          <h2 className="text-[15px] font-semibold text-[#111827] mb-2">Создать курс из материалов</h2>
          <p className="text-sm text-[#6B7280] mb-4">
            ИИ проанализирует загруженные документы и предложит план курсов. Вы сможете выбрать режим генерации.
          </p>

          {/* Step 1: Analyze */}
          {!analysis && (
            <button
              type="button"
              onClick={handleAnalyze}
              disabled={analyzing}
              className="bg-[#2563EB] text-white font-semibold px-6 py-2.5 rounded-[10px] hover:bg-[#1D4ED8] transition-colors disabled:opacity-60 flex items-center gap-2"
            >
              {analyzing ? (
                <>
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin inline-block" />
                  Анализирую материалы...
                </>
              ) : "Анализировать материалы"}
            </button>
          )}

          {/* Step 2: Analysis result */}
          {analysis && (
            <div>
              {/* Warning badge */}
              {analysis.warning && (
                <div className="flex items-start gap-2 mb-4 bg-[#FFFBEB] border border-[#F59E0B] rounded-xl px-4 py-3 text-sm text-[#92400E]">
                  <span className="shrink-0 mt-0.5">⚠️</span>
                  <span>{analysis.warning}</span>
                </div>
              )}

              <div className="flex items-center gap-2 mb-4">
                <span className="text-sm font-semibold text-[#111827]">
                  {analysis.recommended_mode === "multiple_courses"
                    ? `Найдено ${analysis.programs.length} учебных программ`
                    : "Рекомендуется один курс"}
                </span>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                  analysis.recommended_mode === "multiple_courses"
                    ? "bg-[#EEF2FF] text-[#2563EB]"
                    : "bg-[#F0FDF4] text-[#10B981]"
                }`}>
                  {analysis.recommended_mode === "multiple_courses" ? "Несколько курсов" : "Один курс"}
                </span>
              </div>

              {/* Program cards */}
              <div className="flex flex-col gap-3 mb-5">
                {analysis.programs.map((p, i) => (
                  <div key={i} className="border border-[#E5E7EB] rounded-xl p-4 bg-[#F9FAFB]">
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-[#9CA3AF] uppercase tracking-wide">
                          Курс {i + 1}
                        </span>
                        {p.estimated_modules > 0 && (
                          <span className="text-xs text-[#6B7280]">~{p.estimated_modules} модулей</span>
                        )}
                      </div>
                      {p.target_role && (
                        <span className="text-xs bg-[#EEF2FF] text-[#2563EB] font-medium px-2 py-0.5 rounded-full shrink-0">
                          {p.target_role}
                        </span>
                      )}
                    </div>
                    <div className="text-[15px] font-semibold text-[#111827] mb-1">{p.course_title}</div>
                    <div className="text-sm text-[#374151] mb-2">{p.description}</div>
                    {p.source_files.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {p.source_files.map((f, fi) => (
                          <span key={fi} className="text-[11px] bg-white border border-[#E5E7EB] text-[#6B7280] px-2 py-0.5 rounded-full">
                            {EXT_ICON[f.split(".").pop()?.toLowerCase() ?? ""] ?? "📄"} {f}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Action buttons */}
              <div className="flex flex-wrap gap-3">
                {analysis.recommended_mode === "multiple_courses" ? (
                  <>
                    <button
                      type="button"
                      onClick={() => handleGenerateMulti(analysis.programs)}
                      className="bg-[#2563EB] text-white font-semibold px-6 py-2.5 rounded-[10px] hover:bg-[#1D4ED8] transition-colors text-sm"
                    >
                      Создать отдельные курсы ({analysis.programs.length})
                    </button>
                    <button
                      type="button"
                      onClick={handleGenerateSingle}
                      className="bg-white border border-[#E5E7EB] text-[#374151] font-medium px-5 py-2.5 rounded-[10px] hover:bg-[#F3F4F6] transition-colors text-sm"
                    >
                      Создать один общий курс
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={handleGenerateSingle}
                      className="bg-[#2563EB] text-white font-semibold px-6 py-2.5 rounded-[10px] hover:bg-[#1D4ED8] transition-colors text-sm"
                    >
                      Создать курс
                    </button>
                    {analysis.programs.length > 1 && (
                      <button
                        type="button"
                        onClick={() => handleGenerateMulti(analysis.programs)}
                        className="bg-white border border-[#E5E7EB] text-[#374151] font-medium px-5 py-2.5 rounded-[10px] hover:bg-[#F3F4F6] transition-colors text-sm"
                      >
                        Создать отдельные курсы ({analysis.programs.length})
                      </button>
                    )}
                  </>
                )}
                <button
                  type="button"
                  onClick={() => setAnalysis(null)}
                  className="text-sm text-[#9CA3AF] hover:text-[#374151] px-3 py-2.5 transition-colors"
                >
                  Повторить анализ
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Generation progress */}
      {(isGenerating || job?.status === "done") && (
        <div className="bg-white rounded-2xl border border-[#E5E7EB] p-6 mb-6">
          <h2 className="text-[15px] font-semibold text-[#111827] mb-3">Генерация курса</h2>

          {isGenerating && (
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-3 h-3 rounded-full bg-[#2563EB] animate-pulse shrink-0" />
                <span className="text-sm text-[#374151]">{job ? jobStatusLabel(job) : ""}</span>
              </div>
              {job && job.progress_total > 0 && (
                <div className="w-full bg-[#E5E7EB] rounded-full h-2">
                  <div
                    className="bg-[#2563EB] h-2 rounded-full transition-all duration-500"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
              )}
              <p className="text-xs text-[#9CA3AF] mt-2">
                Можете закрыть страницу — генерация продолжится в фоне
              </p>
            </div>
          )}

          {job?.status === "done" && (
            <div className="flex items-center gap-2 text-sm text-[#10B981] font-medium">
              <span>✓</span> Курс создан! Переходим...
            </div>
          )}
        </div>
      )}

      {/* Files list */}
      <div>
        <h2 className="text-[15px] font-semibold text-[#111827] mb-3">
          Загруженные файлы
          {materials.length > 0 && <span className="text-[#6B7280] font-normal text-xs ml-2">({materials.length})</span>}
        </h2>
        {materials.length === 0 ? (
          <div className="bg-white rounded-2xl border border-[#E5E7EB] p-10 text-center text-[#6B7280] text-sm">
            <div className="text-3xl mb-2">📄</div>Файлы не загружены
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {materials.map((m) => {
              const ext = m.file_name.split(".").pop()?.toLowerCase() ?? "";
              return (
                <div key={m.file_name} className="bg-white border border-[#E5E7EB] rounded-xl px-4 py-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{EXT_ICON[ext] ?? "📄"}</span>
                    <div>
                      <div className="text-sm font-semibold text-[#111827]">{m.file_name}</div>
                      <div className="text-xs text-[#10B981]">✓ Загружен и обработан</div>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDelete(m.file_name)}
                    disabled={isGenerating}
                    className="text-sm text-[#6B7280] hover:text-red-500 transition-colors px-3 py-1 rounded-lg hover:bg-red-50 disabled:opacity-40"
                  >
                    Удалить
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
