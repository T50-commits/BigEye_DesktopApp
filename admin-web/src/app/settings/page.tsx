"use client";

import { useEffect, useState } from "react";
import { getConfig, updateConfig, updatePrompt, getDictionary, updateDictionary } from "@/lib/api";
import LoadingSpinner from "@/components/shared/LoadingSpinner";
import { cn } from "@/lib/utils";

type Tab = "version" | "rates" | "bank" | "processing" | "maintenance" | "prompts" | "blacklist" | "dictionary";
const TABS: { key: Tab; label: string }[] = [
  { key: "version", label: "เวอร์ชัน" },
  { key: "rates", label: "อัตราเครดิต" },
  { key: "bank", label: "ธนาคาร" },
  { key: "processing", label: "ประมวลผล" },
  { key: "maintenance", label: "ปิดปรับปรุง" },
  { key: "prompts", label: "พรอมต์" },
  { key: "blacklist", label: "คำต้องห้าม" },
  { key: "dictionary", label: "พจนานุกรม" },
];

export default function SettingsPage() {
  const [cfg, setCfg] = useState<Record<string, unknown>>({});
  const [tab, setTab] = useState<Tab>("version");
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");

  const load = async () => {
    setLoading(true);
    try { setCfg(await getConfig()); } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const save = async (section: string, data: Record<string, unknown>) => {
    try {
      const res = await updateConfig(section, data) as { message: string };
      setMsg(res.message); load();
    } catch (e: unknown) { setMsg(e instanceof Error ? e.message : "Error"); }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-bold text-txt-primary">ตั้งค่าระบบ</h1>
      {msg && <div className="text-xs text-accent-green bg-accent-green/10 border border-accent-green/20 rounded-btn px-3 py-2">{msg}</div>}

      {/* Tabs */}
      <div className="flex gap-1 flex-wrap bg-bg-surface border border-bdr rounded-card p-1">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => { setTab(t.key); setMsg(""); }}
            className={cn("px-3 py-1.5 text-xs rounded-btn transition-colors",
              tab === t.key ? "bg-accent-blue/10 text-accent-blue" : "text-txt-muted hover:text-txt-secondary"
            )}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="bg-bg-surface border border-bdr rounded-card p-5">
        {tab === "version" && <VersionForm cfg={cfg} onSave={(d) => save("version", d)} />}
        {tab === "rates" && <RatesForm cfg={cfg} onSave={(d) => save("rates", d)} />}
        {tab === "bank" && <BankForm cfg={cfg} onSave={(d) => save("bank", d)} />}
        {tab === "processing" && <ProcessingForm cfg={cfg} onSave={(d) => save("processing", d)} />}
        {tab === "maintenance" && <MaintenanceForm cfg={cfg} onSave={(d) => save("maintenance", d)} />}
        {tab === "prompts" && <PromptsForm cfg={cfg} onReload={load} setMsg={setMsg} />}
        {tab === "blacklist" && <BlacklistForm cfg={cfg} onSave={(d) => save("blacklist", d)} />}
        {tab === "dictionary" && <DictionaryForm setMsg={setMsg} />}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="space-y-1"><label className="text-xs text-txt-muted">{label}</label>{children}</div>;
}
function Input({ value, onChange, type = "text", placeholder = "" }: { value: string; onChange: (v: string) => void; type?: string; placeholder?: string }) {
  return <input type={type} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className="w-full px-3 py-2 bg-bg-input border border-bdr rounded-input text-sm text-txt-primary" />;
}
function SaveBtn({ onClick }: { onClick: () => void }) {
  return <button onClick={onClick} className="mt-4 px-4 py-2 bg-accent-blue text-white text-sm rounded-btn hover:opacity-90">บันทึก</button>;
}

function VersionForm({ cfg, onSave }: { cfg: Record<string, unknown>; onSave: (d: Record<string, unknown>) => void }) {
  const [v, setV] = useState(String(cfg.app_latest_version || ""));
  const [f, setF] = useState(String(cfg.force_update_below || ""));
  const [u, setU] = useState(String(cfg.app_download_url || ""));
  const [n, setN] = useState(String(cfg.app_update_notes || ""));
  return <div className="space-y-3 max-w-md">
    <Field label="เวอร์ชันล่าสุด"><Input value={v} onChange={setV} placeholder="2.0.0" /></Field>
    <Field label="บังคับอัปเดตต่ำกว่า"><Input value={f} onChange={setF} placeholder="1.9.0" /></Field>
    <Field label="ลิงก์ดาวน์โหลด"><Input value={u} onChange={setU} placeholder="https://..." /></Field>
    <Field label="หมายเหตุอัปเดต"><Input value={n} onChange={setN} /></Field>
    <SaveBtn onClick={() => onSave({ app_latest_version: v, force_update_below: f, app_download_url: u, app_update_notes: n })} />
  </div>;
}

function RatesForm({ cfg, onSave }: { cfg: Record<string, unknown>; onSave: (d: Record<string, unknown>) => void }) {
  const rates = (cfg.credit_rates || {}) as Record<string, number>;
  const [er, setEr] = useState(String(cfg.exchange_rate || 4));
  const [istockPhoto, setIstockPhoto] = useState(String(rates.istock_photo || rates.istock || 3));
  const [istockVideo, setIstockVideo] = useState(String(rates.istock_video || rates.istock || 3));
  const [adobePhoto, setAdobePhoto] = useState(String(rates.adobe_photo || rates.adobe || 2));
  const [adobeVideo, setAdobeVideo] = useState(String(rates.adobe_video || rates.adobe || 2));
  const [ssPhoto, setSsPhoto] = useState(String(rates.shutterstock_photo || rates.shutterstock || 2));
  const [ssVideo, setSsVideo] = useState(String(rates.shutterstock_video || rates.shutterstock || 2));
  return <div className="space-y-5 max-w-md">
    <Field label="อัตราแลกเปลี่ยน (1 บาท = ? เครดิต)"><Input value={er} onChange={setEr} type="number" /></Field>
    <div className="border border-bdr rounded-input p-3 space-y-2">
      <p className="text-xs font-semibold text-txt-secondary">iStock</p>
      <div className="grid grid-cols-2 gap-3">
        <Field label="ภาพนิ่ง (เครดิต/ไฟล์)"><Input value={istockPhoto} onChange={setIstockPhoto} type="number" /></Field>
        <Field label="วีดีโอ (เครดิต/ไฟล์)"><Input value={istockVideo} onChange={setIstockVideo} type="number" /></Field>
      </div>
    </div>
    <div className="border border-bdr rounded-input p-3 space-y-2">
      <p className="text-xs font-semibold text-txt-secondary">Adobe</p>
      <div className="grid grid-cols-2 gap-3">
        <Field label="ภาพนิ่ง (เครดิต/ไฟล์)"><Input value={adobePhoto} onChange={setAdobePhoto} type="number" /></Field>
        <Field label="วีดีโอ (เครดิต/ไฟล์)"><Input value={adobeVideo} onChange={setAdobeVideo} type="number" /></Field>
      </div>
    </div>
    <div className="border border-bdr rounded-input p-3 space-y-2">
      <p className="text-xs font-semibold text-txt-secondary">Shutterstock</p>
      <div className="grid grid-cols-2 gap-3">
        <Field label="ภาพนิ่ง (เครดิต/ไฟล์)"><Input value={ssPhoto} onChange={setSsPhoto} type="number" /></Field>
        <Field label="วีดีโอ (เครดิต/ไฟล์)"><Input value={ssVideo} onChange={setSsVideo} type="number" /></Field>
      </div>
    </div>
    <SaveBtn onClick={() => onSave({
      exchange_rate: Number(er),
      credit_rates: {
        istock_photo: Number(istockPhoto), istock_video: Number(istockVideo),
        adobe_photo: Number(adobePhoto), adobe_video: Number(adobeVideo),
        shutterstock_photo: Number(ssPhoto), shutterstock_video: Number(ssVideo),
      }
    })} />
  </div>;
}

function BankForm({ cfg, onSave }: { cfg: Record<string, unknown>; onSave: (d: Record<string, unknown>) => void }) {
  const bank = (cfg.bank_info || {}) as Record<string, string>;
  const [bn, setBn] = useState(bank.bank_name || "");
  const [an, setAn] = useState(bank.account_number || "");
  const [am, setAm] = useState(bank.account_name || "");
  return <div className="space-y-3 max-w-md">
    <Field label="ชื่อธนาคาร"><Input value={bn} onChange={setBn} placeholder="กสิกรไทย" /></Field>
    <Field label="เลขบัญชี"><Input value={an} onChange={setAn} placeholder="xxx-x-xxxxx-x" /></Field>
    <Field label="ชื่อบัญชี"><Input value={am} onChange={setAm} /></Field>
    <SaveBtn onClick={() => onSave({ bank_name: bn, account_number: an, account_name: am })} />
  </div>;
}

function ProcessingForm({ cfg, onSave }: { cfg: Record<string, unknown>; onSave: (d: Record<string, unknown>) => void }) {
  const [ct, setCt] = useState(String(cfg.context_cache_threshold || 20));
  const [mi, setMi] = useState(String(cfg.max_concurrent_images || 5));
  const [mv, setMv] = useState(String(cfg.max_concurrent_videos || 2));
  return <div className="space-y-3 max-w-md">
    <Field label="Context Cache Threshold"><Input value={ct} onChange={setCt} type="number" /></Field>
    <Field label="Max Concurrent Images"><Input value={mi} onChange={setMi} type="number" /></Field>
    <Field label="Max Concurrent Videos"><Input value={mv} onChange={setMv} type="number" /></Field>
    <SaveBtn onClick={() => onSave({ context_cache_threshold: Number(ct), max_concurrent_images: Number(mi), max_concurrent_videos: Number(mv) })} />
  </div>;
}

function MaintenanceForm({ cfg, onSave }: { cfg: Record<string, unknown>; onSave: (d: Record<string, unknown>) => void }) {
  const [on, setOn] = useState(Boolean(cfg.maintenance_mode));
  const [msg, setMsg] = useState(String(cfg.maintenance_message || ""));
  return <div className="space-y-4 max-w-md">
    <div className="flex items-center justify-between">
      <span className="text-sm text-txt-primary">โหมดปิดปรับปรุง</span>
      <button onClick={() => setOn(!on)} className={cn("w-12 h-6 rounded-full transition-colors relative", on ? "bg-accent-red" : "bg-border")}>
        <div className={cn("w-5 h-5 rounded-full bg-white absolute top-0.5 transition-all", on ? "left-6" : "left-0.5")} />
      </button>
    </div>
    {on && <div className="p-3 bg-accent-red/5 border border-accent-red/20 rounded-btn text-xs text-accent-red">⚠️ ผู้ใช้ทุกคนจะไม่สามารถใช้งานได้</div>}
    <Field label="ข้อความแจ้ง"><Input value={msg} onChange={setMsg} placeholder="ระบบปิดปรับปรุงชั่วคราว..." /></Field>
    <SaveBtn onClick={() => onSave({ maintenance_mode: on, maintenance_message: msg })} />
  </div>;
}

function PromptsForm({ cfg, onReload, setMsg }: { cfg: Record<string, unknown>; onReload: () => void; setMsg: (s: string) => void }) {
  const prompts = (cfg.prompts || {}) as Record<string, string>;
  const [key, setKey] = useState<"istock" | "hybrid" | "single">("istock");
  const [content, setContent] = useState(prompts[key] || "");
  useEffect(() => { setContent(prompts[key] || ""); }, [key, prompts]);
  const doSave = async () => {
    try {
      const res = await updatePrompt(key, content) as { message: string };
      setMsg(res.message); onReload();
    } catch (e: unknown) { setMsg(e instanceof Error ? e.message : "Error"); }
  };
  return <div className="space-y-3">
    <div className="flex gap-2">
      {(["istock", "hybrid", "single"] as const).map((k) => (
        <button key={k} onClick={() => setKey(k)} className={cn("px-3 py-1.5 text-xs rounded-btn border", key === k ? "bg-accent-blue/10 text-accent-blue border-accent-blue/20" : "text-txt-muted border-bdr")}>{k}</button>
      ))}
    </div>
    <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={12} className="w-full px-3 py-2 bg-bg-input border border-bdr rounded-input text-sm text-txt-primary font-mono resize-y" />
    <SaveBtn onClick={doSave} />
  </div>;
}

function BlacklistForm({ cfg, onSave }: { cfg: Record<string, unknown>; onSave: (d: Record<string, unknown>) => void }) {
  const [terms, setTerms] = useState((cfg.blacklist as string[] || []).join("\n"));
  return <div className="space-y-3">
    <p className="text-xs text-txt-muted">คำต้องห้าม (บรรทัดละ 1 คำ)</p>
    <textarea value={terms} onChange={(e) => setTerms(e.target.value)} rows={10} className="w-full px-3 py-2 bg-bg-input border border-bdr rounded-input text-sm text-txt-primary font-mono resize-y" />
    <div className="flex items-center gap-3">
      <SaveBtn onClick={() => onSave({ terms: terms.split("\n").map((t) => t.trim()).filter(Boolean) })} />
      <span className="text-xs text-txt-muted">{terms.split("\n").filter((t) => t.trim()).length} คำ</span>
    </div>
  </div>;
}

function DictionaryForm({ setMsg }: { setMsg: (s: string) => void }) {
  const [words, setWords] = useState("");
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const res = await getDictionary();
      setWords((res.words || []).join("\n"));
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const doSave = async () => {
    try {
      const list = words.split("\n").map((w) => w.trim()).filter(Boolean);
      const res = await updateDictionary(list);
      setMsg(res.message);
    } catch (e: unknown) { setMsg(e instanceof Error ? e.message : "Error"); }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      const newWords = text.split("\n").map((w) => w.trim()).filter(Boolean);
      const existing = words.split("\n").map((w) => w.trim()).filter(Boolean);
      const merged = Array.from(new Set([...existing, ...newWords])).sort();
      setWords(merged.join("\n"));
      setMsg(`นำเข้า ${newWords.length} คำ (รวมทั้งหมด ${merged.length} คำ)`);
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  const handleExport = () => {
    const blob = new Blob([words], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "dictionary.txt"; a.click();
    URL.revokeObjectURL(url);
  };

  const wordList = words.split("\n").filter((w) => w.trim());
  const filtered = search ? wordList.filter((w) => w.toLowerCase().includes(search.toLowerCase())) : wordList;

  if (loading) return <div className="text-sm text-txt-muted">กำลังโหลด...</div>;

  return <div className="space-y-3">
    <div className="flex items-center justify-between flex-wrap gap-2">
      <p className="text-xs text-txt-muted">พจนานุกรมคีย์เวิร์ด (บรรทัดละ 1 คำ)</p>
      <div className="flex gap-2">
        <label className="px-3 py-1.5 text-xs bg-accent-purple/10 text-accent-purple border border-accent-purple/20 rounded-btn cursor-pointer hover:bg-accent-purple/20">
          อัปโหลด .txt
          <input type="file" accept=".txt" onChange={handleFileUpload} className="hidden" />
        </label>
        <button onClick={handleExport} className="px-3 py-1.5 text-xs bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20 rounded-btn hover:bg-accent-cyan/20">
          ส่งออก .txt
        </button>
      </div>
    </div>
    <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="ค้นหาคำ..." className="w-full px-3 py-2 bg-bg-input border border-bdr rounded-input text-sm text-txt-primary" />
    {search ? (
      <div className="bg-bg-input border border-bdr rounded-input p-3 max-h-64 overflow-y-auto">
        {filtered.length === 0 ? <p className="text-xs text-txt-muted">ไม่พบคำที่ค้นหา</p> : (
          <div className="flex flex-wrap gap-1.5">
            {filtered.map((w, i) => <span key={i} className="px-2 py-0.5 text-xs bg-accent-blue/10 text-accent-blue rounded">{w}</span>)}
          </div>
        )}
      </div>
    ) : (
      <textarea value={words} onChange={(e) => setWords(e.target.value)} rows={14} className="w-full px-3 py-2 bg-bg-input border border-bdr rounded-input text-sm text-txt-primary font-mono resize-y" />
    )}
    <div className="flex items-center gap-3">
      <SaveBtn onClick={doSave} />
      <span className="text-xs text-txt-muted">{wordList.length} คำ{search && filtered.length !== wordList.length ? ` (แสดง ${filtered.length})` : ""}</span>
    </div>
  </div>;
}
