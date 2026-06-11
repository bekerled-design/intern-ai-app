export function formatDateTime(str: string) {
  const d = new Date(str);
  if (isNaN(d.getTime())) return str;
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  const isYesterday = d.toDateString() === yesterday.toDateString();
  const time = d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  if (isToday) return `Сегодня в ${time}`;
  if (isYesterday) return `Вчера в ${time}`;
  return d.toLocaleDateString("ru-RU", { day: "numeric", month: "long" }) + ` в ${time}`;
}
