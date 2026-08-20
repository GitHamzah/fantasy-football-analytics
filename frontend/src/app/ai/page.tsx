"use client";

import { ChevronDown, Loader2, Send } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { askAI } from "@/lib/api";

type Msg = {
  role: "user" | "assistant";
  content: string;
  dataContext?: string;
  failed?: boolean;
};

const QUICK_PROMPTS = [
  "Best waiver pickups",
  "Draft strategy PPR",
  "Top 5 RBs 2026",
  "Best DST stream",
];

export default function AiPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState<Record<number, boolean>>({});
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  async function send(question: string) {
    const q = question.trim();
    if (!q || busy) return;

    setInput("");
    setMessages((m) => [...m, { role: "user", content: q }]);
    setBusy(true);

    try {
      const res = await askAI(q);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: res.answer,
          dataContext: res.data_context,
        },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content:
            e instanceof Error
              ? `Could not get an answer: ${e.message}`
              : "Could not get an answer.",
          failed: true,
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col">
      <h1 className="text-2xl font-bold tracking-tight">AI Analyst</h1>
      <p className="mt-1 text-sm text-muted">
        Ask anything. The backend pulls real numbers from the warehouse before
        answering, so responses cite actual data.
      </p>

      <div className="mt-5 flex flex-wrap gap-2">
        {QUICK_PROMPTS.map((p) => (
          <button
            key={p}
            onClick={() => send(p)}
            disabled={busy}
            className="rounded-md border border-border bg-surface px-3 py-1.5 text-xs text-muted transition-colors hover:border-accent hover:text-text disabled:opacity-50"
          >
            {p}
          </button>
        ))}
      </div>

      <div className="mt-6 space-y-4">
        {messages.length === 0 && !busy && (
          <div className="rounded-lg border border-border bg-surface px-4 py-10 text-center text-sm text-muted">
            No messages yet. Try a prompt above, or ask your own question.
          </div>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            className={
              "flex " + (m.role === "user" ? "justify-end" : "justify-start")
            }
          >
            <div
              className={
                "max-w-[85%] rounded-lg px-4 py-3 text-sm leading-relaxed " +
                (m.role === "user"
                  ? "bg-accent text-white"
                  : m.failed
                    ? "border border-grade-bad/40 bg-surface text-grade-bad"
                    : "border border-border bg-surface text-text")
              }
            >
              <div className="whitespace-pre-wrap">{m.content}</div>

              {m.dataContext && (
                <div className="mt-3 border-t border-border pt-2">
                  <button
                    onClick={() => setOpen((o) => ({ ...o, [i]: !o[i] }))}
                    className="flex items-center gap-1 text-[11px] uppercase tracking-wider text-faint hover:text-muted"
                  >
                    <ChevronDown
                      size={12}
                      className={
                        "transition-transform " + (open[i] ? "rotate-180" : "")
                      }
                    />
                    Data used
                  </button>
                  {open[i] && (
                    <pre className="mt-2 max-h-64 overflow-auto rounded bg-bg p-2 text-[11px] leading-snug text-muted">
                      {m.dataContext}
                    </pre>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {busy && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 rounded-lg border border-border bg-surface px-4 py-3 text-sm text-muted">
              <Loader2 size={14} className="animate-spin" />
              Pulling data and thinking…
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="sticky bottom-4 mt-6 flex items-center gap-2 rounded-lg border border-border bg-surface p-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about players, matchups, draft strategy…"
          disabled={busy}
          className="flex-1 bg-transparent px-2 py-1.5 text-sm text-text outline-none placeholder:text-faint disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="flex items-center gap-1.5 rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white transition-opacity disabled:opacity-40"
        >
          <Send size={14} />
          Send
        </button>
      </form>

      {messages.length > 0 && (
        <button
          onClick={() => setMessages([])}
          className="mt-3 self-start text-xs text-faint hover:text-muted"
        >
          Clear conversation
        </button>
      )}
    </div>
  );
}
