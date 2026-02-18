"use client";

import { useEffect, useState, useCallback } from "react";
import { getSlips, approveSlip, rejectSlip } from "@/lib/api";
import { formatNumber, formatDateTime, cn } from "@/lib/utils";
import StatusBadge from "@/components/shared/StatusBadge";
import LoadingSpinner from "@/components/shared/LoadingSpinner";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface SlipRow {
  id: string; user_id: string; status: string; amount_detected: number | null;
  amount_credited: number | null; bank_ref: string; verification_method: string;
  reject_reason: string; created_at: string; verified_at: string;
}

const FILTERS = ["", "PENDING", "VERIFIED", "REJECTED"];

export default function SlipsPage() {
  const [slips, setSlips] = useState<SlipRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getSlips(filter, page) as { slips: SlipRow[]; total: number; pages: number };
      setSlips(res.slips); setTotal(res.total); setPages(res.pages);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [filter, page]);

  useEffect(() => { load(); }, [load]);

  const doApprove = async (id: string) => {
    const amt = prompt("จำนวนเครดิตที่จะเพิ่ม:");
    if (!amt) return;
    try {
      const res = await approveSlip(id, Number(amt)) as { message: string };
      setActionMsg(res.message); load();
    } catch (e: unknown) { setActionMsg(e instanceof Error ? e.message : "Error"); }
  };

  const doReject = async (id: string) => {
    const reason = prompt("เหตุผลที่ปฏิเสธ:");
    try {
      const res = await rejectSlip(id, reason || "") as { message: string };
      setActionMsg(res.message); load();
    } catch (e: unknown) { setActionMsg(e instanceof Error ? e.message : "Error"); }
  };

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-bold text-txt-primary">สลิปเติมเงิน</h1>

      {actionMsg && <div className="text-xs text-accent-green bg-accent-green/10 border border-accent-green/20 rounded-btn px-3 py-2">{actionMsg}</div>}

      {/* Filters */}
      <div className="flex gap-2">
        {FILTERS.map((f) => (
          <button key={f} onClick={() => { setFilter(f); setPage(1); }}
            className={cn("px-3 py-1.5 text-xs rounded-btn border transition-colors",
              filter === f ? "bg-accent-blue/10 text-accent-blue border-accent-blue/20" : "bg-bg-surface text-txt-muted border-bdr hover:bg-bg-hover"
            )}>
            {f || "ทั้งหมด"}
          </button>
        ))}
      </div>

      {loading ? <LoadingSpinner /> : (
        <>
          <div className="bg-bg-surface border border-bdr rounded-card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-bdr text-txt-muted text-xs">
                  <th className="text-left px-4 py-3 font-medium">วันที่</th>
                  <th className="text-left px-4 py-3 font-medium">ผู้ใช้</th>
                  <th className="text-right px-4 py-3 font-medium">จำนวน (บาท)</th>
                  <th className="text-left px-4 py-3 font-medium">Bank Ref</th>
                  <th className="text-center px-4 py-3 font-medium">สถานะ</th>
                  <th className="text-center px-4 py-3 font-medium">การจัดการ</th>
                </tr>
              </thead>
              <tbody>
                {slips.map((s) => (
                  <tr key={s.id} className="border-b border-bdr/50 hover:bg-bg-hover transition-colors">
                    <td className="px-4 py-3 text-txt-muted text-xs">{formatDateTime(s.created_at)}</td>
                    <td className="px-4 py-3 text-txt-secondary font-mono text-xs">{s.user_id.slice(0, 12)}...</td>
                    <td className="px-4 py-3 text-right text-accent-green font-medium">{s.amount_detected != null ? formatNumber(s.amount_detected) : "—"}</td>
                    <td className="px-4 py-3 text-txt-muted text-xs font-mono">{s.bank_ref || "—"}</td>
                    <td className="px-4 py-3 text-center"><StatusBadge status={s.status} /></td>
                    <td className="px-4 py-3 text-center">
                      {s.status === "PENDING" && (
                        <div className="flex gap-1.5 justify-center">
                          <button onClick={() => doApprove(s.id)} className="px-2 py-1 text-[11px] bg-accent-green/10 text-accent-green border border-accent-green/20 rounded hover:bg-accent-green/20">อนุมัติ</button>
                          <button onClick={() => doReject(s.id)} className="px-2 py-1 text-[11px] bg-accent-red/10 text-accent-red border border-accent-red/20 rounded hover:bg-accent-red/20">ปฏิเสธ</button>
                        </div>
                      )}
                      {s.status === "REJECTED" && s.reject_reason && (
                        <span className="text-[11px] text-txt-muted">{s.reject_reason}</span>
                      )}
                    </td>
                  </tr>
                ))}
                {slips.length === 0 && <tr><td colSpan={6} className="text-center py-8 text-txt-muted text-sm">ไม่มีรายการ</td></tr>}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between text-xs text-txt-muted">
            <span>{total} รายการ</span>
            <div className="flex items-center gap-2">
              <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page <= 1} className="p-1 hover:text-txt-primary disabled:opacity-30"><ChevronLeft size={16} /></button>
              <span>{page} / {pages}</span>
              <button onClick={() => setPage(Math.min(pages, page + 1))} disabled={page >= pages} className="p-1 hover:text-txt-primary disabled:opacity-30"><ChevronRight size={16} /></button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
