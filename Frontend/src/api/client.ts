const API_BASE = import.meta.env.VITE_API_URL;
const BASE = `${API_BASE}/dashboard`;
async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  
  const headers = new Headers(opts?.headers);

  // only set content-type when sending JSON body
  const method = (opts?.method ?? "GET").toUpperCase();
  if (["POST", "PUT", "PATCH"].includes(method)) {
    headers.set("Content-Type", "application/json");
  } else {
    headers.delete("Content-Type");
  }

  // ngrok free-tier browser warning bypass
  headers.set("ngrok-skip-browser-warning", "true");

  const res = await fetch(`${BASE}${path}`, {
    ...opts,
    headers,
    credentials: "include",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  // Repos
  listRepos: () => request<import('../types').Repo[]>('/repos/list'),

  addRepo: (url: string, branch = 'main') =>
    request<import('../types').Repo>('/repos/add', {
      method: 'POST',
      body: JSON.stringify({ url, default_branch: branch }),
    }),

  deleteRepo: (id: number) =>
    request<void>(`/repos/delete/${id}`, { method: 'DELETE' }),

  syncRepo: (id: number) =>
    request<import('../types').SyncStatus>(`/repos/sync/${id}`, { method: 'POST' }),

  // Runs
  listRuns: (repoId: number, limit = 20, branch?: string, status?: string) => {
    if (repoId == null) throw new Error("repoId required");
    const params = new URLSearchParams({ limit: String(limit) });
    if (branch) params.set('branch', branch);
    if (status) params.set('status', status);
    return request<import('../types').PipelineRun[]>(`/repos/${repoId}/runs?${params}`);
  },

  getLatestRun: (repoId: number) => {
    if (repoId == null) throw new Error("repoId required");

    return request<import('../types').PipelineRunDetail>(`/repos/${repoId}/runs/latest`);
  },

  getRun: (repoId: number, runId: number) => {
    if (repoId == null) throw new Error("repoId required");
    if (runId == null) throw new Error("runId required");

    return request<import('../types').PipelineRunDetail>(
      `/repos/${repoId}/runs/${runId}`
    );
  },

  // Jobs & Tests
  getRunJobs: (repoId: number, runId: number) => {
    if (repoId == null) throw new Error("repoId required");
    if (runId == null) throw new Error("runId required");

    return request<import('../types').JobTiming[]>(`/repos/${repoId}/runs/${runId}/jobs`);
  },

  getRunTests: (repoId: number, runId: number) => {
    if (repoId == null) throw new Error("repoId required");
    if (runId == null) throw new Error("runId required");

    return request<import('../types').TestRun[]>(`/repos/${repoId}/runs/${runId}/tests`);
  },

  getTestHistory: (repoId: number, testName: string, limit = 20) => {
    if (repoId == null) throw new Error("repoId required");
    if (!testName) throw new Error("testName required");

    return request<import('../types').TestHistoryPoint[]>(
      `/repos/${repoId}/tests/${encodeURIComponent(testName)}/history?limit=${limit}`
    );
  },

  // Insights & Trends
  getInsights: (repoId: number, runId?: number) => {
    if (repoId == null) throw new Error("repoId required");
    return request<import('../types').Insight[]>(
      `/repos/${repoId}/insights${runId ? `?run_id=${runId}` : ''}`
    );
  },


  getTrends: (repoId: number, limit = 20) =>{
    if (repoId == null) throw new Error("repoId required");
  
    return request<import('../types').TrendPoint[]>(`/repos/${repoId}/trends?limit=${limit}`);
  },
};
