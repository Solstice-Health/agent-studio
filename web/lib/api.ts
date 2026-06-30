// Auth is a shim, so the demo client always acts as the acme creator.
const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const HEADERS = {
  "X-Workspace-Slug": "acme",
  "X-User-Email": "creator@acme.test",
  "Content-Type": "application/json",
};

export const streamUrl = (runId: number) => `${BASE}/runs/${runId}/stream`;

export async function listAgents() {
  const r = await fetch(`${BASE}/agents`, { headers: HEADERS });
  return r.json();
}

export async function listRuns() {
  const r = await fetch(`${BASE}/runs`, { headers: HEADERS });
  return r.json();
}

export async function createRun(agentId: number) {
  const r = await fetch(`${BASE}/runs`, {
    method: "POST",
    headers: HEADERS,
    body: JSON.stringify({ agent_id: agentId }),
  });
  return r.json();
}

export async function getRun(runId: number) {
  const r = await fetch(`${BASE}/runs/${runId}`, { headers: HEADERS });
  return r.json();
}

export async function runGate(runId: number) {
  const r = await fetch(`${BASE}/runs/${runId}/gate`, { method: "POST", headers: HEADERS });
  return r.json();
}
