"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3, Users, Receipt, Settings2, Wallet,
  Wrench, ClipboardList, Gift, LogOut, Eye,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "@/lib/constants";
import { useAuth } from "@/lib/auth";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const ICON_MAP: Record<string, React.ComponentType<any>> = {
  BarChart3, Users, Receipt, Settings2, Wallet, Wrench, ClipboardList, Gift,
};

export default function Sidebar() {
  const pathname = usePathname();
  const { logout } = useAuth();

  return (
    <aside className="hidden lg:flex flex-col w-[240px] h-screen bg-bg-surface border-r border-bdr fixed left-0 top-0 z-30">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 h-16 border-b border-bdr">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center">
          <Eye size={18} className="text-white" />
        </div>
        <span className="text-sm font-semibold text-txt-primary tracking-wide">BigEye Admin</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = ICON_MAP[item.icon];
          const active = pathname?.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-btn text-sm transition-colors",
                active
                  ? "bg-accent-blue/10 text-accent-blue font-medium"
                  : "text-txt-secondary hover:bg-bg-hover hover:text-txt-primary"
              )}
            >
              {Icon && <Icon size={18} />}
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Logout */}
      <div className="p-3 border-t border-bdr">
        <button
          onClick={logout}
          className="flex items-center gap-3 px-3 py-2.5 rounded-btn text-sm text-txt-muted hover:bg-bg-hover hover:text-accent-red transition-colors w-full"
        >
          <LogOut size={18} />
          <span>ออกจากระบบ</span>
        </button>
      </div>
    </aside>
  );
}
