"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { createRun, listAgents, listRuns } from "../lib/api";

export default function Home() {
  const [agents, setAgents] = useState<any[]>([]);
  const [runs, setRuns] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      setAgents(await listAgents());
      setRuns(await listRuns());
      setError(null);
    } catch (e: any) {
      setError(e.message);
    }
  }

  useEffect(() => {
    refresh();
    // The seeded runs finish in the background, so poll to see them land.
    const timer = setInterval(refresh, 2000);
    return () => clearInterval(timer);
  }, []);

  return (
    <main>
      <h1>Agent Studio</h1>
      <p>Workspace: acme (the demo client acts as the acme creator).</p>
      {error && <p style={{ color: "crimson" }}>Error: {error}</p>}

      <h2>Agents</h2>
      <ul>
        {agents.map((a) => (
          <li key={a.id}>
            {a.name}{" "}
            <button
              onClick={async () => {
                try {
                  await createRun(a.id);
                } catch (e: any) {
                  setError(e.message);
                }
                refresh();
              }}
            >
              Start a run
            </button>
          </li>
        ))}
      </ul>

      <h2>Runs</h2>
      <ul>
        {runs.map((r) => (
          <li key={r.id}>
            <Link href={`/runs/${r.id}`}>Run {r.id}</Link> &mdash; {r.status}
          </li>
        ))}
      </ul>
    </main>
  );
}
