"use client";

export default function LoadingSpinner({ text = "กำลังโหลด..." }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-3">
      <div className="w-8 h-8 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
      <span className="text-sm text-txt-muted">{text}</span>
    </div>
  );
}
