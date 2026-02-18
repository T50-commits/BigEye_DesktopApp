"use client";

import { cn, statusBgColor } from "@/lib/utils";

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border", statusBgColor(status))}>
      {status}
    </span>
  );
}
