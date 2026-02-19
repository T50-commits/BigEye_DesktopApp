// ── Dashboard ──
export interface DashboardStats {
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

export interface ChartPoint {
  date: string;
  [key: string]: string | number;
}

export interface DashboardCharts {
  revenue: ChartPoint[];
  users: ChartPoint[];
}

// ── Users ──
export interface UserSummary {
  uid: string;
  email: string;
  full_name: string;
  credits: number;
  status: string;
  tier: string;
  last_login: string;
  created_at: string;
}

export interface UserDetail extends UserSummary {
  hardware_id: string;
  total_topup_baht: number;
  total_credits_used: number;
  app_version: string;
  os_type: string;
  last_active: string;
}

export interface Transaction {
  id: string;
  type: string;
  amount: number;
  balance_after: number;
  description: string;
  date: string;
}

export interface Job {
  id: string;
  job_token: string;
  user_id: string;
  mode: string;
  file_count: number;
  status: string;
  reserved_credits: number;
  actual_usage: number;
  refund_amount: number;
  success_count: number;
  failed_count: number;
  created_at: string;
  completed_at: string;
}

export interface JobDetail extends Job {
  keyword_style: string;
  model: string;
  photo_count: number;
  video_count: number;
  photo_rate: number;
  video_rate: number;
  version: string;
}

// ── Slips ──
export interface Slip {
  id: string;
  user_id: string;
  status: string;
  amount_detected: number | null;
  amount_credited: number | null;
  bank_ref: string;
  verification_method: string;
  reject_reason: string;
  created_at: string;
  verified_at: string;
}

export interface SlipDetail extends Slip {
  verification_result: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

// ── Finance ──
export interface FinanceDay {
  date: string;
  topup_thb: number;
  topup_count: number;
  recognized_thb: number;
  recognized_credits: number;
  new_users: number;
  active_users: number;
  jobs_count: number;
  files_processed: number;
}

export interface FinanceSummary {
  total_topup_thb: number;
  total_recognized_thb: number;
  total_new_users: number;
  total_jobs: number;
  total_files: number;
}

export interface FinanceMonth {
  month: string;
  topup_thb: number;
  recognized_thb: number;
  deferred_revenue: number;
  new_users: number;
  active_users: number;
  jobs_count: number;
  avg_revenue_per_user: number;
}

export interface FinanceYTD {
  total_topup_thb: number;
  total_recognized_thb: number;
  total_deferred: number;
  tax_base_estimate: number;
}

// ── Audit Logs ──
export interface AuditLog {
  id: string;
  event_type: string;
  user_id: string;
  severity: string;
  details: Record<string, unknown>;
  created_at: string;
}

// ── Paginated Response ──
export interface PaginatedResponse<T> {
  total: number;
  page: number;
  pages: number;
  [key: string]: T[] | number;
}
