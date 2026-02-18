export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api/v1";

export const COLORS = {
  blue: "#4f8cff",
  cyan: "#22d3ee",
  green: "#34d399",
  yellow: "#fbbf24",
  red: "#f87171",
  purple: "#a78bfa",
  pink: "#f472b6",
  orange: "#fb923c",
} as const;

export const NAV_ITEMS = [
  { label: "แดชบอร์ด", href: "/dashboard", icon: "BarChart3" },
  { label: "ผู้ใช้งาน", href: "/users", icon: "Users" },
  { label: "สลิปเติมเงิน", href: "/slips", icon: "Receipt" },
  { label: "ตรวจสอบงาน", href: "/jobs", icon: "Settings2" },
  { label: "การเงิน", href: "/finance", icon: "Wallet" },
  { label: "ตั้งค่า", href: "/settings", icon: "Wrench" },
  { label: "บันทึกระบบ", href: "/audit-logs", icon: "ClipboardList" },
  { label: "โปรโมชั่น", href: "/promotions", icon: "Gift" },
] as const;
