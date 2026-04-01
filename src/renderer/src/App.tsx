import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactElement,
} from "react";
import Markdown from "react-markdown";
import { ApiKeyDialog } from "./ApiKeyDialog";
import { AuditPanel } from "./AuditPanel";
import { LibraryPanel } from "./LibraryPanel";
import { resolveSidecarBase } from "./lib/sidecar-url";

type Source = {
  chunk_id: number;
  title: string | null;
  score: number;
  excerpt: string;
};

type Usage = {
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
};

type QueryResponse = {
  answer: string;
  sources: Source[];
  usage: Usage | null;
};

declare global {
  interface Window {
    appInfo?: { sidecarOrigin: string };
    electronAPI?: {
      getApiKey: () => Promise<{
        isSet: boolean;
        encryptionAvailable: boolean;
      }>;
      setApiKey: (key: string) => Promise<{ ok: boolean }>;
      clearApiKey: () => Promise<{ ok: boolean }>;
    };
  }
}

type Tab = "chat" | "library" | "audit";

const EXAMPLE_QUESTIONS = [
  "What makes a good case study?",
  "How should I approach SEO content strategy?",
  "What's heading-aware chunking and why does it matter?",
  "How do I personalize email nurture sequences?",
];

export function App(): ReactElement {
  const [tab, setTab] = useState<Tab>("chat");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<
    {
      role: "user" | "assistant";
      text: string;
      sources?: Source[];
      usage?: Usage | null;
    }[]
  >([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const [keyDialogOpen, setKeyDialogOpen] = useState(false);
  const [keyIsSet, setKeyIsSet] = useState(false);
  const [encryptionAvailable, setEncryptionAvailable] = useState(true);

  const base = useMemo(
    () =>
      resolveSidecarBase(
        import.meta.env.VITE_SIDECAR_URL,
        window.appInfo?.sidecarOrigin,
      ),
    [],
  );

  const refreshKeyStatus = useCallback(async () => {
    if (!window.electronAPI) return;
    try {
      const result = await window.electronAPI.getApiKey();
      setKeyIsSet(result.isSet);
      setEncryptionAvailable(result.encryptionAvailable);
    } catch {
      /* preload not available */
    }
  }, []);

  useEffect(() => {
    void refreshKeyStatus();
  }, [refreshKeyStatus]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const send = useCallback(
    async (override?: string) => {
      const q = (override ?? input).trim();
      if (!q || loading) return;
      if (!override) setInput("");
      setError(null);
      setMessages((m) => [...m, { role: "user", text: q }]);
      setLoading(true);
      try {
        const res = await fetch(`${base}/api/query`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: q }),
        });
        if (!res.ok) {
          const t = await res.text();
          throw new Error(t || res.statusText);
        }
        const data = (await res.json()) as QueryResponse;
        setMessages((m) => [
          ...m,
          {
            role: "assistant",
            text: data.answer,
            sources: data.sources,
            usage: data.usage,
          },
        ]);
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Request failed";
        setError(msg);
        setMessages((m) => [
          ...m,
          { role: "assistant", text: `Error: ${msg}` },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [base, input, loading],
  );

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b border-zinc-800 bg-zinc-900/80 px-6 py-3 backdrop-blur">
        <div className="flex items-center gap-6">
          <h1 className="text-base font-semibold tracking-tight text-zinc-50">
            Marketing RAG Assistant
          </h1>
          <nav className="flex gap-1">
            {(["chat", "library", "audit"] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTab(t)}
                className={`rounded-lg px-3 py-1.5 text-sm capitalize transition ${
                  tab === t
                    ? "bg-zinc-800 font-medium text-zinc-100"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                {t}
              </button>
            ))}
          </nav>
        </div>
        <button
          type="button"
          onClick={() => setKeyDialogOpen(true)}
          className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-200"
          aria-label="API key settings"
        >
          <span
            className={`h-2 w-2 rounded-full ${keyIsSet ? "bg-emerald-500" : "bg-zinc-600"}`}
          />
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-4 w-4"
          >
            <path
              fillRule="evenodd"
              d="M8 7a5 5 0 1 1 3.61 4.804l-1.903 1.903A1 1 0 0 1 9 14H8v1a1 1 0 0 1-1 1H6v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1v-2a1 1 0 0 1 .293-.707L8.196 8.39A5.002 5.002 0 0 1 8 7Zm5-3a.75.75 0 0 0 0 1.5A1.5 1.5 0 0 1 14.5 7 .75.75 0 0 0 16 7a3 3 0 0 0-3-3Z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      </header>

      {tab === "chat" ? (
        <main className="flex min-h-0 flex-1 flex-col gap-4 p-6">
          {error ? (
            <div className="flex items-center justify-between rounded-lg border border-amber-900/60 bg-amber-950/40 px-4 py-3 text-sm text-amber-100">
              <span>{error}</span>
              <button
                type="button"
                onClick={() => setError(null)}
                className="ml-3 text-amber-400 hover:text-amber-200"
                aria-label="Dismiss error"
              >
                &times;
              </button>
            </div>
          ) : null}

          <div
            ref={scrollRef}
            className="flex flex-1 flex-col gap-3 overflow-y-auto rounded-xl border border-zinc-800 bg-zinc-900/50 p-4"
          >
            {messages.length === 0 ? (
              <div className="flex flex-1 flex-col items-center justify-center gap-5 py-8">
                <p className="text-sm text-zinc-500">
                  Ask about your content library. Try one of these:
                </p>
                <div className="flex flex-wrap justify-center gap-2">
                  {EXAMPLE_QUESTIONS.map((q) => (
                    <button
                      key={q}
                      type="button"
                      onClick={() => void send(q)}
                      className="rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-2 text-xs text-zinc-300 transition hover:border-emerald-700/50 hover:text-emerald-300"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
            {messages.map((msg, i) => (
              <div
                key={`${i}-${msg.role}`}
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "ml-auto bg-emerald-900/40 text-emerald-50 ring-1 ring-emerald-800/50"
                    : "bg-zinc-800/80 text-zinc-100"
                }`}
              >
                {msg.role === "assistant" ? (
                  <div className="prose-invert prose-sm prose prose-zinc max-w-none prose-headings:mt-3 prose-headings:mb-1 prose-headings:text-zinc-200 prose-p:my-1.5 prose-ul:my-1.5 prose-ol:my-1.5 prose-li:my-0.5 prose-strong:text-zinc-200">
                    <Markdown>{msg.text}</Markdown>
                  </div>
                ) : (
                  <div className="whitespace-pre-wrap">{msg.text}</div>
                )}
                {msg.sources && msg.sources.length > 0 ? (
                  <details className="mt-3 border-t border-zinc-700/50 pt-2">
                    <summary className="cursor-pointer select-none text-xs text-zinc-500 hover:text-zinc-300">
                      {msg.sources.length} source
                      {msg.sources.length !== 1 ? "s" : ""} retrieved
                    </summary>
                    <ul className="mt-2 space-y-2 text-xs text-zinc-400">
                      {msg.sources.map((s) => (
                        <li key={s.chunk_id}>
                          <span className="font-medium text-zinc-300">
                            {s.title ?? `Chunk #${s.chunk_id}`}
                          </span>
                          <span className="text-zinc-500">
                            {" "}
                            · score {s.score.toFixed(3)}
                          </span>
                          <p className="mt-1 line-clamp-3 text-zinc-500">
                            {s.excerpt}
                          </p>
                        </li>
                      ))}
                    </ul>
                  </details>
                ) : null}
                {msg.usage && msg.usage.cost_usd > 0 ? (
                  <div className="mt-2 flex gap-3 text-[10px] text-zinc-600">
                    <span>{msg.usage.model}</span>
                    <span>
                      {msg.usage.input_tokens} in / {msg.usage.output_tokens}{" "}
                      out
                    </span>
                    <span>
                      $
                      {msg.usage.cost_usd < 0.01
                        ? msg.usage.cost_usd.toFixed(4)
                        : msg.usage.cost_usd.toFixed(2)}
                    </span>
                  </div>
                ) : null}
              </div>
            ))}
            {loading ? (
              <div className="flex max-w-[85%] items-center gap-1.5 rounded-2xl bg-zinc-800/80 px-4 py-3">
                <span className="h-2 w-2 animate-bounce rounded-full bg-zinc-500 [animation-delay:0ms]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-zinc-500 [animation-delay:150ms]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-zinc-500 [animation-delay:300ms]" />
              </div>
            ) : null}
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && void send()}
              placeholder="Ask a question…"
              className="flex-1 rounded-xl border border-zinc-700 bg-zinc-900 px-4 py-3 text-sm text-zinc-100 outline-none ring-emerald-700/0 transition focus:border-emerald-700/50 focus:ring-2 focus:ring-emerald-700/30"
              disabled={loading}
              aria-label="Question"
            />
            <button
              type="button"
              onClick={() => void send()}
              disabled={loading || !input.trim()}
              className="rounded-xl bg-emerald-700 px-5 py-3 text-sm font-medium text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Send
            </button>
          </div>
        </main>
      ) : tab === "library" ? (
        <LibraryPanel sidecarBase={base} />
      ) : (
        <AuditPanel sidecarBase={base} />
      )}

      {keyDialogOpen ? (
        <ApiKeyDialog
          isKeySet={keyIsSet}
          encryptionAvailable={encryptionAvailable}
          onClose={() => setKeyDialogOpen(false)}
          onSaved={() => {
            void refreshKeyStatus();
            setKeyDialogOpen(false);
          }}
        />
      ) : null}
    </div>
  );
}
