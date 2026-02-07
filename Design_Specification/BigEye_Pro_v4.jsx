import { useState, useCallback } from "react";

const C = {
  bg: "#1A1A2E", surface: "#16213E", surfaceAlt: "#0F3460",
  border: "#1A3A6B", borderLight: "#264773",
  text: "#E8E8E8", textSec: "#8892A8", textDim: "#4A5568",
  accent: "#FF00CC", accent2: "#7B2FFF",
  success: "#00E396", warning: "#FEB019", error: "#FF4560",
  credit: "#FFD700", blue: "#00B4D8",
};
const grad = `linear-gradient(135deg, ${C.accent}, ${C.accent2})`;
const gradSubtle = `linear-gradient(135deg, ${C.accent}18, ${C.accent2}18)`;

const sampleImages = Array.from({ length: 12 }, (_, i) => ({
  url: `https://picsum.photos/seed/be${i + 20}/400/400`,
  preview: `https://picsum.photos/seed/be${i + 20}/600/400`,
}));

const mockFiles = [
  { name: "IMG_001.jpg", type: "photo", status: "completed", img: 0, title: "Professional woman working at modern office desk with laptop", desc: "A young professional businesswoman focused on her work at a clean, modern office desk with a laptop computer and coffee cup, natural lighting from large windows", keywords: "Woman, Professional, Office, Business, Work, Modern, Desk, Laptop, Technology, Corporate, Businesswoman, Workspace, Indoor, Computer, Focus, Concentration, Career, Job, Employee, Productivity, Natural Light, Window, Coffee, Contemporary, Young Adult, White Collar, Success, Confident, Working, Digital, Workplace, Occupation, Lifestyle, Clean, Bright, Minimalist, Sitting, Table, Achievement, Ambition, Commitment, Determination, Entrepreneur" },
  { name: "IMG_002.jpg", type: "photo", status: "completed", img: 1, title: "Colorful tropical sunset over calm ocean waves", desc: "Breathtaking tropical sunset with vibrant orange and purple colors reflecting on calm ocean waves at a pristine beach destination", keywords: "Sunset, Tropical, Ocean, Beach, Waves, Sky, Colorful, Orange, Purple, Horizon, Sea, Water, Nature, Landscape, Travel, Vacation, Paradise, Calm, Peaceful, Scenic, Coast, Shore, Dusk, Evening, Beautiful, Dramatic, Reflection, Seascape, Summer, Destination, Idyllic, Tranquil, Romantic, Golden Hour, Coastline, Sand, Warm, Vibrant, Exotic, Island, Relaxation, Tourism" },
  { name: "IMG_003.jpg", type: "photo", status: "processing", img: 2 },
  { name: "VID_001.mp4", type: "video", status: "error", img: 3, error: "[RATE_LIMIT] Too many requests, please wait" },
  { name: "IMG_004.jpg", type: "photo", status: "pending", img: 4 },
  { name: "IMG_005.jpg", type: "photo", status: "pending", img: 5 },
  { name: "VID_002.mp4", type: "video", status: "pending", img: 6 },
  { name: "IMG_006.jpg", type: "photo", status: "pending", img: 7 },
  { name: "IMG_007.jpg", type: "photo", status: "completed", img: 8, title: "Fresh organic vegetables at farmers market display", desc: "Colorful assortment of fresh organic vegetables beautifully arranged at a local farmers market stall", keywords: "Vegetables, Fresh, Organic, Market, Food, Healthy, Colorful, Agriculture, Farm, Produce, Natural, Green, Tomato, Pepper, Lettuce, Carrot, Diet, Nutrition, Vegan, Vegetarian, Local, Seasonal, Raw, Harvest, Display, Stall, Shopping, Grocery, Ingredient, Cooking, Kitchen, Salad, Eco, Sustainable, Arrangement, Variety, Assortment, Abundance, Ripe, Quality, Premium, Selection, Wholesome" },
  { name: "IMG_008.jpg", type: "photo", status: "pending", img: 9 },
  { name: "IMG_009.jpg", type: "photo", status: "pending", img: 10 },
  { name: "VID_003.mp4", type: "video", status: "pending", img: 11 },
];

const mockHistory = [
  { date: "07/02 14:42", desc: "Refund 5 failed files", amount: +15 },
  { date: "07/02 14:35", desc: "iStock 50 files", amount: -150 },
  { date: "07/02 14:30", desc: "Top-up 100 THB", amount: +400 },
  { date: "06/02 09:00", desc: "Top-up 300 THB", amount: +1200 },
  { date: "05/02 16:22", desc: "Refund 3 failed", amount: +6 },
  { date: "05/02 16:10", desc: "Adobe 30 files", amount: -60 },
  { date: "04/02 11:00", desc: "Top-up 50 THB", amount: +200 },
];

// ═══════════════════════════════════════
// HOVER BUTTON (Save/Clear with theme hover)
// ═══════════════════════════════════════
function HoverBtn({ children, style = {}, ...props }) {
  const [hovered, setHovered] = useState(false);
  return (
    <button
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        ...btnBase,
        background: hovered ? gradSubtle : "transparent",
        borderColor: hovered ? C.accent + "66" : C.border,
        color: hovered ? C.accent : C.textSec,
        transform: hovered ? "translateY(-1px)" : "none",
        boxShadow: hovered ? `0 4px 12px ${C.accent}15` : "none",
        transition: "all .2s ease",
        ...style,
      }}
      {...props}
    >
      {children}
    </button>
  );
}

// ═══════════════════════════════════════
// CSV WARNING BANNER
// ═══════════════════════════════════════
function CsvWarningBanner({ onDismiss }) {
  return (
    <div style={{
      background: `linear-gradient(135deg, ${C.warning}15, ${C.warning}08)`,
      border: `1px solid ${C.warning}33`,
      borderRadius: 10, padding: "12px 14px", marginBottom: 10,
      display: "flex", gap: 10, alignItems: "flex-start",
    }}>
      <span style={{ fontSize: 18, flexShrink: 0, lineHeight: 1 }}>⚠️</span>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: C.warning, marginBottom: 3 }}>Review Before Uploading</div>
        <div style={{ fontSize: 11, color: C.textSec, lineHeight: 1.5 }}>
          AI-generated metadata may contain inaccuracies. Please review all titles, descriptions, and keywords carefully before submitting to stock platforms.
        </div>
      </div>
      <button onClick={onDismiss} style={{ background: "none", border: "none", color: C.textDim, cursor: "pointer", fontSize: 14, padding: 0, lineHeight: 1 }}>✕</button>
    </div>
  );
}

// ═══════════════════════════════════════
// THUMBNAIL
// ═══════════════════════════════════════
function Thumb({ file, selected, onClick }) {
  const [loaded, setLoaded] = useState(false);
  const imgUrl = sampleImages[file.img]?.url;
  const isVid = file.type === "video";
  return (
    <div onClick={onClick} style={{
      width: 130, height: 130, borderRadius: 10, overflow: "hidden", cursor: "pointer", position: "relative",
      border: selected ? `2px solid ${C.accent}` : file.status === "processing" ? `2px solid ${C.warning}` : "2px solid transparent",
      background: C.surface, transition: "all .15s", flexShrink: 0,
      boxShadow: selected ? `0 0 20px ${C.accent}33` : "0 2px 8px #0003",
    }}>
      <img src={imgUrl} alt="" onLoad={() => setLoaded(true)} style={{ width: "100%", height: "100%", objectFit: "cover", display: loaded ? "block" : "none", filter: file.status === "error" ? "brightness(0.5) saturate(0.5)" : file.status === "processing" ? "brightness(0.7)" : "none" }} />
      {!loaded && <div style={{ width: "100%", height: "100%", background: C.surfaceAlt, display: "flex", alignItems: "center", justifyContent: "center" }}><span style={{ fontSize: 24, opacity: 0.3 }}>{isVid ? "🎬" : "🖼"}</span></div>}
      {isVid && loaded && <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", pointerEvents: "none" }}><div style={{ width: 30, height: 30, borderRadius: "50%", background: "#000a", display: "flex", alignItems: "center", justifyContent: "center" }}><div style={{ width: 0, height: 0, borderLeft: "9px solid #fffd", borderTop: "5px solid transparent", borderBottom: "5px solid transparent", marginLeft: 2 }} /></div></div>}
      <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, padding: "14px 6px 5px", background: "linear-gradient(transparent, #000c)", display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <span style={{ fontSize: 9, color: "#fffc", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 90 }}>{file.name}</span>
        <span style={{ fontSize: 9, background: isVid ? "#7B2FFF99" : "#00B4D855", borderRadius: 3, padding: "1px 4px", color: "#fffd" }}>{isVid ? "VID" : "IMG"}</span>
      </div>
      {file.status === "completed" && <div style={{ position: "absolute", top: 6, right: 6, width: 20, height: 20, borderRadius: "50%", background: C.success, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, color: "#fff", fontWeight: 700, boxShadow: `0 2px 8px ${C.success}66` }}>✓</div>}
      {file.status === "processing" && <div style={{ position: "absolute", inset: 0, background: "#00000044", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 4 }}><div style={{ width: 28, height: 28, border: `3px solid ${C.warning}`, borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} /><span style={{ fontSize: 9, color: C.warning, fontWeight: 600 }}>Processing</span></div>}
      {file.status === "error" && <div style={{ position: "absolute", top: 6, right: 6, width: 20, height: 20, borderRadius: "50%", background: C.error, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, color: "#fff", fontWeight: 700, boxShadow: `0 2px 8px ${C.error}66` }}>✕</div>}
    </div>
  );
}

// ═══════════════════════════════════════
// SHARED
// ═══════════════════════════════════════
function Section({ title, children }) {
  return <div style={{ marginBottom: 4 }}><div style={{ fontSize: 10, fontWeight: 600, color: C.textSec, textTransform: "uppercase", letterSpacing: 1.2, marginBottom: 10, display: "flex", alignItems: "center", gap: 6 }}><div style={{ height: 1, flex: 1, background: C.border }} /><span>{title}</span><div style={{ height: 1, flex: 1, background: C.border }} /></div>{children}</div>;
}
function SmallLabel({ text }) { return <div style={{ fontSize: 11, color: C.textSec, marginTop: 10, marginBottom: 4, fontWeight: 500 }}>{text}</div>; }
function SliderRow({ label, value, onChange, min, max }) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}><span style={{ color: C.textSec }}>{label}</span><span style={{ color: C.text, fontWeight: 600 }}>{value}</span></div>
      <div style={{ position: "relative", height: 20, display: "flex", alignItems: "center" }}>
        <div style={{ position: "absolute", left: 0, right: 0, height: 4, background: C.border, borderRadius: 2 }} />
        <div style={{ position: "absolute", left: 0, width: `${pct}%`, height: 4, background: grad, borderRadius: 2 }} />
        <input type="range" min={min} max={max} value={value} onChange={e => onChange(+e.target.value)} style={{ position: "absolute", width: "100%", opacity: 0, cursor: "pointer", height: 20, margin: 0 }} />
        <div style={{ position: "absolute", left: `calc(${pct}% - 7px)`, width: 14, height: 14, borderRadius: "50%", background: C.accent, boxShadow: `0 0 8px ${C.accent}66`, pointerEvents: "none" }} />
      </div>
    </div>
  );
}
function InfoCard({ title, children }) {
  return <div style={{ background: C.surface, borderRadius: 10, padding: 14, border: `1px solid ${C.border}33` }}>{title && <div style={{ fontSize: 12, fontWeight: 600, color: C.textSec, marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 }}>{title}</div>}<div style={{ display: "flex", flexDirection: "column", gap: 5 }}>{children}</div></div>;
}
function Row({ l, r }) { return <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: C.text }}><span style={{ color: C.textSec }}>{l}</span><span>{r}</span></div>; }

// ═══════════════════════════════════════
// DIALOGS
// ═══════════════════════════════════════
function Dialog({ title, children, onClose, width = 440 }) {
  return (
    <div style={{ position: "fixed", inset: 0, background: "#000b", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 999, backdropFilter: "blur(4px)" }}>
      <div style={{ width, background: C.bg, borderRadius: 16, border: `1px solid ${C.border}`, padding: 28, boxShadow: `0 24px 80px #000a` }}>
        <div style={{ fontSize: 17, fontWeight: 700, marginBottom: 18 }}>{title}</div>
        {children}
        {onClose && <button onClick={onClose} style={{ ...btnBase, marginTop: 18, width: "100%", justifyContent: "center" }}>Close</button>}
      </div>
    </div>
  );
}
function SummaryDialog({ onClose }) {
  return (
    <Dialog title="✅ Processing Complete" onClose={onClose}>
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <InfoCard title="Results"><Row l="Successful" r={<span style={{ color: C.success, fontWeight: 600 }}>9 files</span>} /><Row l="Failed" r={<span style={{ color: C.error, fontWeight: 600 }}>1 file</span>} /><Row l="Breakdown" r="📸 8 photos · 🎬 2 videos" /></InfoCard>
        <InfoCard title="Credits"><Row l="Charged" r="30 cr" /><Row l="Refunded" r={<span style={{ color: C.success }}>+3 cr</span>} /><Row l="Net cost" r="27 cr" /><div style={{ borderTop: `1px solid ${C.border}`, marginTop: 6, paddingTop: 6 }}><Row l="Balance" r={<span style={{ color: C.credit, fontWeight: 700 }}>1,173 credits</span>} /></div></InfoCard>
        <InfoCard title="CSV Files"><div style={{ fontSize: 12 }}>✅ iStock_Photos_gemini-2.5_20260207.csv</div><div style={{ fontSize: 12 }}>✅ iStock_Videos_gemini-2.5_20260207.csv</div></InfoCard>
        {/* CSV Warning in summary too */}
        <div style={{ background: `${C.warning}0D`, border: `1px solid ${C.warning}22`, borderRadius: 8, padding: 12, display: "flex", gap: 8, alignItems: "flex-start" }}>
          <span style={{ fontSize: 14 }}>💡</span>
          <div style={{ fontSize: 11, color: C.textSec, lineHeight: 1.5 }}>
            Remember to review all metadata before uploading to stock platforms. AI results may need manual adjustments for best acceptance rates.
          </div>
        </div>
      </div>
    </Dialog>
  );
}
function HistoryDialog({ onClose }) {
  return (
    <Dialog title="📜 Credit History" onClose={onClose} width={520}>
      <div style={{ maxHeight: 300, overflowY: "auto", borderRadius: 8, border: `1px solid ${C.border}` }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead><tr style={{ background: C.surface }}>{["Date","Transaction","Amount"].map(h => <th key={h} style={{ padding: "10px 12px", textAlign: h === "Amount" ? "right" : "left", color: C.textSec, fontWeight: 600, fontSize: 11, textTransform: "uppercase" }}>{h}</th>)}</tr></thead>
          <tbody>{mockHistory.map((h, i) => <tr key={i} style={{ borderTop: `1px solid ${C.border}33` }}><td style={{ padding: "9px 12px", color: C.textDim, fontSize: 12 }}>{h.date}</td><td style={{ padding: "9px 12px", fontSize: 12 }}>{h.desc}</td><td style={{ padding: "9px 12px", textAlign: "right", fontWeight: 700, color: h.amount > 0 ? C.success : C.error }}>{h.amount > 0 ? "+" : ""}{h.amount}</td></tr>)}</tbody>
        </table>
      </div>
      <div style={{ marginTop: 14, padding: 12, background: gradSubtle, borderRadius: 8, textAlign: "center", fontSize: 13 }}>Balance: <span style={{ color: C.credit, fontWeight: 700, fontSize: 16 }}>1,200 credits</span></div>
    </Dialog>
  );
}
function TopUpDialog({ onClose }) {
  const [status, setStatus] = useState(null);
  return (
    <Dialog title="🪙 Top Up Credits" onClose={onClose} width={460}>
      <div style={{ display: "flex", flexDirection: "column", gap: 14, fontSize: 13 }}>
        <InfoCard title="Transfer To"><div style={{ fontWeight: 600 }}>🏦 Kasikornbank xxx-x-xxxxx-x</div><div style={{ color: C.textSec, marginTop: 2 }}>Account: XXXXX XXXXX</div><div style={{ color: C.credit, marginTop: 6, fontSize: 12, fontWeight: 600 }}>Rate: 1 THB = 4 Credits</div></InfoCard>
        <div onClick={() => !status && setStatus("checking")} style={{ border: `2px dashed ${C.borderLight}`, borderRadius: 12, padding: 28, textAlign: "center", cursor: "pointer", background: status ? C.surface : "transparent" }}>
          {!status ? <><div style={{ fontSize: 24, marginBottom: 6, opacity: 0.6 }}>📎</div><div style={{ color: C.textSec }}>Drop payment slip here</div><div style={{ fontSize: 11, color: C.textDim, marginTop: 2 }}>or click to browse</div></> : <div style={{ color: C.textSec }}>📄 slip_20260207.jpg</div>}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, color: C.textSec }}><span>Amount:</span><input placeholder="100" style={{ ...inputBase, width: 80, textAlign: "center" }} /><span>THB</span></div>
        <button onClick={() => { setStatus("checking"); setTimeout(() => setStatus("success"), 1800); }} style={{ ...pillBtnStyle, opacity: status === "checking" ? 0.6 : 1 }}>{status === "checking" ? "⏳ Verifying..." : "Submit Slip"}</button>
        {status === "success" && <div style={{ textAlign: "center", color: C.success, fontWeight: 600, padding: 8, background: C.success + "11", borderRadius: 8 }}>✅ 400 credits added!</div>}
      </div>
    </Dialog>
  );
}
function ConfirmDialog({ onClose, onConfirm }) {
  return (
    <Dialog title="Confirm Processing" width={400}>
      <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 13 }}>
        <InfoCard><Row l="Files" r="12 (9 photos, 3 videos)" /><Row l="Model" r="gemini-2.5-pro" /><Row l="Platform" r="iStock" /></InfoCard>
        <InfoCard><Row l="Cost" r={<span style={{ color: C.credit, fontWeight: 700 }}>36 credits</span>} /><Row l="After deduction" r={<span style={{ fontWeight: 600 }}>1,164 credits</span>} /></InfoCard>
      </div>
      <div style={{ display: "flex", gap: 10, marginTop: 20 }}>
        <button onClick={onConfirm} style={{ ...pillBtnStyle, flex: 1 }}>Start</button>
        <button onClick={onClose} style={{ ...btnBase, flex: 1, justifyContent: "center" }}>Cancel</button>
      </div>
    </Dialog>
  );
}

// ═══════════════════════════════════════
// EXPORT CSV CONFIRMATION DIALOG
// ═══════════════════════════════════════
function ExportCsvDialog({ onClose, onExport }) {
  return (
    <Dialog title="💾 Export CSV" width={440}>
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {/* Warning */}
        <div style={{
          background: `linear-gradient(135deg, ${C.warning}12, ${C.warning}06)`,
          border: `1px solid ${C.warning}33`, borderRadius: 12, padding: 16,
          display: "flex", gap: 12, alignItems: "flex-start",
        }}>
          <div style={{ fontSize: 28, lineHeight: 1, flexShrink: 0 }}>⚠️</div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: C.warning, marginBottom: 6 }}>Please Review Before Uploading</div>
            <div style={{ fontSize: 12, color: C.textSec, lineHeight: 1.6 }}>
              AI-generated metadata may contain errors or inaccuracies. We strongly recommend reviewing all titles, descriptions, and keywords before submitting to stock platforms to ensure the best acceptance rates and avoid potential rejections.
            </div>
          </div>
        </div>

        {/* Checklist */}
        <div style={{ background: C.surface, borderRadius: 10, padding: 14, border: `1px solid ${C.border}33` }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: C.textSec, marginBottom: 10, textTransform: "uppercase" }}>Quick Checklist</div>
          {[
            "Titles accurately describe the content",
            "Descriptions are relevant and detailed",
            "Keywords don't contain trademarked terms",
          ].map((item, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 0", fontSize: 12, color: C.textSec }}>
              <div style={{ width: 16, height: 16, borderRadius: 4, border: `1px solid ${C.border}`, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9 }}>
              </div>
              {item}
            </div>
          ))}
        </div>

        <div style={{ display: "flex", gap: 10 }}>
          <button onClick={onExport} style={{ ...pillBtnStyle, flex: 1 }}>Export CSV</button>
          <button onClick={onClose} style={{ ...btnBase, flex: 1, justifyContent: "center" }}>Cancel</button>
        </div>
      </div>
    </Dialog>
  );
}

// ═══════════════════════════════════════
// AUTH
// ═══════════════════════════════════════
function AuthWindow({ onLogin }) {
  const [tab, setTab] = useState("login");
  const [loading, setLoading] = useState(false);
  const go = () => { setLoading(true); setTimeout(() => { setLoading(false); onLogin(); }, 1000); };
  return (
    <div style={{ width: 400, background: C.bg, borderRadius: 20, padding: 36, boxShadow: `0 32px 80px #000a, 0 0 0 1px ${C.border}`, position: "relative", overflow: "hidden" }}>
      <div style={{ position: "absolute", top: -60, right: -60, width: 160, height: 160, borderRadius: "50%", background: `${C.accent}08`, filter: "blur(40px)" }} />
      <div style={{ textAlign: "center", marginBottom: 30 }}>
        <div style={{ fontSize: 30, fontWeight: 900, background: grad, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", letterSpacing: 5 }}>BIGEYE PRO</div>
        <div style={{ color: C.textDim, fontSize: 11, letterSpacing: 1, marginTop: 4 }}>STOCK METADATA GENERATOR</div>
      </div>
      <div style={{ display: "flex", marginBottom: 24, borderRadius: 10, overflow: "hidden", border: `1px solid ${C.border}` }}>
        {["login","register"].map(t => <button key={t} onClick={() => setTab(t)} style={{ flex: 1, padding: "11px 0", border: "none", cursor: "pointer", fontSize: 12, fontWeight: 600, letterSpacing: 0.5, background: tab === t ? `${C.accent}15` : "transparent", color: tab === t ? C.accent : C.textDim }}>{t === "login" ? "SIGN IN" : "REGISTER"}</button>)}
      </div>
      {tab === "login" ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <input placeholder="Email" style={inputBase} /><input placeholder="Password" type="password" style={inputBase} />
          <button onClick={go} disabled={loading} style={{ ...pillBtnStyle, marginTop: 4, opacity: loading ? 0.6 : 1 }}>{loading ? "Signing in..." : "Sign In"}</button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <input placeholder="Full Name" style={inputBase} /><input placeholder="Email" style={inputBase} /><input placeholder="Phone Number" style={inputBase} /><input placeholder="Password" type="password" style={inputBase} /><input placeholder="Confirm Password" type="password" style={inputBase} />
          <button onClick={go} disabled={loading} style={{ ...pillBtnStyle, marginTop: 4, opacity: loading ? 0.6 : 1 }}>{loading ? "Creating..." : "Create Account"}</button>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════
// MAIN WINDOW
// ═══════════════════════════════════════
function MainWindow() {
  const [selected, setSelected] = useState(0);
  const [dialog, setDialog] = useState(null);
  const [platform, setPlatform] = useState("iStock");
  const [kwStyle, setKwStyle] = useState("HYBRID");
  const [kwCount, setKwCount] = useState(45);
  const [titleLen, setTitleLen] = useState(70);
  const [descLen, setDescLen] = useState(200);
  const [showCsvWarn, setShowCsvWarn] = useState(true);
  const [exportToast, setExportToast] = useState(false);

  const file = mockFiles[selected];
  const isAdobe = platform.includes("Adobe");
  const rate = platform === "iStock" ? 3 : 2;
  const cost = mockFiles.length * rate;
  const photos = mockFiles.filter(f => f.type === "photo").length;
  const videos = mockFiles.filter(f => f.type === "video").length;
  const completed = mockFiles.filter(f => f.status === "completed").length;
  const pct = Math.round((completed / mockFiles.length) * 100);
  const previewUrl = sampleImages[file.img]?.preview;

  const handleExport = () => {
    setDialog(null);
    setExportToast(true);
    setTimeout(() => setExportToast(false), 4000);
  };

  return (
    <div style={{ width: "100%", height: "100vh", display: "flex", flexDirection: "column", background: C.bg, color: C.text, fontFamily: '"Segoe UI", sans-serif', fontSize: 13, overflow: "hidden", position: "relative" }}>

      {/* EXPORT SUCCESS TOAST */}
      {exportToast && (
        <div style={{
          position: "absolute", top: 60, left: "50%", transform: "translateX(-50%)", zIndex: 100,
          background: C.success + "18", border: `1px solid ${C.success}44`, borderRadius: 10,
          padding: "10px 20px", display: "flex", alignItems: "center", gap: 8,
          boxShadow: `0 8px 32px #0005`, backdropFilter: "blur(8px)",
          animation: "fadeIn .3s ease",
        }}>
          <span style={{ color: C.success, fontWeight: 600, fontSize: 13 }}>✅ CSV exported successfully!</span>
          <button onClick={() => setExportToast(false)} style={{ background: "none", border: "none", color: C.textDim, cursor: "pointer" }}>✕</button>
        </div>
      )}

      {/* TOP BAR */}
      <div style={{ height: 48, background: `linear-gradient(90deg, ${C.surface}, ${C.bg})`, borderBottom: `1px solid ${C.border}`, display: "flex", alignItems: "center", padding: "0 16px", gap: 8, flexShrink: 0 }}>
        <div style={{ fontSize: 14, fontWeight: 800, background: grad, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", letterSpacing: 2, marginRight: 12 }}>BIGEYE</div>
        <div style={{ width: 1, height: 20, background: C.border, marginRight: 4 }} />
        <span style={{ color: C.credit, fontWeight: 700, fontSize: 14 }}>💰 1,200</span>
        <span style={{ color: C.textDim, fontSize: 11 }}>credits</span>
        <button onClick={() => setDialog("topup")} style={{ ...chipBtn, background: `${C.credit}15`, color: C.credit, borderColor: `${C.credit}33` }}>Top Up</button>
        <button style={chipBtn}>↻</button>
        <button onClick={() => setDialog("history")} style={chipBtn}>History</button>
        <div style={{ flex: 1 }} />
        <span style={{ color: C.textSec, fontSize: 12 }}>Somchai J.</span>
        <button style={{ ...chipBtn, color: C.textDim }}>Logout</button>
      </div>

      {/* 3 COLUMNS */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

        {/* SIDEBAR */}
        <div style={{ width: 270, borderRight: `1px solid ${C.border}`, padding: "16px 14px", overflowY: "auto", display: "flex", flexDirection: "column", gap: 18, flexShrink: 0 }}>
          <Section title="API Key">
            <input type="password" defaultValue="AIzaSy..." style={{ ...inputBase, width: "100%", fontSize: 12 }} />
            <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
              <HoverBtn style={{ flex: 1 }}>💾 Save</HoverBtn>
              <HoverBtn style={{ flex: 1 }}>🗑 Clear</HoverBtn>
            </div>
          </Section>
          <Section title="AI Settings">
            <SmallLabel text="Model" />
            <select style={selectBase} defaultValue="gemini-2.5-pro"><option>gemini-2.5-pro</option><option>gemini-2.5-flash</option><option>gemini-2.0-flash</option></select>
            <SmallLabel text="Platform" />
            <select style={selectBase} value={platform} onChange={e => setPlatform(e.target.value)}><option value="iStock">iStock (3 cr/file)</option><option value="Adobe & Shutterstock">Adobe & Shutterstock (2 cr/file)</option></select>
            {isAdobe && <><SmallLabel text="Keyword Style" /><select style={selectBase} value={kwStyle} onChange={e => setKwStyle(e.target.value)}><option value="HYBRID">Hybrid (Phrase & Single)</option><option value="Single">Single Words</option></select></>}
          </Section>
          <Section title="Metadata">
            <SliderRow label="Keywords" value={kwCount} onChange={setKwCount} min={10} max={50} />
            <SliderRow label="Title Length" value={titleLen} onChange={setTitleLen} min={50} max={200} />
            <SliderRow label="Description" value={descLen} onChange={setDescLen} min={100} max={500} />
          </Section>
          <button style={{ ...btnBase, marginTop: "auto", justifyContent: "center", color: C.textDim, fontSize: 11 }}>📋 Debug Log</button>
        </div>

        {/* CENTER */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ padding: "10px 16px", borderBottom: `1px solid ${C.border}`, display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
            <button style={btnBase}>📂 Open Folder</button>
            <div style={{ flex: 1, background: C.surface, borderRadius: 6, padding: "7px 12px", fontSize: 12, color: C.textDim, border: `1px solid ${C.border}`, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>/Users/photographer/stock_photos</div>
            <span style={{ color: C.textSec, fontSize: 12, whiteSpace: "nowrap", fontWeight: 500 }}>📸{photos} 🎬{videos}</span>
          </div>
          <div style={{ flex: 1, padding: 14, overflowY: "auto", display: "flex", flexWrap: "wrap", gap: 10, alignContent: "flex-start" }}>
            {mockFiles.map((f, i) => <Thumb key={i} file={f} selected={selected === i} onClick={() => setSelected(i)} />)}
          </div>
          <div style={{ borderTop: `1px solid ${C.border}`, flexShrink: 0 }}>
            <div style={{ padding: "8px 16px", fontSize: 12, color: C.textSec, display: "flex", alignItems: "center", gap: 16, background: `${C.surface}88` }}>
              <span>📁 {mockFiles.length} files</span>
              <span style={{ color: C.text, fontWeight: 600 }}>≈ {cost} credits</span>
              <span style={{ color: C.textDim }}>({platform.split(" ")[0]} × {rate})</span>
              <span style={{ marginLeft: "auto", color: C.success, fontWeight: 500 }}>✓ Sufficient</span>
            </div>
            <div style={{ padding: "12px 16px", display: "flex", flexDirection: "column", gap: 10, alignItems: "center" }}>
              <div style={{ width: "100%", display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ fontSize: 12, color: C.textSec, minWidth: 120 }}>{completed > 0 ? `Processing ${completed}/${mockFiles.length}` : "Ready"}</span>
                <div style={{ flex: 1, height: 6, background: C.surface, borderRadius: 3, overflow: "hidden" }}><div style={{ width: `${pct}%`, height: "100%", background: grad, borderRadius: 3, transition: "width .4s ease" }} /></div>
                <span style={{ fontSize: 11, color: C.textDim, minWidth: 32, textAlign: "right" }}>{pct}%</span>
              </div>
              <button onClick={() => setDialog("confirm")} style={{ ...pillBtnStyle, width: 220, padding: "12px 0", fontSize: 14, letterSpacing: 1 }}>START</button>
            </div>
          </div>
        </div>

        {/* INSPECTOR */}
        <div style={{ width: 300, borderLeft: `1px solid ${C.border}`, padding: 14, overflowY: "auto", display: "flex", flexDirection: "column", gap: 12, flexShrink: 0 }}>
          <div style={{ width: "100%", height: 190, borderRadius: 10, overflow: "hidden", border: `1px solid ${C.border}`, position: "relative", background: C.surface }}>
            <img src={previewUrl} alt="Preview" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            {file.type === "video" && <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}><div style={{ width: 44, height: 44, borderRadius: "50%", background: "#000a", display: "flex", alignItems: "center", justifyContent: "center" }}><div style={{ width: 0, height: 0, borderLeft: "14px solid #fffd", borderTop: "8px solid transparent", borderBottom: "8px solid transparent", marginLeft: 4 }} /></div></div>}
            {file.status === "completed" && <div style={{ position: "absolute", top: 8, right: 8, background: C.success, borderRadius: 12, padding: "2px 8px", fontSize: 10, fontWeight: 700 }}>✓ Done</div>}
            {file.status === "error" && <div style={{ position: "absolute", top: 8, right: 8, background: C.error, borderRadius: 12, padding: "2px 8px", fontSize: 10, fontWeight: 700 }}>Error</div>}
          </div>
          <div style={{ fontSize: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 3 }}>{file.name}</div>
            <div style={{ color: C.textDim, display: "flex", gap: 10 }}><span>{file.type === "video" ? "🎬 Video" : "📷 Photo"}</span>{file.status === "completed" && <span style={{ color: C.textSec }}>Tokens: 1,234 / 567</span>}</div>
          </div>

          {file.status === "completed" ? <>
            <div><SmallLabel text="Title" /><input defaultValue={file.title} style={{ ...inputBase, width: "100%", fontSize: 12 }} /></div>
            <div><SmallLabel text="Description" /><textarea defaultValue={file.desc} rows={3} style={{ ...inputBase, width: "100%", fontSize: 12, resize: "vertical", fontFamily: "inherit" }} /></div>
            <div><SmallLabel text={`Keywords (${(file.keywords || "").split(",").length})`} /><textarea defaultValue={file.keywords} rows={5} style={{ ...inputBase, width: "100%", fontSize: 11, resize: "vertical", fontFamily: "inherit", lineHeight: 1.5 }} /></div>
          </> : file.status === "error" ? (
            <div style={{ background: `${C.error}11`, border: `1px solid ${C.error}33`, borderRadius: 10, padding: 14, color: C.error, fontSize: 13 }}>⚠️ {file.error}</div>
          ) : file.status === "processing" ? (
            <div style={{ textAlign: "center", color: C.warning, padding: 20 }}>Processing...</div>
          ) : (
            <div style={{ textAlign: "center", color: C.textDim, padding: 20 }}>Pending</div>
          )}

          <HoverBtn
            onClick={() => setDialog("exportCsv")}
            style={{ marginTop: "auto", justifyContent: "center", width: "100%", background: `${C.blue}12`, color: C.blue, borderColor: `${C.blue}33` }}
          >
            💾 Export CSV
          </HoverBtn>
        </div>
      </div>

      {/* STATUS BAR */}
      <div style={{ height: 22, background: C.surface, borderTop: `1px solid ${C.border}`, display: "flex", alignItems: "center", padding: "0 12px", fontSize: 10, color: C.textDim, flexShrink: 0 }}><span>Ready</span><div style={{ flex: 1 }} /><span>v2.0.0</span></div>

      {/* DIALOGS */}
      {dialog === "summary" && <SummaryDialog onClose={() => setDialog(null)} />}
      {dialog === "history" && <HistoryDialog onClose={() => setDialog(null)} />}
      {dialog === "topup" && <TopUpDialog onClose={() => setDialog(null)} />}
      {dialog === "confirm" && <ConfirmDialog onClose={() => setDialog(null)} onConfirm={() => setDialog("summary")} />}
      {dialog === "exportCsv" && <ExportCsvDialog onClose={() => setDialog(null)} onExport={handleExport} />}
    </div>
  );
}

// ═══════════════════════════════════════
// ROOT
// ═══════════════════════════════════════
export default function App() {
  const [screen, setScreen] = useState("auth");
  return (
    <div style={{ width: "100%", minHeight: "100vh", background: "#0a0a14", color: "#fff", fontFamily: '"Segoe UI", sans-serif' }}>
      <div style={{ display: "flex", gap: 6, padding: "10px 16px", background: "#06060f", borderBottom: `1px solid ${C.border}`, alignItems: "center" }}>
        <span style={{ fontSize: 11, color: C.textDim, marginRight: 8 }}>Screen:</span>
        {[["auth","🔐 Login"],["main","🖥️ Main Window"]].map(([k,l]) => (
          <button key={k} onClick={() => setScreen(k)} style={{ padding: "5px 14px", borderRadius: 6, border: `1px solid ${screen === k ? C.accent : C.border}`, cursor: "pointer", fontSize: 11, fontWeight: 600, background: screen === k ? `${C.accent}18` : "transparent", color: screen === k ? C.accent : C.textDim }}>{l}</button>
        ))}
      </div>
      {screen === "auth" ? (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "calc(100vh - 44px)", background: C.bg }}>
          <AuthWindow onLogin={() => setScreen("main")} />
        </div>
      ) : <MainWindow />}
      <style>{`
        * { box-sizing: border-box; margin: 0; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: ${C.border}; border-radius: 3px; }
        input::placeholder, textarea::placeholder { color: ${C.textDim}; }
        select { appearance: auto; }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity: 0; transform: translateX(-50%) translateY(-8px); } to { opacity: 1; transform: translateX(-50%) translateY(0); } }
      `}</style>
    </div>
  );
}

const inputBase = { background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, padding: "10px 12px", color: C.text, fontSize: 13, outline: "none", width: "100%", boxSizing: "border-box" };
const selectBase = { ...inputBase, cursor: "pointer", paddingRight: 8 };
const pillBtnStyle = { background: grad, border: "none", borderRadius: 22, padding: "11px 24px", color: "#fff", fontWeight: 700, fontSize: 13, cursor: "pointer", width: "100%", letterSpacing: 0.5, textAlign: "center" };
const btnBase = { background: "transparent", border: `1px solid ${C.border}`, borderRadius: 8, padding: "7px 14px", color: C.textSec, fontSize: 12, cursor: "pointer", fontWeight: 500, display: "flex", alignItems: "center", gap: 5, whiteSpace: "nowrap" };
const chipBtn = { background: "transparent", border: `1px solid ${C.border}`, borderRadius: 6, padding: "4px 10px", color: C.textSec, fontSize: 11, cursor: "pointer", fontWeight: 500 };
