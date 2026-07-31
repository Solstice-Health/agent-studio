"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { getRun, runGate } from "../../../lib/api";
import { useRunStream } from "../../../lib/useSSE";
import Transcript from "./Transcript";

export default function RunPage() {
  const params = useParams();
  const id = Number(params.id);

  const events = useRunStream(id);
  const [run, setRun] = useState<any>(null);
  const [gate, setGate] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const data = await getRun(id);
        if (alive) {
          setRun(data);
          setError(null);
        }
      } catch (e: any) {
        if (alive) setError(e.message);
      }
    };
    tick();
    const timer = setInterval(tick, 1000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [id]);

  // A failed run records why in the transcript. Without pulling it out, the page reads
  // "failed" with no reason anywhere in the UI.
  const failures = events.filter((e) => e.kind === "error");

  return (
    <main>
      <h1>Run {id}</h1>
      <p>Status: {run?.status ?? "..."}</p>
      {error && <p style={{ color: "crimson" }}>Error: {error}</p>}

      {failures.length > 0 && (
        <section>
          <h2>Why it failed</h2>
          {failures.map((e, i) => (
            <pre key={i} style={{ color: "crimson" }}>
              {e.payload?.content ?? JSON.stringify(e.payload)}
            </pre>
          ))}
        </section>
      )}

      <h2>Transcript (live)</h2>
      <Transcript steps={events} />

      <h2>Draft</h2>
      {run?.draft?.sections?.length ? (
        run.draft.sections.map((s: any, i: number) => (
          <div key={i}>
            <h3>{s.title}</h3>
            <p>{s.body}</p>
            <small>cites: {(s.cited_source_ids ?? []).join(", ") || "nothing"}</small>
          </div>
        ))
      ) : (
        <p>(no draft yet)</p>
      )}

      <h2>Gate</h2>
      <button
        onClick={async () => {
          try {
            setGate(await runGate(id));
            setError(null);
          } catch (e: any) {
            setGate(null);
            setError(e.message);
          }
        }}
      >
        Run gate
      </button>
      {gate && (
        <div>
          <p>
            <strong>{gate.gate_status}</strong>
          </p>
          <table>
            <tbody>
              {gate.checks.map((c: any) => (
                <tr key={c.key}>
                  <td>{c.key}</td>
                  <td>{c.status}</td>
                  <td>{c.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
