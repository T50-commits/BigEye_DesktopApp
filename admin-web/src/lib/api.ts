import { API_URL } from "./constants";

let _token: string | null = null;

export function setToken(token: string | null) {
  _token = token;
}

export function getToken(): string | null {
  return _token;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (_token) {
    headers["Authorization"] = `Bearer ${_token}`;
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401 || res.status === 403) {
    // Token expired or not admin
    if (path !== "/auth/login") {
      setToken(null);
      window.location.href = "/login";
    }
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || body.message || `Error ${res.status}`);
  }

  // Handle blob responses (Excel export)
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("spreadsheet") || ct.includes("octet-stream") || ct.includes("pdf")) {
    return res.blob() as unknown as T;
  }

  return res.json();
}

// ── Auth ──
export async function login(email: string, password: string) {
  return request<{ token: string; user_id: string }>("/admin/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

// ── Dashboard ──
export async function getDashboardStats() {
  return request<Record<string, unknown>>("/admin/dashboard/stats");
}

export async function getDashboardCharts(days = 30) {
  return request<Record<string, unknown>>(`/admin/dashboard/charts?days=${days}`);
}

// ── Users ──
export async function getUsers(search = "", page = 1, limit = 50) {
  const params = new URLSearchParams({ search, page: String(page), limit: String(limit) });
  return request<Record<string, unknown>>(`/admin/users?${params}`);
}

export async function getUser(uid: string) {
  return request<Record<string, unknown>>(`/admin/users/${uid}`);
}

export async function getUserTransactions(uid: string, limit = 50) {
  return request<Record<string, unknown>>(`/admin/users/${uid}/transactions?limit=${limit}`);
}

export async function getUserJobs(uid: string, limit = 50) {
  return request<Record<string, unknown>>(`/admin/users/${uid}/jobs?limit=${limit}`);
}

export async function adjustCredits(uid: string, amount: number, reason: string) {
  return request<Record<string, unknown>>(`/admin/users/${uid}/adjust-credits`, {
    method: "POST",
    body: JSON.stringify({ amount, reason }),
  });
}

export async function suspendUser(uid: string) {
  return request<Record<string, unknown>>(`/admin/users/${uid}/suspend`, { method: "POST" });
}

export async function unsuspendUser(uid: string) {
  return request<Record<string, unknown>>(`/admin/users/${uid}/unsuspend`, { method: "POST" });
}

export async function resetHardware(uid: string) {
  return request<Record<string, unknown>>(`/admin/users/${uid}/reset-hardware`, { method: "POST" });
}

export async function resetPassword(uid: string, newPassword: string, resetHw = false) {
  return request<Record<string, unknown>>(`/admin/users/${uid}/reset-password`, {
    method: "POST",
    body: JSON.stringify({ new_password: newPassword, reset_hardware: resetHw }),
  });
}

// ── Slips ──
export async function getSlips(status = "", page = 1, limit = 50) {
  const params = new URLSearchParams({ status, page: String(page), limit: String(limit) });
  return request<Record<string, unknown>>(`/admin/slips?${params}`);
}

export async function getSlip(id: string) {
  return request<Record<string, unknown>>(`/admin/slips/${id}`);
}

export async function approveSlip(id: string, creditAmount: number) {
  return request<Record<string, unknown>>(`/admin/slips/${id}/approve`, {
    method: "POST",
    body: JSON.stringify({ credit_amount: creditAmount }),
  });
}

export async function rejectSlip(id: string, reason: string) {
  return request<Record<string, unknown>>(`/admin/slips/${id}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

// ── Jobs ──
export async function getJobs(status = "", page = 1, limit = 50) {
  const params = new URLSearchParams({ status, page: String(page), limit: String(limit) });
  return request<Record<string, unknown>>(`/admin/jobs?${params}`);
}

export async function getJob(id: string) {
  return request<Record<string, unknown>>(`/admin/jobs/${id}`);
}

export async function forceRefundJob(id: string) {
  return request<Record<string, unknown>>(`/admin/jobs/${id}/force-refund`, { method: "POST" });
}

export async function cleanupJobs() {
  return request<Record<string, unknown>>("/admin/cleanup-jobs", { method: "POST" });
}

// ── Finance ──
export async function getFinanceDaily(from: string, to: string) {
  const params = new URLSearchParams({ from, to });
  return request<Record<string, unknown>>(`/admin/finance/daily?${params}`);
}

export async function getFinanceMonthly(year: number) {
  return request<Record<string, unknown>>(`/admin/finance/monthly?year=${year}`);
}

export async function exportFinance(from: string, to: string, format = "xlsx") {
  const params = new URLSearchParams({ from, to, format });
  return request<Blob>(`/admin/finance/export?${params}`);
}

// ── Config ──
export async function getConfig() {
  return request<Record<string, unknown>>("/admin/config");
}

export async function updateConfig(section: string, data: Record<string, unknown>) {
  return request<Record<string, unknown>>(`/admin/config/${section}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function updatePrompt(key: string, content: string) {
  return request<Record<string, unknown>>(`/admin/config/prompts/${key}`, {
    method: "PUT",
    body: JSON.stringify({ content }),
  });
}

// ── Dictionary ──
export async function getDictionary() {
  return request<{ words: string[] }>("/admin/config/dictionary");
}

export async function updateDictionary(words: string[]) {
  return request<{ message: string }>("/admin/config/dictionary", {
    method: "PUT",
    body: JSON.stringify({ words }),
  });
}

// ── Audit Logs ──
export async function getAuditLogs(severity = "", days = 7, search = "", page = 1, limit = 100) {
  const params = new URLSearchParams({
    severity, days: String(days), search, page: String(page), limit: String(limit),
  });
  return request<Record<string, unknown>>(`/admin/audit-logs?${params}`);
}

// ── Promotions (existing endpoints) ──
export async function getPromos(status = "") {
  const params = status ? `?status=${status}` : "";
  return request<Record<string, unknown>>(`/admin/promo/list${params}`);
}

export async function getPromo(id: string) {
  return request<Record<string, unknown>>(`/admin/promo/${id}`);
}

export async function createPromo(data: Record<string, unknown>) {
  return request<Record<string, unknown>>("/admin/promo/create", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updatePromo(id: string, data: Record<string, unknown>) {
  return request<Record<string, unknown>>(`/admin/promo/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function promoAction(id: string, action: string) {
  return request<Record<string, unknown>>(`/admin/promo/${id}/${action}`, { method: "POST" });
}

export async function getPromoStats(id: string) {
  return request<Record<string, unknown>>(`/admin/promo/${id}/stats`);
}
