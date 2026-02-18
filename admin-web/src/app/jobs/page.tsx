"use client";

import { useEffect, useState, useCallback } from "react";
import { getJobs, forceRefundJob, cleanupJobs } from "@/lib/api";
import { formatNumber, formatDateTime, cn } from "@/lib/utils";
import StatusBadge from "@/components/shared/StatusBadge";
import LoadingSpinner from "@/components/shared/LoadingSpinner";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface JobRow {
  id: string; job_token: string; user_id: string; user_name: string; user_email: string;
  mode: string; file_count: number;
  status: string; reserved_credits: number; actual_usage: number;
  success_count: number; failed_count: number; created_at: string;
}

const FILTERS = ["", "RESERVED", "COMPLETED", "EXPIRED", "REFUNDED"];

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getJobs(filter, page) as { jobs: JobRow[]; total: number; pages: number };
      setJobs(res.jobs); setTotal(res.total); setPages(res.pages);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [filter, page]);

  useEffect(() => { load(); }, [load]);

  const doRefund = async (id: string) => {
    if (!confirm("คืนเครดิตงานนี้?")) return;
    try {
      const res = await forceRefundJob(id) as { message: string };
      setMsg(res.message); load();
    } catch (e: unknown) { setMsg(e instanceof Error ? e.message : "Error"); }
  };

  const doCleanup = async () => {
    if (!confirm("คืนเครดิตงานค้างทั้งหมด?")) return;
    try {
      const res = await cleanupJobs() as { message: string };
      setMsg(res.message); load();
    } catch (e: unknown) { setMsg(e instanceof Error ? e.message : "Error"); }
  };

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-bold text-txt-primary">ตรวจสอบงาน</h1>
      {msg && <div className="text-xs text-accent-green bg-accent-green/10 border border-accent-green/20 rounded-btn px-3 py-2">{msg}</div>}

      <div className="flex items-center gap-2 flex-wrap">
        {FILTERS.map((f) => (
          <button key={f} onClick={() => { setFilter(f); setPage(1); }}
            className={cn("px-3 py-1.5 text-xs rounded-btn border transition-colors",
              filter === f ? "bg-accent-blue/10 text-accent-blue border-accent-blue/20" : "bg-bg-surface text-txt-muted border-bdr hover:bg-bg-hover"
            )}>
            {f || "ทั้งหมด"}
          </button>
        ))}
        <div className="ml-auto">
          <button onClick={doCleanup}
            className="px-3 py-1.5 text-xs rounded-btn border border-accent-orange/30 bg-accent-orange/10 text-accent-orange hover:bg-accent-orange/20 transition-colors">
            คืนเครดิตงานค้างทั้งหมด
          </button>
        </div>
      </div>

      {loading ? <LoadingSpinner /> : (
        <>
          <div className="bg-bg-surface border border-bdr rounded-card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-bdr text-txt-muted text-xs">
                  <th className="text-left px-4 py-3 font-medium">Token</th>
                  <th className="text-left px-4 py-3 font-medium">ผู้ใช้</th>
                  <th className="text-left px-4 py-3 font-medium">Mode</th>
                  <th className="text-right px-4 py-3 font-medium">ไฟล์</th>
                  <th className="text-right px-4 py-3 font-medium">เครดิต</th>
                  <th className="text-center px-4 py-3 font-medium">✓/✗</th>
                  <th className="text-center px-4 py-3 font-medium">สถานะ</th>
                  <th className="text-left px-4 py-3 font-medium">วันที่</th>
                  <th className="text-center px-4 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((j) => (
                  <tr key={j.id} className="border-b border-bdr/50 hover:bg-bg-hover transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-txt-secondary">{j.job_token.slice(0, 12)}...</td>
                    <td className="px-4 py-3 text-xs">
                      <div className="text-txt-secondary font-medium">{j.user_name || "—"}</div>
                      <div className="text-txt-muted text-[11px]">{j.user_email || j.user_id.slice(0, 12)}</div>
                    </td>
                    <td className="px-4 py-3 text-txt-secondary text-xs">{j.mode}</td>
                    <td className="px-4 py-3 text-right">{j.file_count}</td>
                    <td className="px-4 py-3 text-right text-accent-yellow">{formatNumber(j.reserved_credits)}</td>
                    <td className="px-4 py-3 text-center text-xs">
                      <span className="text-accent-green">{j.success_count}</span>
                      <span className="text-txt-muted">/</span>
                      <span className="text-accent-red">{j.failed_count}</span>
                    </td>
                    <td className="px-4 py-3 text-center"><StatusBadge status={j.status} /></td>
                    <td className="px-4 py-3 text-txt-muted text-xs">{formatDateTime(j.created_at)}</td>
                    <td className="px-4 py-3 text-center">
                      {(j.status === "RESERVED" || j.status === "PROCESSING") && (
                        <button onClick={() => doRefund(j.id)} className="px-2 py-1 text-[11px] bg-accent-red/10 text-accent-red border border-accent-red/20 rounded hover:bg-accent-red/20">คืนเครดิต</button>
                      )}
                    </td>
                  </tr>
                ))}
                {jobs.length === 0 && <tr><td colSpan={9} className="text-center py-8 text-txt-muted text-sm">ไม่มีรายการ</td></tr>}
              </tbody>
            </table>
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
