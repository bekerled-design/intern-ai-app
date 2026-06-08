"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { logout, getUser } from "@/lib/auth";
import api from "@/lib/api";

const NAV = [
  { icon: "🏠", label: "Главная",      href: "/dashboard",  needsCourse: false, adminOnly: false },
  { icon: "📚", label: "Модули",       href: "/modules",    needsCourse: true,  adminOnly: false },
  { icon: "📝", label: "Тест",         href: "/test",       needsCourse: true,  adminOnly: false },
  { icon: "💬", label: "AI-наставник", href: "/mentor",     needsCourse: false, adminOnly: false },
  { icon: "👤", label: "Профиль",      href: "/profile",    needsCourse: false, adminOnly: false },
  { icon: "📁", label: "Мои курсы",    href: "/courses",    needsCourse: false, adminOnly: false },
  { icon: "📄", label: "Материалы",    href: "/materials",  needsCourse: false, adminOnly: false },
  { icon: "⚙️", label: "Администратор",href: "/admin",      needsCourse: false, adminOnly: true  },
];

interface Notification { id: number; message: string }

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const user = getUser();
  const initial = user?.username?.[0]?.toUpperCase() ?? "U";
  const companyRole = user?.company_role;
  const isAdmin = companyRole === "owner" || companyRole === "admin" ||
                  user?.role === "admin" || user?.username?.toLowerCase() === "admin";
  const roleLabel = companyRole === "owner" ? "Владелец"
    : companyRole === "admin" ? "Администратор"
    : companyRole === "employee" ? "Сотрудник"
    : user?.role === "admin" ? "Администратор" : "Стажёр";
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [toast, setToast] = useState<string | null>(null);
  const [hasCourse, setHasCourse] = useState(false);

  useEffect(() => {
    setHasCourse(!!localStorage.getItem("current_course_id"));
  }, [pathname]);

  useEffect(() => {
    if (!user || isAdmin) return;
    api.get("/notifications").then((r) => {
      const notes: Notification[] = r.data ?? [];
      setNotifications(notes);
      if (notes.length > 0) {
        setToast(notes[0].message);
        setTimeout(() => setToast(null), 6000);
      }
    }).catch(() => {});
  }, []);

  async function dismissNotification(id: number) {
    await api.post(`/notifications/${id}/read`, {}).catch(() => {});
    setNotifications((prev) => prev.filter((n) => n.id !== id));
    setToast(null);
  }

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <>
      {toast && (
        <div className="fixed bottom-5 right-5 z-50 max-w-sm bg-[#1E3A8A] text-white text-sm rounded-2xl shadow-xl p-4 flex items-start gap-3 animate-in fade-in slide-in-from-bottom-2">
          <span className="text-lg shrink-0">🔔</span>
          <div className="flex-1">
            <div className="font-semibold mb-0.5">Новое обучение</div>
            <div className="text-[#BFDBFE] text-xs leading-relaxed">{toast}</div>
          </div>
          <button
            onClick={() => notifications[0] && dismissNotification(notifications[0].id)}
            className="text-[#93C5FD] hover:text-white transition-colors shrink-0 mt-0.5"
          >
            ✕
          </button>
        </div>
      )}
    <aside className="w-[260px] min-h-screen bg-white border-r border-[#E5E7EB] flex flex-col px-3 py-5 shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-3 px-2 pb-6">
        <div className="w-9 h-9 bg-[#2563EB] rounded-[9px] flex items-center justify-center text-white text-lg shrink-0">🎓</div>
        <span className="text-[17px] font-bold text-[#111827]">Стажировка</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 flex flex-col gap-0.5">
        {NAV.filter((item) => !item.adminOnly || isAdmin).map(({ icon, label, href, needsCourse }) => {
          const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
          const resolvedHref = needsCourse && !hasCourse ? "/courses" : href;
          const hasBadge = href === "/courses" && notifications.length > 0;
          const inner = (
            <>
              <span>{icon}</span>
              <span className="flex-1">{label}</span>
              {hasBadge && (
                <span className="w-5 h-5 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center shrink-0">
                  {notifications.length}
                </span>
              )}
            </>
          );
          return active ? (
            <div key={href} className="flex items-center gap-3 px-3 py-2.5 rounded-[10px] bg-[#EEF2FF] text-[#2563EB] font-semibold text-[14px]">
              {inner}
            </div>
          ) : (
            <Link key={href} href={resolvedHref} className="flex items-center gap-3 px-3 py-2.5 rounded-[10px] text-[#374151] text-[14px] font-medium hover:bg-[#F3F4F6] transition-colors">
              {inner}
            </Link>
          );
        })}
      </nav>

      {/* Divider */}
      <hr className="border-[#E5E7EB] my-4" />

      {/* User */}
      <div className="flex items-center gap-3 px-2 mb-3">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm shrink-0 ${isAdmin ? "bg-[#FEF3C7] text-[#D97706]" : "bg-[#EEF2FF] text-[#2563EB]"}`}>
          {initial}
        </div>
        <div>
          <div className="text-[13px] font-semibold text-[#111827]">{user?.username}</div>
          <div className="text-[11px] text-[#6B7280]">{roleLabel}</div>
        </div>
      </div>
      <button
        onClick={handleLogout}
        className="w-full text-[14px] text-[#374151] py-2 rounded-[10px] hover:bg-[#F3F4F6] transition-colors"
      >
        Выйти
      </button>
    </aside>
    </>
  );
}
