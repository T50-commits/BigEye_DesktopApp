"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { getPromo, updatePromo } from "@/lib/api";
import PromoForm, { type PromoFormData } from "@/components/shared/PromoForm";
import LoadingSpinner from "@/components/shared/LoadingSpinner";

export default function EditPromoPage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;
  const [initial, setInitial] = useState<Partial<PromoFormData> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        const res = await getPromo(id) as Record<string, unknown>;
        const cond = (res.conditions || {}) as Record<string, unknown>;
        const reward = (res.reward || {}) as Record<string, unknown>;
        const display = (res.display || {}) as Record<string, unknown>;

        // Convert ISO dates to datetime-local format
        const toLocal = (v: unknown) => {
          if (!v) return "";
          const s = String(v);
          try { return new Date(s).toISOString().slice(0, 16); } catch { return s.slice(0, 16); }
        };

        setInitial({
          name: String(res.name || ""),
          code: String(res.code || ""),
          type: String(res.type || "WELCOME_BONUS"),
          priority: Number(res.priority || 0),
          conditions: {
            start_date: toLocal(cond.start_date) || new Date().toISOString().slice(0, 16),
            end_date: toLocal(cond.end_date) || "",
            min_topup_baht: cond.min_topup_baht != null ? Number(cond.min_topup_baht) : null,
            max_topup_baht: cond.max_topup_baht != null ? Number(cond.max_topup_baht) : null,
            max_redemptions: cond.max_redemptions != null ? Number(cond.max_redemptions) : null,
            max_per_user: cond.max_per_user != null ? Number(cond.max_per_user) : null,
            eligible_tiers: (cond.eligible_tiers as string[] | null) || null,
            new_users_only: Boolean(cond.new_users_only),
            first_topup_only: Boolean(cond.first_topup_only),
            require_code: Boolean(cond.require_code),
          },
          reward: {
            type: String(reward.type || "BONUS_CREDITS"),
            bonus_credits: reward.bonus_credits != null ? Number(reward.bonus_credits) : null,
            override_rate: reward.override_rate != null ? Number(reward.override_rate) : null,
            bonus_percentage: reward.bonus_percentage != null ? Number(reward.bonus_percentage) : null,
            tiers: (reward.tiers as { min_baht: number; bonus_credits: number }[] | null) || null,
          },
          display: {
            banner_text: String(display.banner_text || ""),
            banner_color: String(display.banner_color || "#FF4560"),
            show_in_client: display.show_in_client !== false,
            show_in_topup: display.show_in_topup !== false,
          },
        });
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "ไม่สามารถโหลดข้อมูลโปรโมชั่น");
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  const handleUpdate = async (data: PromoFormData) => {
    await updatePromo(id, data as unknown as Record<string, unknown>);
    router.push("/promotions");
  };

  if (loading) return <LoadingSpinner text="กำลังโหลดข้อมูลโปรโมชั่น..." />;

  if (error) return (
    <div className="space-y-4">
      <a href="/promotions" className="text-xs text-txt-muted hover:text-txt-secondary">&larr; กลับ</a>
      <div style={{ color: "#f87171", background: "rgba(248,113,113,0.1)", border: "1px solid rgba(248,113,113,0.2)", borderRadius: 10, padding: "12px 16px", fontSize: 13 }}>
        {error}
      </div>
    </div>
  );

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <a href="/promotions" className="text-xs text-txt-muted hover:text-txt-secondary">&larr; กลับ</a>
        <h1 className="text-xl font-bold text-txt-primary">แก้ไขโปรโมชั่น</h1>
      </div>
      {initial && <PromoForm initial={initial} onSubmit={handleUpdate} submitLabel="บันทึกการแก้ไข" />}
    </div>
  );
}
