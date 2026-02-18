"use client";

import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface MetricCardProps {
  icon: LucideIcon;
  label: string;
  value: string | number;
  color: string;
  sub?: string;
  trend?: "up" | "down" | "neutral";
}

export default function MetricCard({ icon: Icon, label, value, color, sub, trend }: MetricCardProps) {
  return (
    <div className="relative bg-bg-surface border border-bdr rounded-card p-5 overflow-hidden group hover:border-bdr-hover transition-colors">
      {/* Glow blob */}
      <div className={cn("absolute -top-6 -right-6 w-20 h-20 rounded-full blur-2xl opacity-20 group-hover:opacity-30 transition-opacity", color)} />

      <div className="relative">
        <div className="flex items-center gap-2 mb-3">
          <Icon size={16} className={cn("opacity-70", color.replace("bg-", "text-"))} />
          <span className="text-[11px] font-medium uppercase tracking-wider text-txt-muted">{label}</span>
        </div>
        <div className={cn("text-2xl font-bold", color.replace("bg-", "text-"))}>{value}</div>
        {sub && (
          <div className={cn(
            "text-xs mt-1.5",
            trend === "up" ? "text-accent-green" : trend === "down" ? "text-accent-red" : "text-txt-muted"
          )}>
            {trend === "up" && "↑ "}{trend === "down" && "↓ "}{sub}
          </div>
        )}
      </div>
    </div>
  );
}
