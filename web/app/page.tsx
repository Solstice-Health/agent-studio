"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { createRun, listAgents, listRuns } from "../lib/api";

export default function Home() {
  const [agents, setAgents] = useState<any[]>([]);
  const [runs, setRuns] = useState<any[]>([]);

  async function refresh() {
    setAgents(await listAgents());
    setRuns(await listRuns());
  }

  useEffect(() => {
    refresh();
  }, []);

  return (
    <main>
      <h1>Agent Studio</h1>
      <p>Workspace: acme (the demo client acts as the acme creator).</p>

      <h2>Agents</h2>
      <ul>
        {agents.map((a) => (
          <li key={a.id}>
            {a.name}{" "}
            <button
              onClick={async () => {
                await createRun(a.id);
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
