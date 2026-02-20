"use client";

import { useEffect, useState, useCallback } from "react";
import { getUsers, getUser, getUserTransactions, getUserJobs, adjustCredits, suspendUser, unsuspendUser, resetHardware, resetPassword, deleteUser } from "@/lib/api";
import { formatNumber, formatCurrency, formatDateTime, statusBgColor, cn } from "@/lib/utils";
import StatusBadge from "@/components/shared/StatusBadge";
import LoadingSpinner from "@/components/shared/LoadingSpinner";
import { Search, X, ChevronLeft, ChevronRight } from "lucide-react";

interface User {
  uid: string; email: string; full_name: string; credits: number;
  status: string; tier: string; last_login: string; created_at: string;
}

interface UserFull extends User {
  hardware_id: string; total_topup_baht: number;
  total_credits_used: number; app_version: string; os_type: string; last_active: string;
}

interface Tx { id: string; type: string; amount: number; balance_after: number; description: string; date: string; }
interface Job { id: string; job_token: string; mode: string; file_count: number; status: string; reserved_credits: number; actual_usage: number; success_count: number; failed_count: number; created_at: string; }

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<UserFull | null>(null);
  const [txs, setTxs] = useState<Tx[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [tab, setTab] = useState<"info" | "txs" | "jobs">("info");
  const [actionMsg, setActionMsg] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getUsers(search, page) as { users: User[]; total: number; pages: number };
      setUsers(res.users);
      setTotal(res.total);
      setPages(res.pages);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [search, page]);

  useEffect(() => { load(); }, [load]);

  const selectUser = async (uid: string) => {
    try {
      const [u, t, j] = await Promise.all([
        getUser(uid) as unknown as Promise<UserFull>,
        getUserTransactions(uid) as unknown as Promise<{ transactions: Tx[] }>,
        getUserJobs(uid) as unknown as Promise<{ jobs: Job[] }>,
      ]);
      setSelected(u);
      setTxs(t.transactions);
      setJobs(j.jobs);
      setTab("info");
      setActionMsg("");
    } catch (e) { console.error(e); }
  };

  const doAction = async (fn: () => Promise<unknown>) => {
    try {
      const res = await fn() as { message?: string };
      setActionMsg(res.message || "สำเร็จ");
      if (selected) selectUser(selected.uid);
      load();
    } catch (e: unknown) {
      setActionMsg(e instanceof Error ? e.message : "เกิดข้อผิดพลาด");
    }
  };

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-bold text-txt-primary">ผู้ใช้งาน</h1>

      {/* Search */}
      <div className="relative max-w-md">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-txt-muted" />
        <input
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          placeholder="ค้นหา email, ชื่อ, uid..."
          className="w-full pl-9 pr-3 py-2 bg-bg-input border border-bdr rounded-input text-sm text-txt-primary placeholder:text-txt-muted"
        />
      </div>

      <div className="flex gap-5">
        {/* Table */}
        <div className="flex-1 min-w-0">
          {loading ? <LoadingSpinner /> : (
            <>
              <div className="bg-bg-surface border border-bdr rounded-card overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-bdr text-txt-muted text-xs">
                        <th className="text-left px-4 py-3 font-medium">Email</th>
                        <th className="text-left px-4 py-3 font-medium">ชื่อ</th>
                        <th className="text-right px-4 py-3 font-medium">เครดิต</th>
                        <th className="text-center px-4 py-3 font-medium">สถานะ</th>
                        <th className="text-left px-4 py-3 font-medium">เข้าสู่ระบบล่าสุด</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map((u) => (
                        <tr
                          key={u.uid}
                          onClick={() => selectUser(u.uid)}
                          className={cn(
                            "border-b border-bdr/50 cursor-pointer transition-colors",
                            selected?.uid === u.uid ? "bg-accent-blue/5" : "hover:bg-bg-hover"
                          )}
                        >
                          <td className="px-4 py-3 text-txt-primary font-mono text-xs">{u.email}</td>
                          <td className="px-4 py-3 text-txt-secondary">{u.full_name || "—"}</td>
                          <td className="px-4 py-3 text-right text-accent-yellow font-medium">{formatNumber(u.credits)}</td>
                          <td className="px-4 py-3 text-center"><StatusBadge status={u.status} /></td>
                          <td className="px-4 py-3 text-txt-muted text-xs">{formatDateTime(u.last_login)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Pagination */}
              <div className="flex items-center justify-between mt-3 text-xs text-txt-muted">
                <span>{total} ผู้ใช้</span>
                <div className="flex items-center gap-2">
                  <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page <= 1} className="p-1 hover:text-txt-primary disabled:opacity-30"><ChevronLeft size={16} /></button>
                  <span>{page} / {pages}</span>
                  <button onClick={() => setPage(Math.min(pages, page + 1))} disabled={page >= pages} className="p-1 hover:text-txt-primary disabled:opacity-30"><ChevronRight size={16} /></button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Detail Panel */}
        {selected && (
          <div className="w-[380px] shrink-0 hidden xl:block bg-bg-surface border border-bdr rounded-card p-5 space-y-4 max-h-[calc(100vh-140px)] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-txt-primary">รายละเอียดผู้ใช้</h3>
              <button onClick={() => setSelected(null)} className="text-txt-muted hover:text-txt-primary"><X size={16} /></button>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 bg-bg-root rounded-btn p-0.5">
              {(["info", "txs", "jobs"] as const).map((t) => (
                <button key={t} onClick={() => setTab(t)} className={cn("flex-1 py-1.5 text-xs rounded-btn transition-colors", tab === t ? "bg-bg-elevated text-txt-primary" : "text-txt-muted hover:text-txt-secondary")}>
                  {t === "info" ? "ข้อมูล" : t === "txs" ? "เครดิต" : "งาน"}
                </button>
              ))}
            </div>

            {actionMsg && <div className="text-xs text-accent-green bg-accent-green/10 border border-accent-green/20 rounded-btn px-3 py-2">{actionMsg}</div>}

            {tab === "info" && (
              <div className="space-y-3 text-xs">
                <InfoRow label="UID" value={selected.uid} mono />
                <InfoRow label="Email" value={selected.email} />
                <InfoRow label="ชื่อ" value={selected.full_name} />
                <InfoRow label="เครดิต" value={formatNumber(selected.credits)} highlight />
                <InfoRow label="เติมเงินรวม" value={formatCurrency(selected.total_topup_baht)} />
                <InfoRow label="ใช้ไปรวม" value={formatNumber(selected.total_credits_used) + " cr"} />
                <InfoRow label="Tier" value={selected.tier} />
                <InfoRow label="Hardware" value={selected.hardware_id?.slice(0, 16) + "..." || "—"} mono />
                <InfoRow label="App Version" value={selected.app_version || "—"} />
                <InfoRow label="OS" value={selected.os_type || "—"} />
                <InfoRow label="สมัครเมื่อ" value={formatDateTime(selected.created_at)} />
                <InfoRow label="ใช้งานล่าสุด" value={formatDateTime(selected.last_active)} />

                <hr className="border-bdr" />
                <h4 className="text-txt-secondary font-medium">การจัดการ</h4>

                {/* Adjust Credits */}
                <form onSubmit={(e) => {
                  e.preventDefault();
                  const fd = new FormData(e.currentTarget);
                  doAction(() => adjustCredits(selected.uid, Number(fd.get("amount")), String(fd.get("reason"))));
                }} className="flex flex-col gap-1.5">
                  <div className="flex gap-1.5">
                    <input name="amount" type="number" required placeholder="จำนวน (+/-)" className="flex-1 px-2 py-1.5 bg-bg-input border border-bdr rounded text-xs text-txt-primary" />
                    <input name="reason" placeholder="เหตุผล" className="flex-1 px-2 py-1.5 bg-bg-input border border-bdr rounded text-xs text-txt-primary" />
                  </div>
                  <button type="submit" className="px-3 py-1.5 bg-accent-blue/10 text-accent-blue border border-accent-blue/20 rounded text-xs hover:bg-accent-blue/20">ปรับเครดิต</button>
                </form>

                {/* Suspend / Unsuspend */}
                {selected.status === "active" ? (
                  <button onClick={() => doAction(() => suspendUser(selected.uid))} className="w-full px-3 py-1.5 bg-accent-red/10 text-accent-red border border-accent-red/20 rounded text-xs hover:bg-accent-red/20">ระงับบัญชี</button>
                ) : selected.status === "suspended" ? (
                  <button onClick={() => doAction(() => unsuspendUser(selected.uid))} className="w-full px-3 py-1.5 bg-accent-green/10 text-accent-green border border-accent-green/20 rounded text-xs hover:bg-accent-green/20">เปิดบัญชี</button>
                ) : null}

                {/* Reset Hardware */}
                <button onClick={() => doAction(() => resetHardware(selected.uid))} className="w-full px-3 py-1.5 bg-accent-yellow/10 text-accent-yellow border border-accent-yellow/20 rounded text-xs hover:bg-accent-yellow/20">รีเซ็ต Hardware ID</button>

                {/* Reset Password */}
                <form onSubmit={(e) => {
                  e.preventDefault();
                  const fd = new FormData(e.currentTarget);
                  doAction(() => resetPassword(selected.uid, String(fd.get("pw")), true));
                }} className="flex gap-1.5">
                  <input name="pw" type="text" required minLength={8} placeholder="รหัสผ่านใหม่" className="flex-1 px-2 py-1.5 bg-bg-input border border-bdr rounded text-xs text-txt-primary" />
                  <button type="submit" className="px-3 py-1.5 bg-accent-orange/10 text-accent-orange border border-accent-orange/20 rounded text-xs hover:bg-accent-orange/20">รีเซ็ต</button>
                </form>

                {/* Delete Account */}
                <hr className="border-bdr" />
                {!confirmDelete ? (
                  <button onClick={() => setConfirmDelete(true)} className="w-full px-3 py-1.5 bg-accent-red/5 text-accent-red/70 border border-accent-red/20 rounded text-xs hover:bg-accent-red/15 hover:text-accent-red">ลบบัญชีนี้</button>
                ) : (
                  <div className="space-y-1.5">
                    <p className="text-xs text-accent-red">⚠️ ยืนยันลบบัญชี <span className="font-semibold">{selected.email}</span> ? ไม่สามารถกู้คืนได้</p>
                    <div className="flex gap-1.5">
                      <button onClick={() => { doAction(() => deleteUser(selected.uid)); setConfirmDelete(false); setSelected(null); }} className="flex-1 px-3 py-1.5 bg-accent-red text-white rounded text-xs hover:bg-accent-red/80">ยืนยันลบ</button>
                      <button onClick={() => setConfirmDelete(false)} className="flex-1 px-3 py-1.5 bg-bg-input border border-bdr rounded text-xs text-txt-secondary hover:text-txt-primary">ยกเลิก</button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {tab === "txs" && (
              <div className="space-y-1.5 max-h-96 overflow-y-auto">
                {txs.length === 0 && <p className="text-xs text-txt-muted py-4 text-center">ไม่มีรายการ</p>}
                {txs.map((t) => (
                  <div key={t.id} className="flex items-center justify-between px-2 py-1.5 bg-bg-root rounded text-xs">
                    <div>
                      <div className="text-txt-secondary">{t.description || t.type}</div>
                      <div className="text-txt-muted text-[10px]">{t.date}</div>
                    </div>
                    <span className={t.amount > 0 ? "text-accent-green font-medium" : "text-accent-red font-medium"}>
                      {t.amount > 0 ? "+" : ""}{formatNumber(t.amount)}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {tab === "jobs" && (
              <div className="space-y-1.5 max-h-96 overflow-y-auto">
                {jobs.length === 0 && <p className="text-xs text-txt-muted py-4 text-center">ไม่มีรายการ</p>}
                {jobs.map((j) => (
                  <div key={j.id} className="px-2 py-1.5 bg-bg-root rounded text-xs space-y-0.5">
                    <div className="flex items-center justify-between">
                      <span className="text-txt-secondary">{j.mode} · {j.file_count} ไฟล์</span>
                      <StatusBadge status={j.status} />
                    </div>
                    <div className="text-txt-muted text-[10px]">{j.created_at} · ✓{j.success_count} ✗{j.failed_count}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function InfoRow({ label, value, mono, highlight }: { label: string; value: string; mono?: boolean; highlight?: boolean }) {
  return (
    <div className="flex justify-between">
      <span className="text-txt-muted">{label}</span>
      <span className={cn(mono && "font-mono", highlight && "text-accent-yellow font-medium", "text-txt-primary text-right max-w-[200px] truncate")}>{value}</span>
    </div>
  );
}
