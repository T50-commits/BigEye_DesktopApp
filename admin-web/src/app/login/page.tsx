"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

const S = {
  page: { minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#f5f7fa", padding: 16, fontFamily: "'IBM Plex Sans Thai', system-ui, sans-serif" } as React.CSSProperties,
  card: { width: "100%", maxWidth: 380, background: "#ffffff", border: "1px solid #d1d9e6", borderRadius: 16, padding: 32, boxShadow: "0 8px 32px rgba(0,0,0,0.08)" } as React.CSSProperties,
  logo: { width: 48, height: 48, borderRadius: 12, background: "linear-gradient(135deg, #3b82f6, #7c3aed)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 12px", fontSize: 22, color: "#fff" } as React.CSSProperties,
  title: { textAlign: "center" as const, color: "#1a202c", fontSize: 18, fontWeight: 600, margin: 0 },
  subtitle: { textAlign: "center" as const, color: "#a0aec0", fontSize: 12, marginTop: 4, marginBottom: 32 },
  label: { display: "block", color: "#4a5568", fontSize: 12, marginBottom: 6 },
  input: { width: "100%", padding: "10px 12px", background: "#f8f9fb", border: "1px solid #d1d9e6", borderRadius: 10, color: "#1a202c", fontSize: 14, outline: "none", boxSizing: "border-box" as const, marginBottom: 16 },
  btn: { width: "100%", padding: "10px 0", background: "linear-gradient(90deg, #3b82f6, #7c3aed)", color: "#fff", fontSize: 14, fontWeight: 500, border: "none", borderRadius: 10, cursor: "pointer" } as React.CSSProperties,
  error: { color: "#dc2626", background: "rgba(220,38,38,0.06)", border: "1px solid rgba(220,38,38,0.15)", borderRadius: 10, padding: "8px 12px", fontSize: 12, marginBottom: 16 },
};

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "เข้าสู่ระบบไม่สำเร็จ");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={S.page}>
      <div style={S.card}>
        <div style={S.logo}>👁</div>
        <h1 style={S.title}>BigEye Pro Admin</h1>
        <p style={S.subtitle}>เข้าสู่ระบบจัดการ</p>

        <form onSubmit={handleSubmit}>
          <label style={S.label}>อีเมล</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={S.input}
            placeholder="admin@bigeye.pro"
          />
          <label style={S.label}>รหัสผ่าน</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={S.input}
            placeholder="••••••••"
          />
          {error && <div style={S.error}>{error}</div>}
          <button type="submit" disabled={loading} style={{ ...S.btn, opacity: loading ? 0.5 : 1 }}>
            {loading ? "กำลังเข้าสู่ระบบ..." : "เข้าสู่ระบบ"}
          </button>
        </form>
      </div>
    </div>
  );
}
