"use client";

import { useEffect, useState, useCallback } from "react";
import { getAuditLogs } from "@/lib/api";
import { formatDateTime, cn } from "@/lib/utils";
import LoadingSpinner from "@/components/shared/LoadingSpinner";
import { Search, ChevronLeft, ChevronRight, ChevronDown, ChevronUp } from "lucide-react";

interface LogEntry {
  id: string; event_type: string; user_id: string; severity: string;
  details: Record<string, unknown>; created_at: string;
}

const SEVERITIES = ["", "INFO", "WARNING", "ERROR"];

function severityColor(s: string) {
  if (s === "ERROR") return "text-accent-red bg-accent-red/10 border-accent-red/20";
  if (s === "WARNING") return "text-accent-yellow bg-accent-yellow/10 border-accent-yellow/20";
  return "text-accent-blue bg-accent-blue/10 border-accent-blue/20";
}

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [severity, setSeverity] = useState("");
  const [search, setSearch] = useState("");
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getAuditLogs(severity, days, search, page) as { logs: LogEntry[]; total: number; pages: number };
      setLogs(res.logs); setTotal(res.total); setPages(res.pages);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [severity, days, search, page]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-bold text-txt-primary">บันทึกระบบ</h1>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex gap-1.5">
          {SEVERITIES.map((s) => (
            <button key={s} onClick={() => { setSeverity(s); setPage(1); }}
              className={cn("px-2.5 py-1.5 text-xs rounded-btn border transition-colors",
                severity === s ? "bg-accent-blue/10 text-accent-blue border-accent-blue/20" : "text-txt-muted border-bdr hover:bg-bg-hover"
              )}>
              {s || "ทั้งหมด"}
            </button>
          ))}
        </div>
        <select value={days} onChange={(e) => { setDays(Number(e.target.value)); setPage(1); }}
          className="px-2 py-1.5 bg-bg-input border border-bdr rounded-input text-xs text-txt-primary">
          <option value={1}>1 วัน</option><option value={7}>7 วัน</option><option value={30}>30 วัน</option><option value={90}>90 วัน</option>
        </select>
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-txt-muted" />
          <input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="ค้นหา event, user..."
            className="w-full pl-8 pr-3 py-1.5 bg-bg-input border border-bdr rounded-input text-xs text-txt-primary" />
        </div>
      </div>

      {loading ? <LoadingSpinner /> : (
        <>
          <div className="space-y-1.5">
            {logs.map((l) => (
              <div key={l.id} className="bg-bg-surface border border-bdr rounded-card overflow-hidden">
                <button onClick={() => setExpanded(expanded === l.id ? null : l.id)}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-bg-hover transition-colors">
                  <span className={cn("px-1.5 py-0.5 text-[10px] font-medium rounded border", severityColor(l.severity))}>{l.severity}</span>
                  <span className="text-xs text-txt-primary font-medium flex-1 truncate">{l.event_type}</span>
                  <span className="text-[10px] text-txt-muted font-mono">{l.user_id.slice(0, 12)}</span>
                  <span className="text-[10px] text-txt-muted">{formatDateTime(l.created_at)}</span>
                  {expanded === l.id ? <ChevronUp size={14} className="text-txt-muted" /> : <ChevronDown size={14} className="text-txt-muted" />}
                </button>
                {expanded === l.id && (
                  <div className="px-4 pb-3 border-t border-bdr/50">
                    <pre className="text-[11px] text-txt-secondary font-mono bg-bg-root rounded p-3 mt-2 overflow-x-auto max-h-60">
                      {JSON.stringify(l.details, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ))}
            {logs.length === 0 && <div className="text-center py-12 text-txt-muted text-sm">ไม่มีรายการ</div>}
          </div>

          <div className="flex items-center justify-between text-xs text-txt-muted">
            <span>{total} รายการ</span>
            <div className="flex items-center gap-2">
              <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page <= 1} className="p-1 disabled:opacity-30"><ChevronLeft size={16} /></button>
              <span>{page} / {pages}</span>
              <button onClick={() => setPage(Math.min(pages, page + 1))} disabled={page >= pages} className="p-1 disabled:opacity-30"><ChevronRight size={16} /></button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
