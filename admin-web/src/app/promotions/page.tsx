"use client";

import { useEffect, useState } from "react";
import { getPromos, promoAction } from "@/lib/api";
import { formatDateTime, cn } from "@/lib/utils";
import StatusBadge from "@/components/shared/StatusBadge";
import LoadingSpinner from "@/components/shared/LoadingSpinner";

interface Promo {
  promo_id: string; name: string; code: string | null; type: string;
  status: string; priority: number; created_at: string;
  conditions: { min_amount?: number; start_date?: string; end_date?: string };
  reward: { type?: string; value?: number };
  stats: { total_used?: number; total_bonus_credits?: number };
}

const FILTERS = ["", "ACTIVE", "DRAFT", "PAUSED", "CANCELLED", "EXPIRED"];

export default function PromotionsPage() {
  const [promos, setPromos] = useState<Promo[]>([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const res = await getPromos(filter) as { promotions: Promo[] };
      // Hide CANCELLED from the default "All" view (when filter is empty)
      const allPromos = res.promotions || [];
      setPromos(filter === "" ? allPromos.filter(p => p.status !== "CANCELLED") : allPromos);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [filter]);

  const doAction = async (id: string, action: string) => {
    const isDelete = action === "delete";
    if (!confirm(isDelete ? "ลบโปรโมชั่นนี้ถาวร ใช่หรือไม่? (ไม่สามารถกู้คืนได้)" : `${action} โปรโมชั่นนี้?`)) return;
    try {
      if (isDelete) {
        const { deletePromo } = await import("@/lib/api");
        const res = await deletePromo(id) as { message: string };
        setMsg(res.message);
      } else {
        const res = await promoAction(id, action) as { message: string };
        setMsg(res.message);
      }
      load();
    } catch (e: unknown) { setMsg(e instanceof Error ? e.message : "Error"); }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-txt-primary">โปรโมชั่น</h1>
        <a href="/promotions/create" className="px-3 py-1.5 text-xs bg-accent-blue text-white rounded-btn hover:opacity-90">+ สร้างใหม่</a>
      </div>

      {msg && <div className="text-xs text-accent-green bg-accent-green/10 border border-accent-green/20 rounded-btn px-3 py-2">{msg}</div>}

      <div className="flex gap-2 flex-wrap">
        {FILTERS.map((f) => (
          <button key={f} onClick={() => setFilter(f)}
            className={cn("px-3 py-1.5 text-xs rounded-btn border transition-colors",
              filter === f ? "bg-accent-blue/10 text-accent-blue border-accent-blue/20" : "text-txt-muted border-bdr hover:bg-bg-hover"
            )}>
            {f || "ทั้งหมด"}
          </button>
        ))}
      </div>

      {loading ? <LoadingSpinner /> : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {promos.map((p) => (
            <div key={p.promo_id} className="bg-bg-surface border border-bdr rounded-card p-4 space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-medium text-txt-primary">{p.name}</h3>
                  {p.code && <span className="text-[11px] font-mono text-accent-purple bg-accent-purple/10 px-1.5 py-0.5 rounded mt-1 inline-block">{p.code}</span>}
                </div>
                <StatusBadge status={p.status} />
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div><span className="text-txt-muted">ประเภท:</span> <span className="text-txt-secondary">{p.type}</span></div>
                <div><span className="text-txt-muted">ลำดับ:</span> <span className="text-txt-secondary">{p.priority}</span></div>
                <div><span className="text-txt-muted">ใช้แล้ว:</span> <span className="text-accent-green">{p.stats?.total_used || 0}</span></div>
                <div><span className="text-txt-muted">โบนัส:</span> <span className="text-accent-yellow">{p.stats?.total_bonus_credits || 0} cr</span></div>
              </div>

              {p.reward?.type && (
                <div className="text-xs text-txt-muted">
                  รางวัล: {p.reward.type} {p.reward.value}
                  {p.conditions?.min_amount ? ` (ขั้นต่ำ ${p.conditions.min_amount} บาท)` : ""}
                </div>
              )}

              <div className="flex gap-1.5 pt-1 flex-wrap">
                {["DRAFT", "PAUSED"].includes(p.status) && (
                  <a href={`/promotions/edit/${p.promo_id}`} className="px-2 py-1 text-[11px] bg-accent-blue/10 text-accent-blue border border-accent-blue/20 rounded hover:bg-accent-blue/20">แก้ไข</a>
                )}
                {p.status === "DRAFT" && (
                  <button onClick={() => doAction(p.promo_id, "activate")} className="px-2 py-1 text-[11px] bg-accent-green/10 text-accent-green border border-accent-green/20 rounded hover:bg-accent-green/20">เปิดใช้</button>
                )}
                {p.status === "ACTIVE" && (
                  <button onClick={() => doAction(p.promo_id, "pause")} className="px-2 py-1 text-[11px] bg-accent-yellow/10 text-accent-yellow border border-accent-yellow/20 rounded hover:bg-accent-yellow/20">หยุดชั่วคราว</button>
                )}
                {p.status === "PAUSED" && (
                  <button onClick={() => doAction(p.promo_id, "activate")} className="px-2 py-1 text-[11px] bg-accent-green/10 text-accent-green border border-accent-green/20 rounded hover:bg-accent-green/20">เปิดใช้</button>
                )}
                {["ACTIVE", "DRAFT", "PAUSED"].includes(p.status) && (
                  <button onClick={() => doAction(p.promo_id, "cancel")} className="px-2 py-1 text-[11px] bg-accent-red/10 text-accent-red border border-accent-red/20 rounded hover:bg-accent-red/20">ยกเลิก</button>
                )}
                {["DRAFT", "PAUSED", "CANCELLED"].includes(p.status) && (
                  <button onClick={() => doAction(p.promo_id, "delete")} className="px-2 py-1 text-[11px] bg-accent-red/5 text-accent-red/60 border border-accent-red/20 rounded hover:bg-accent-red/15 hover:text-accent-red ml-auto">ลบถาวร</button>
                )}
              </div>
            </div>
          ))}
          {promos.length === 0 && <div className="col-span-full text-center py-12 text-txt-muted text-sm">ไม่มีโปรโมชั่น</div>}
        </div>
      )}
    </div>
  );
}
