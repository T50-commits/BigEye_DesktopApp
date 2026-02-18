"use client";

import { useEffect, useState } from "react";
import { getDashboardStats, getDashboardCharts } from "@/lib/api";
import { formatNumber, formatCurrency } from "@/lib/utils";
import MetricCard from "@/components/shared/MetricCard";
import LoadingSpinner from "@/components/shared/LoadingSpinner";
import {
  Users, UserPlus, Wallet, TrendingUp,
  Briefcase, AlertTriangle, CheckCircle,
  Receipt, Clock, RefreshCw,
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";

interface Stats {
  active_users: number;
  new_users_today: number;
  topup_thb_today: number;
  recognized_thb_today: number;
  exchange_rate: number;
  jobs_today: number;
  errors_today: number;
  success_rate: number;
  pending_slips: number;
  stuck_jobs: number;
}

interface ChartData {
  revenue: { date: string; topup_thb: number; recognized_thb: number }[];
  users: { date: string; new_users: number; active_users: number }[];
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [charts, setCharts] = useState<ChartData | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [s, c] = await Promise.all([
        getDashboardStats(),
        getDashboardCharts(30),
      ]);
      setStats(s as unknown as Stats);
      setCharts(c as unknown as ChartData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading || !stats) return <LoadingSpinner />;

  const now = new Date().toLocaleString("th-TH", {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-txt-primary">แดชบอร์ด</h1>
          <p className="text-xs text-txt-muted mt-0.5">{now}</p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-txt-secondary bg-bg-surface border border-bdr rounded-btn hover:bg-bg-hover transition-colors"
        >
          <RefreshCw size={14} />
          รีเฟรช
        </button>
      </div>

      {/* Metric Cards — Row 1 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard icon={Users} label="ผู้ใช้งาน" value={formatNumber(stats.active_users)} color="bg-accent-blue" />
        <MetricCard icon={UserPlus} label="สมัครใหม่วันนี้" value={formatNumber(stats.new_users_today)} color="bg-accent-purple" />
        <MetricCard icon={Wallet} label="รายรับเติมเงิน" value={formatCurrency(stats.topup_thb_today)} color="bg-accent-green" />
        <MetricCard icon={TrendingUp} label="รายได้รับรู้" value={formatCurrency(stats.recognized_thb_today)} color="bg-accent-orange" />
      </div>

      {/* Metric Cards — Row 2 (Jobs) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard icon={Briefcase} label="งานวันนี้" value={formatNumber(stats.jobs_today)} color="bg-accent-yellow" />
        <MetricCard icon={AlertTriangle} label="ไฟล์ผิดพลาด" value={formatNumber(stats.errors_today)} color="bg-accent-red" />
        <MetricCard
          icon={CheckCircle}
          label="อัตราสำเร็จ"
          value={`${stats.success_rate}%`}
          color={stats.success_rate >= 90 ? "bg-accent-green" : stats.success_rate >= 70 ? "bg-accent-yellow" : "bg-accent-red"}
        />
      </div>

      {/* Alert Cards */}
      {(stats.pending_slips > 0 || stats.stuck_jobs > 0) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {stats.pending_slips > 0 && (
            <a href="/slips" className="flex items-center gap-3 p-4 bg-accent-orange/5 border border-accent-orange/20 rounded-card hover:bg-accent-orange/10 transition-colors">
              <Receipt size={20} className="text-accent-orange" />
              <div>
                <div className="text-sm font-medium text-accent-orange">สลิปรอตรวจ {stats.pending_slips} รายการ</div>
                <div className="text-xs text-txt-muted">คลิกเพื่อตรวจสอบ</div>
              </div>
            </a>
          )}
          {stats.stuck_jobs > 0 && (
            <a href="/jobs" className="flex items-center gap-3 p-4 bg-accent-red/5 border border-accent-red/20 rounded-card hover:bg-accent-red/10 transition-colors">
              <Clock size={20} className="text-accent-red" />
              <div>
                <div className="text-sm font-medium text-accent-red">งานค้าง {stats.stuck_jobs} รายการ</div>
                <div className="text-xs text-txt-muted">คลิกเพื่อตรวจสอบ</div>
              </div>
            </a>
          )}
        </div>
      )}

      {/* Charts */}
      {charts && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Revenue Chart */}
          <div className="bg-bg-surface border border-bdr rounded-card p-5">
            <h3 className="text-sm font-medium text-txt-secondary mb-4">รายได้ 30 วัน</h3>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={charts.revenue}>
                <defs>
                  <linearGradient id="gGreen" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#059669" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#059669" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gOrange" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ea580c" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#ea580c" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1c2541" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#4f5d80" }} tickFormatter={(v: string) => v.slice(5)} />
                <YAxis tick={{ fontSize: 10, fill: "#4f5d80" }} />
                <Tooltip
                  contentStyle={{ background: "#0c1021", border: "1px solid #1c2541", borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: "#8b9cc7" }}
                />
                <Area type="monotone" dataKey="topup_thb" name="รายรับเติมเงิน" stroke="#059669" fill="url(#gGreen)" strokeWidth={2} />
                <Area type="monotone" dataKey="recognized_thb" name="รายได้รับรู้" stroke="#ea580c" fill="url(#gOrange)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* User Growth Chart */}
          <div className="bg-bg-surface border border-bdr rounded-card p-5">
            <h3 className="text-sm font-medium text-txt-secondary mb-4">ผู้ใช้ใหม่ 30 วัน</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={charts.users}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1c2541" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#4f5d80" }} tickFormatter={(v: string) => v.slice(5)} />
                <YAxis tick={{ fontSize: 10, fill: "#4f5d80" }} />
                <Tooltip
                  contentStyle={{ background: "#0c1021", border: "1px solid #1c2541", borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: "#8b9cc7" }}
                />
                <Bar dataKey="new_users" name="ผู้ใช้ใหม่" fill="#a78bfa" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
