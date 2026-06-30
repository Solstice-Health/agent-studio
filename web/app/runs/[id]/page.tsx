"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { getRun, runGate } from "../../../lib/api";
import { useRunStream } from "../../../lib/useSSE";

export default function RunPage() {
  const params = useParams();
  const id = Number(params.id);

  const events = useRunStream(id);
  const [run, setRun] = useState<any>(null);
  const [gate, setGate] = useState<any>(null);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      const data = await getRun(id);
      if (alive) setRun(data);
    };
    tick();
    const timer = setInterval(tick, 1000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [id]);

  return (
    <main>
      <h1>Run {id}</h1>
      <p>Status: {run?.status ?? "..."}</p>

      <h2>Transcript (live)</h2>
      <pre>
        {events.length
          ? events.map((e) => `${e.event} ${e.kind ?? ""} ${e.seq ?? e.status ?? ""}`).join("\n")
          : "(waiting for steps...)"}
      </pre>

      <h2>Draft</h2>
      {run?.draft?.sections?.length ? (
        run.draft.sections.map((s: any, i: number) => (
          <div key={i}>
            <h3>{s.title}</h3>
            <p>{s.body}</p>
          </div>
        ))
      ) : (
        <p>(no draft yet)</p>
      )}

      <h2>Gate</h2>
      <button onClick={async () => setGate(await runGate(id))}>Run gate</button>
      {gate && <pre>{JSON.stringify(gate, null, 2)}</pre>}
    </main>
  );
}
