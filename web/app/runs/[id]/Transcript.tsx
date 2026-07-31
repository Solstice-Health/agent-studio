"use client";

/**
 * Renders a run's transcript step by step.
 *
 * The transcript is the record of truth for a run, so this shows what the model actually
 * said, which tool it called with which arguments, and what came back — not just the step
 * kinds. Tool results are matched back to the call that produced them by tool_call_id, so
 * a result reads as "get_source" rather than as an anonymous blob of JSON.
 */

export type Step = {
  event?: string;
  seq?: number;
  kind?: string;
  status?: string;
  payload?: any;
};

const LABELS: Record<string, string> = {
  system: "System prompt",
  user: "Brief",
  assistant: "Model turn",
  tool: "Tool result",
  error: "Error",
};

function pretty(value: unknown): string {
  if (typeof value !== "string") return JSON.stringify(value, null, 2);
  try {
    return JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    return value; // not JSON after all; show it as sent
  }
}

function parsed(value: unknown): any {
  if (typeof value !== "string") return value;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

// Thinking blocks arrive with empty text unless the model is asked to summarize them, so
// only surface the ones that actually carry content.
function thinkingOf(payload: any): string[] {
  return (payload?.provider_content ?? [])
    .filter((b: any) => b?.type === "thinking" && b?.thinking?.trim())
    .map((b: any) => b.thinking as string);
}

export default function Transcript({ steps }: { steps: Step[] }) {
  // One EventSource can be opened twice under React strict mode, so key off seq rather
  // than trusting arrival order to be unique.
  const bySeq = new Map<number, Step>();
  for (const s of steps) {
    if (s.event === "step" && typeof s.seq === "number") bySeq.set(s.seq, s);
  }
  const ordered = [...bySeq.values()].sort((a, b) => (a.seq ?? 0) - (b.seq ?? 0));

  if (!ordered.length) return <p>(waiting for steps...)</p>;

  const toolNameById = new Map<string, string>();
  for (const s of ordered) {
    for (const call of s.payload?.tool_calls ?? []) {
      if (call?.id) toolNameById.set(call.id, call.name);
    }
  }

  const modelTurns = ordered.filter((s) => s.payload?.role === "assistant").length;
  const toolCalls = ordered.reduce(
    (n, s) => n + (s.payload?.tool_calls?.length ?? 0),
    0,
  );

  return (
    <div>
      <p className="muted">
        {ordered.length} steps &middot; {modelTurns} model turns &middot; {toolCalls} tool calls
      </p>

      {ordered.map((step) => {
        const payload = step.payload ?? {};
        const role: string = payload.role ?? (step.kind === "error" ? "error" : "assistant");
        const isError = role === "error";
        const calls = payload.tool_calls ?? [];
        const thinking = thinkingOf(payload);
        const toolName = payload.tool_call_id
          ? toolNameById.get(payload.tool_call_id)
          : undefined;
        const result = role === "tool" ? parsed(payload.content) : null;
        const failed = Boolean(result && typeof result === "object" && "error" in result);

        let label = LABELS[role] ?? step.kind ?? "step";
        if (role === "tool" && toolName) label = `Tool result · ${toolName}`;

        return (
          <section key={step.seq} className={`step${isError || failed ? " step-error" : ""}`}>
            <header className="step-head">
              <span className="seq">#{step.seq}</span>
              <strong>{label}</strong>
              {calls.length > 0 && (
                <span className="muted">
                  {" "}
                  &rarr; {calls.length} tool call{calls.length > 1 ? "s" : ""}
                </span>
              )}
              {failed && <span className="muted"> &rarr; errored</span>}
            </header>

            {thinking.map((t, i) => (
              <div key={i}>
                <div className="muted">thinking</div>
                <pre>{t}</pre>
              </div>
            ))}

            {role !== "tool" && payload.content ? <pre>{payload.content}</pre> : null}

            {calls.map((call: any) => (
              <div key={call.id}>
                <div className="muted">
                  calls <code>{call.name}</code>
                </div>
                <pre>{pretty(call.arguments ?? {})}</pre>
              </div>
            ))}

            {role === "tool" ? <pre>{pretty(payload.content)}</pre> : null}

            <details>
              <summary className="muted">raw</summary>
              <pre>{JSON.stringify(payload, null, 2)}</pre>
            </details>
          </section>
        );
      })}
    </div>
  );
}
