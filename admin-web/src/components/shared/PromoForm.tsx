"use client";

import { useState } from "react";

const S = {
  label: "block text-xs text-[#4a5568] mb-1.5",
  input: "w-full px-3 py-2 bg-[#f8f9fb] border border-[#d1d9e6] rounded-[10px] text-sm text-[#1a202c] outline-none",
  select: "w-full px-3 py-2 bg-[#f8f9fb] border border-[#d1d9e6] rounded-[10px] text-sm text-[#1a202c] outline-none",
  section: "space-y-3 p-4 bg-[#ffffff] border border-[#d1d9e6] rounded-[16px]",
  sectionTitle: "text-sm font-medium text-[#1a202c] mb-3",
};

const PROMO_TYPES = [
  { value: "WELCOME_BONUS", label: "โบนัสสมาชิกใหม่" },
  { value: "TIERED_BONUS", label: "โบนัสตามขั้น" },
  { value: "RATE_BOOST", label: "เพิ่มอัตราเครดิต" },
  { value: "FLAT_BONUS", label: "โบนัสคงที่" },
];

const REWARD_TYPES = [
  { value: "BONUS_CREDITS", label: "เครดิตโบนัส" },
  { value: "RATE_OVERRIDE", label: "แทนที่อัตราเครดิต" },
  { value: "TIERED_BONUS", label: "โบนัสตามขั้น" },
];

export interface PromoFormData {
  name: string;
  code: string;
  type: string;
  priority: number;
  conditions: {
    start_date: string;
    end_date: string;
    min_topup_baht: number | null;
    max_topup_baht: number | null;
    max_redemptions: number | null;
    max_per_user: number | null;
    eligible_tiers: string[] | null;
    new_users_only: boolean;
    first_topup_only: boolean;
    require_code: boolean;
  };
  reward: {
    type: string;
    bonus_credits: number | null;
    override_rate: number | null;
    bonus_percentage: number | null;
    tiers: { min_baht: number; bonus_credits: number }[] | null;
  };
  display: {
    banner_text: string;
    banner_color: string;
    show_in_client: boolean;
    show_in_topup: boolean;
  };
}

const DEFAULT_DATA: PromoFormData = {
  name: "",
  code: "",
  type: "WELCOME_BONUS",
  priority: 0,
  conditions: {
    start_date: new Date().toISOString().slice(0, 16),
    end_date: "",
    min_topup_baht: null,
    max_topup_baht: null,
    max_redemptions: null,
    max_per_user: null,
    eligible_tiers: null,
    new_users_only: false,
    first_topup_only: false,
    require_code: false,
  },
  reward: {
    type: "BONUS_CREDITS",
    bonus_credits: null,
    override_rate: null,
    bonus_percentage: null,
    tiers: null,
  },
  display: {
    banner_text: "",
    banner_color: "#FF4560",
    show_in_client: true,
    show_in_topup: true,
  },
};

interface Props {
  initial?: Partial<PromoFormData>;
  onSubmit: (data: PromoFormData) => Promise<void>;
  submitLabel: string;
}

export default function PromoForm({ initial, onSubmit, submitLabel }: Props) {
  const [data, setData] = useState<PromoFormData>({ ...DEFAULT_DATA, ...initial });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const set = <K extends keyof PromoFormData>(key: K, val: PromoFormData[K]) =>
    setData((d) => ({ ...d, [key]: val }));

  const setCond = (key: string, val: unknown) =>
    setData((d) => ({ ...d, conditions: { ...d.conditions, [key]: val } }));

  const setReward = (key: string, val: unknown) =>
    setData((d) => ({ ...d, reward: { ...d.reward, [key]: val } }));

  const setDisplay = (key: string, val: unknown) =>
    setData((d) => ({ ...d, display: { ...d.display, [key]: val } }));

  const handleSubmit = async () => {
    if (!data.name.trim()) { setError("กรุณาใส่ชื่อโปรโมชั่น"); return; }
    setSaving(true);
    setError("");
    try {
      await onSubmit(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "เกิดข้อผิดพลาด");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-5 max-w-2xl">
      {error && (
        <div style={{ color: "#f87171", background: "rgba(248,113,113,0.1)", border: "1px solid rgba(248,113,113,0.2)", borderRadius: 10, padding: "8px 12px", fontSize: 12 }}>
          {error}
        </div>
      )}

      {/* Basic Info */}
      <div className={S.section}>
        <h3 className={S.sectionTitle}>ข้อมูลพื้นฐาน</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className={S.label}>ชื่อโปรโมชั่น *</label>
            <input className={S.input} value={data.name} onChange={(e) => set("name", e.target.value)} placeholder="เช่น สมาชิกใหม่รับโบนัส" />
          </div>
          <div>
            <label className={S.label}>โค้ด (ถ้ามี)</label>
            <input className={S.input} value={data.code} onChange={(e) => set("code", e.target.value.toUpperCase())} placeholder="PROMO2026" />
          </div>
          <div>
            <label className={S.label}>ประเภท</label>
            <select className={S.select} value={data.type} onChange={(e) => set("type", e.target.value)}>
              {PROMO_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div>
            <label className={S.label}>ลำดับความสำคัญ</label>
            <input className={S.input} type="number" value={data.priority} onChange={(e) => set("priority", Number(e.target.value))} />
          </div>
        </div>
      </div>

      {/* Conditions */}
      <div className={S.section}>
        <h3 className={S.sectionTitle}>เงื่อนไข</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className={S.label}>วันเริ่มต้น</label>
            <input className={S.input} type="datetime-local" value={data.conditions.start_date} onChange={(e) => setCond("start_date", e.target.value)} />
          </div>
          <div>
            <label className={S.label}>วันสิ้นสุด</label>
            <input className={S.input} type="datetime-local" value={data.conditions.end_date || ""} onChange={(e) => setCond("end_date", e.target.value || null)} />
          </div>
          <div>
            <label className={S.label}>เติมเงินขั้นต่ำ (บาท)</label>
            <input className={S.input} type="number" value={data.conditions.min_topup_baht ?? ""} onChange={(e) => setCond("min_topup_baht", e.target.value ? Number(e.target.value) : null)} />
          </div>
          <div>
            <label className={S.label}>เติมเงินสูงสุด (บาท)</label>
            <input className={S.input} type="number" value={data.conditions.max_topup_baht ?? ""} onChange={(e) => setCond("max_topup_baht", e.target.value ? Number(e.target.value) : null)} />
          </div>
          <div>
            <label className={S.label}>จำนวนครั้งสูงสุด (รวม)</label>
            <input className={S.input} type="number" value={data.conditions.max_redemptions ?? ""} onChange={(e) => setCond("max_redemptions", e.target.value ? Number(e.target.value) : null)} />
          </div>
          <div>
            <label className={S.label}>จำนวนครั้ง/คน</label>
            <input className={S.input} type="number" value={data.conditions.max_per_user ?? ""} onChange={(e) => setCond("max_per_user", e.target.value ? Number(e.target.value) : null)} />
          </div>
        </div>
        <div className="flex flex-wrap gap-4 mt-3">
          <label className="flex items-center gap-2 text-xs text-[#4a5568] cursor-pointer">
            <input type="checkbox" checked={data.conditions.new_users_only} onChange={(e) => setCond("new_users_only", e.target.checked)} className="accent-[#3b82f6]" />
            สมาชิกใหม่เท่านั้น
          </label>
          <label className="flex items-center gap-2 text-xs text-[#4a5568] cursor-pointer">
            <input type="checkbox" checked={data.conditions.first_topup_only} onChange={(e) => setCond("first_topup_only", e.target.checked)} className="accent-[#3b82f6]" />
            เติมเงินครั้งแรกเท่านั้น
          </label>
          <label className="flex items-center gap-2 text-xs text-[#4a5568] cursor-pointer">
            <input type="checkbox" checked={data.conditions.require_code} onChange={(e) => setCond("require_code", e.target.checked)} className="accent-[#3b82f6]" />
            ต้องใส่โค้ด
          </label>
        </div>
      </div>

      {/* Reward */}
      <div className={S.section}>
        <h3 className={S.sectionTitle}>รางวัล</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className={S.label}>ประเภทรางวัล</label>
            <select className={S.select} value={data.reward.type} onChange={(e) => setReward("type", e.target.value)}>
              {REWARD_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          {data.reward.type === "BONUS_CREDITS" && (
            <div>
              <label className={S.label}>เครดิตโบนัส</label>
              <input className={S.input} type="number" value={data.reward.bonus_credits ?? ""} onChange={(e) => setReward("bonus_credits", e.target.value ? Number(e.target.value) : null)} />
            </div>
          )}
          {data.reward.type === "RATE_OVERRIDE" && (
            <div>
              <label className={S.label}>อัตราเครดิตใหม่ (เครดิต/บาท)</label>
              <input className={S.input} type="number" value={data.reward.override_rate ?? ""} onChange={(e) => setReward("override_rate", e.target.value ? Number(e.target.value) : null)} />
            </div>
          )}
          <div>
            <label className={S.label}>เปอร์เซ็นต์โบนัส (%)</label>
            <input className={S.input} type="number" value={data.reward.bonus_percentage ?? ""} onChange={(e) => setReward("bonus_percentage", e.target.value ? Number(e.target.value) : null)} />
          </div>
        </div>
      </div>

      {/* Display */}
      <div className={S.section}>
        <h3 className={S.sectionTitle}>การแสดงผล</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className={S.label}>ข้อความแบนเนอร์</label>
            <input className={S.input} value={data.display.banner_text} onChange={(e) => setDisplay("banner_text", e.target.value)} placeholder="รับโบนัส 50 เครดิต!" />
          </div>
          <div>
            <label className={S.label}>สีแบนเนอร์</label>
            <div className="flex gap-2 items-center">
              <input type="color" value={data.display.banner_color} onChange={(e) => setDisplay("banner_color", e.target.value)} className="w-10 h-10 rounded border-0 cursor-pointer" />
              <input className={S.input} value={data.display.banner_color} onChange={(e) => setDisplay("banner_color", e.target.value)} />
            </div>
          </div>
        </div>
        <div className="flex flex-wrap gap-4 mt-3">
          <label className="flex items-center gap-2 text-xs text-[#4a5568] cursor-pointer">
            <input type="checkbox" checked={data.display.show_in_client} onChange={(e) => setDisplay("show_in_client", e.target.checked)} className="accent-[#3b82f6]" />
            แสดงใน Client
          </label>
          <label className="flex items-center gap-2 text-xs text-[#4a5568] cursor-pointer">
            <input type="checkbox" checked={data.display.show_in_topup} onChange={(e) => setDisplay("show_in_topup", e.target.checked)} className="accent-[#3b82f6]" />
            แสดงในหน้าเติมเงิน
          </label>
        </div>
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={saving}
        style={{ width: "100%", padding: "12px 0", background: "linear-gradient(90deg, #3b82f6, #7c3aed)", color: "#fff", fontSize: 14, fontWeight: 500, border: "none", borderRadius: 10, cursor: "pointer", opacity: saving ? 0.5 : 1 }}
      >
        {saving ? "กำลังบันทึก..." : submitLabel}
      </button>
    </div>
  );
}
