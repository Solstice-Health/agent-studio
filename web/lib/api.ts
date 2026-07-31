// Auth is a shim, so the demo client always acts as the acme creator.
const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const HEADERS = {
  "X-Workspace-Slug": "acme",
  "X-User-Email": "creator@acme.test",
  "Content-Type": "application/json",
};

export const streamUrl = (runId: number) => `${BASE}/runs/${runId}/stream`;

// Surfaces the api's `detail` rather than letting a non-2xx body flow on as if it were
// the expected shape and fail somewhere further from the cause.
async function request(path: string, init: RequestInit = {}) {
  const r = await fetch(`${BASE}${path}`, { headers: HEADERS, ...init });
  const body = await r.json().catch(() => null);
  if (!r.ok) {
    throw new Error(body?.detail ?? `${init.method ?? "GET"} ${path} failed (${r.status})`);
  }
  return body;
}

export const listAgents = () => request("/agents");
export const listRuns = () => request("/runs");
export const getRun = (runId: number) => request(`/runs/${runId}`);

export const createRun = (agentId: number) =>
  request("/runs", { method: "POST", body: JSON.stringify({ agent_id: agentId }) });

export const runGate = (runId: number) => request(`/runs/${runId}/gate`, { method: "POST" });
