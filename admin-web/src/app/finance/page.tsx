"use client";

import { useEffect, useState } from "react";
import { getFinanceDaily, getFinanceMonthly, exportFinance } from "@/lib/api";
import { formatCurrency, formatNumber } from "@/lib/utils";
import MetricCard from "@/components/shared/MetricCard";
import LoadingSpinner from "@/components/shared/LoadingSpinner";
import { Wallet, TrendingUp, Clock, Calculator, Download } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

interface Day { date: string; topup_thb: number; topup_count: number; recognized_thb: number; recognized_credits: number; new_users: number; active_users: number; jobs_count: number; files_processed: number; }
interface Summary { total_topup_thb: number; total_recognized_thb: number; total_new_users: number; total_jobs: number; total_files: number; }
interface Month { month: string; topup_thb: number; recognized_thb: number; deferred_revenue: number; new_users: number; active_users: number; jobs_count: number; avg_revenue_per_user: number; }
interface YTD { total_topup_thb: number; total_recognized_thb: number; total_deferred: number; tax_base_estimate: number; }

export default function FinancePage() {
  const [days, setDays] = useState<Day[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [months, setMonths] = useState<Month[]>([]);
  const [ytd, setYtd] = useState<YTD | null>(null);
  const [loading, setLoading] = useState(true);
  const [dateFrom, setDateFrom] = useState(() => { const d = new Date(); d.setDate(d.getDate() - 30); return d.toISOString().slice(0, 10); });
  const [dateTo, setDateTo] = useState(() => new Date().toISOString().slice(0, 10));

  const load = async () => {
    setLoading(true);
    try {
      const [daily, monthly] = await Promise.all([
        getFinanceDaily(dateFrom, dateTo) as Promise<{ days: Day[]; summary: Summary }>,
        getFinanceMonthly(new Date().getFullYear()) as Promise<{ months: Month[]; ytd: YTD }>,
      ]);
      setDays(daily.days); setSummary(daily.summary);
      setMonths(monthly.months); setYtd(monthly.ytd);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [dateFrom, dateTo]);

  const doExport = async () => {
    try {
      const blob = await exportFinance(dateFrom, dateTo, "xlsx");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = `bigeye_finance_${dateFrom}_${dateTo}.xlsx`; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { console.error(e); alert("Export failed"); }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-bold text-txt-primary">การเงิน</h1>
        <div className="flex items-center gap-2">
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="px-2 py-1.5 bg-bg-input border border-bdr rounded-input text-xs text-txt-primary" />
          <span className="text-txt-muted text-xs">ถึง</span>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="px-2 py-1.5 bg-bg-input border border-bdr rounded-input text-xs text-txt-primary" />
          <button onClick={doExport} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-accent-green/10 text-accent-green border border-accent-green/20 rounded-btn hover:bg-accent-green/20">
            <Download size={14} /> Export Excel
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard icon={Wallet} label="รายรับ (เติมเงิน)" value={formatCurrency(summary.total_topup_thb)} color="bg-accent-green" />
          <MetricCard icon={TrendingUp} label="รายได้รับรู้" value={formatCurrency(summary.total_recognized_thb)} color="bg-accent-orange" />
          <MetricCard icon={Clock} label="รายรับรอรับรู้" value={formatCurrency(summary.total_topup_thb - summary.total_recognized_thb)} color="bg-accent-yellow" />
          <MetricCard icon={Calculator} label="ฐานภาษีโดยประมาณ" value={formatCurrency(summary.total_recognized_thb)} color="bg-accent-purple" />
        </div>
      )}

      {/* Revenue Chart */}
      {days.length > 0 && (
        <div className="bg-bg-surface border border-bdr rounded-card p-5">
          <h3 className="text-sm font-medium text-txt-secondary mb-4">รายรับ vs รายได้รับรู้</h3>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={days}>
              <defs>
                <linearGradient id="fGreen" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#059669" stopOpacity={0.3} /><stop offset="95%" stopColor="#059669" stopOpacity={0} /></linearGradient>
                <linearGradient id="fOrange" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#ea580c" stopOpacity={0.3} /><stop offset="95%" stopColor="#ea580c" stopOpacity={0} /></linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1c2541" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#4f5d80" }} tickFormatter={(v: string) => v.slice(5)} />
              <YAxis tick={{ fontSize: 10, fill: "#4f5d80" }} />
              <Tooltip contentStyle={{ background: "#0c1021", border: "1px solid #1c2541", borderRadius: 8, fontSize: 12 }} />
              <Area type="monotone" dataKey="topup_thb" name="รายรับเติมเงิน (บาท)" stroke="#059669" fill="url(#fGreen)" strokeWidth={2} />
              <Area type="monotone" dataKey="recognized_thb" name="รายได้รับรู้ (บาท)" stroke="#ea580c" fill="url(#fOrange)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Daily Table */}
      <div className="bg-bg-surface border border-bdr rounded-card overflow-x-auto">
        <div className="px-5 py-3 border-b border-bdr"><h3 className="text-sm font-medium text-txt-secondary">รายวัน</h3></div>
        <table className="w-full text-xs">
          <thead><tr className="border-b border-bdr text-txt-muted">
            <th className="text-left px-4 py-2.5 font-medium">วันที่</th>
            <th className="text-right px-4 py-2.5 font-medium">รายรับ</th>
            <th className="text-right px-4 py-2.5 font-medium">เติม</th>
            <th className="text-right px-4 py-2.5 font-medium">รายได้รับรู้</th>
            <th className="text-right px-4 py-2.5 font-medium">เครดิตใช้</th>
            <th className="text-right px-4 py-2.5 font-medium">งาน</th>
            <th className="text-right px-4 py-2.5 font-medium">ไฟล์</th>
            <th className="text-right px-4 py-2.5 font-medium">ผู้ใช้ใหม่</th>
          </tr></thead>
          <tbody>
            {days.map((d) => (
              <tr key={d.date} className="border-b border-bdr/30 hover:bg-bg-hover">
                <td className="px-4 py-2 text-txt-secondary">{d.date}</td>
                <td className="px-4 py-2 text-right text-accent-green">{formatCurrency(d.topup_thb)}</td>
                <td className="px-4 py-2 text-right text-txt-muted">{d.topup_count}</td>
                <td className="px-4 py-2 text-right text-accent-orange">{formatCurrency(d.recognized_thb)}</td>
                <td className="px-4 py-2 text-right text-txt-muted">{formatNumber(d.recognized_credits)}</td>
                <td className="px-4 py-2 text-right text-txt-muted">{d.jobs_count}</td>
                <td className="px-4 py-2 text-right text-txt-muted">{d.files_processed}</td>
                <td className="px-4 py-2 text-right text-accent-purple">{d.new_users}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Monthly Table */}
      <div className="bg-bg-surface border border-bdr rounded-card overflow-x-auto">
        <div className="px-5 py-3 border-b border-bdr"><h3 className="text-sm font-medium text-txt-secondary">รายเดือน ({new Date().getFullYear()})</h3></div>
        <table className="w-full text-xs">
          <thead><tr className="border-b border-bdr text-txt-muted">
            <th className="text-left px-4 py-2.5 font-medium">เดือน</th>
            <th className="text-right px-4 py-2.5 font-medium">รายรับ</th>
            <th className="text-right px-4 py-2.5 font-medium">รายได้รับรู้</th>
            <th className="text-right px-4 py-2.5 font-medium">ส่วนต่าง</th>
            <th className="text-right px-4 py-2.5 font-medium">งาน</th>
            <th className="text-right px-4 py-2.5 font-medium">ผู้ใช้ใหม่</th>
            <th className="text-right px-4 py-2.5 font-medium">รายได้/ผู้ใช้</th>
          </tr></thead>
          <tbody>
            {months.map((m) => (
              <tr key={m.month} className="border-b border-bdr/30 hover:bg-bg-hover">
                <td className="px-4 py-2 text-txt-secondary">{m.month}</td>
                <td className="px-4 py-2 text-right text-accent-green">{formatCurrency(m.topup_thb)}</td>
                <td className="px-4 py-2 text-right text-accent-orange">{formatCurrency(m.recognized_thb)}</td>
                <td className="px-4 py-2 text-right text-accent-yellow">{formatCurrency(m.deferred_revenue)}</td>
                <td className="px-4 py-2 text-right text-txt-muted">{m.jobs_count}</td>
                <td className="px-4 py-2 text-right text-accent-purple">{m.new_users}</td>
                <td className="px-4 py-2 text-right text-txt-muted">{formatCurrency(m.avg_revenue_per_user)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {ytd && (
          <div className="px-5 py-3 border-t border-bdr flex flex-wrap gap-6 text-xs">
            <div><span className="text-txt-muted">รวมรายรับ YTD:</span> <span className="text-accent-green font-medium">{formatCurrency(ytd.total_topup_thb)}</span></div>
            <div><span className="text-txt-muted">รวมรายได้รับรู้:</span> <span className="text-accent-orange font-medium">{formatCurrency(ytd.total_recognized_thb)}</span></div>
            <div><span className="text-txt-muted">ส่วนต่าง:</span> <span className="text-accent-yellow font-medium">{formatCurrency(ytd.total_deferred)}</span></div>
            <div><span className="text-txt-muted">ฐานภาษี:</span> <span className="text-accent-purple font-medium">{formatCurrency(ytd.tax_base_estimate)}</span></div>
          </div>
        )}
      </div>
    </div>
  );
}
