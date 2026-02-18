"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3, Users, Receipt, Settings2, Wallet,
  Wrench, ClipboardList, Gift, X, Eye, LogOut, Menu,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "@/lib/constants";
import { useAuth } from "@/lib/auth";
import { useState } from "react";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const ICON_MAP: Record<string, React.ComponentType<any>> = {
  BarChart3, Users, Receipt, Settings2, Wallet, Wrench, ClipboardList, Gift,
};

export default function MobileNav() {
  const pathname = usePathname();
  const { logout } = useAuth();
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Hamburger button */}
      <button
        onClick={() => setOpen(true)}
        className="lg:hidden fixed top-3 left-3 z-50 p-2 rounded-btn bg-bg-surface border border-bdr text-txt-secondary hover:text-txt-primary"
      >
        <Menu size={20} />
      </button>

      {/* Overlay */}
      {open && (
        <div className="lg:hidden fixed inset-0 z-50">
          <div className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-[260px] bg-bg-surface border-r border-bdr flex flex-col animate-in slide-in-from-left">
            {/* Header */}
            <div className="flex items-center justify-between px-5 h-14 border-b border-bdr">
              <div className="flex items-center gap-2">
                <Eye size={18} className="text-accent-blue" />
                <span className="text-sm font-semibold">BigEye Admin</span>
              </div>
              <button onClick={() => setOpen(false)} className="text-txt-muted hover:text-txt-primary">
                <X size={18} />
              </button>
            </div>

            {/* Nav */}
            <nav className="flex-1 py-3 px-3 space-y-1 overflow-y-auto">
              {NAV_ITEMS.map((item) => {
                const Icon = ICON_MAP[item.icon];
                const active = pathname?.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setOpen(false)}
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
                onClick={() => { logout(); setOpen(false); }}
                className="flex items-center gap-3 px-3 py-2.5 rounded-btn text-sm text-txt-muted hover:bg-bg-hover hover:text-accent-red w-full"
              >
                <LogOut size={18} />
                <span>ออกจากระบบ</span>
              </button>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
