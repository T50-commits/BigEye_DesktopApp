import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(n: number): string {
  return n.toLocaleString("th-TH");
}

export function formatCurrency(n: number): string {
  return `฿${n.toLocaleString("th-TH", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
}

export function formatCredits(n: number): string {
  return `${n.toLocaleString("th-TH")} เครดิต`;
}

export function formatDate(iso: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("th-TH", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatDateTime(iso: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("th-TH", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function relativeTime(iso: string): string {
  if (!iso) return "—";
  const now = Date.now();
  const then = new Date(iso).getTime();
  const diff = now - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "เมื่อสักครู่";
  if (mins < 60) return `${mins} นาทีที่แล้ว`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} ชม.ที่แล้ว`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} วันที่แล้ว`;
  return formatDate(iso);
}

export function statusColor(status: string): string {
  const s = status.toLowerCase();
  if (["active", "verified", "completed", "success"].includes(s)) return "text-accent-green";
  if (["pending", "reserved", "processing"].includes(s)) return "text-accent-yellow";
  if (["suspended", "banned", "rejected", "failed", "expired"].includes(s)) return "text-accent-red";
  if (["draft", "paused"].includes(s)) return "text-txt-muted";
  return "text-txt-secondary";
}

export function statusBgColor(status: string): string {
  const s = status.toLowerCase();
  if (["active", "verified", "completed", "success"].includes(s)) return "bg-accent-green/10 text-accent-green border-accent-green/20";
  if (["pending", "reserved", "processing"].includes(s)) return "bg-accent-yellow/10 text-accent-yellow border-accent-yellow/20";
  if (["suspended", "banned", "rejected", "failed", "expired"].includes(s)) return "bg-accent-red/10 text-accent-red border-accent-red/20";
  if (["draft", "paused"].includes(s)) return "bg-txt-muted/10 text-txt-muted border-txt-muted/20";
  return "bg-txt-secondary/10 text-txt-secondary border-txt-secondary/20";
}
