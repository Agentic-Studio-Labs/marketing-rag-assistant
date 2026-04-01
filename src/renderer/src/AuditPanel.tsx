import { useCallback, useEffect, useState, type ReactElement } from "react";

interface AuditEvent {
  id: number;
  event_type: string;
  detail: string | null;
  created_at: string;
}

interface AuditData {
  events: AuditEvent[];
  total: number;
}

interface Props {
  sidecarBase: string;
}

const EVENT_STYLES: Record<string, { label: string; color: string }> = {
  query: { label: "Query", color: "bg-blue-900/50 text-blue-300" },
  upload: { label: "Upload", color: "bg-emerald-900/50 text-emerald-300" },
  reindex: { label: "Reindex", color: "bg-violet-900/50 text-violet-300" },
  key_change: { label: "Key Change", color: "bg-amber-900/50 text-amber-300" },
  error: { label: "Error", color: "bg-red-900/50 text-red-300" },
  system: { label: "System", color: "bg-zinc-700/50 text-zinc-300" },
};

function EventBadge({ type }: { type: string }): ReactElement {
  const style = EVENT_STYLES[type] ?? {
    label: type,
    color: "bg-zinc-800 text-zinc-400",
  };
  return (
    <span
      className={`inline-block rounded-md px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${style.color}`}
    >
      {style.label}
    </span>
  );
}

function parseDetail(detail: string | null): Record<string, unknown> | null {
  if (!detail) return null;
  try {
    return JSON.parse(detail) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function DetailDisplay({
  detail,
}: {
  detail: string | null;
}): ReactElement | null {
  if (!detail) return null;
  const parsed = parseDetail(detail);
  if (!parsed) return <span className="text-zinc-500">{detail}</span>;

  return (
    <span className="text-zinc-500">
      {Object.entries(parsed).map(([key, val], idx) => (
        <span key={key}>
          {idx > 0 ? " · " : ""}
          <span className="text-zinc-400">{key}:</span>{" "}
          {typeof val === "object" ? JSON.stringify(val) : String(val)}
        </span>
      ))}
    </span>
  );
}

const PAGE_SIZE = 50;

export function AuditPanel({ sidecarBase }: Props): ReactElement {
  const [data, setData] = useState<AuditData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);

  const fetchAudit = useCallback(
    async (p: number) => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          `${sidecarBase}/api/audit?limit=${PAGE_SIZE}&offset=${p * PAGE_SIZE}`,
        );
        if (!res.ok) throw new Error(await res.text());
        setData((await res.json()) as AuditData);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load audit log");
      } finally {
        setLoading(false);
      }
    },
    [sidecarBase],
  );

  useEffect(() => {
    void fetchAudit(page);
  }, [fetchAudit, page]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-baseline gap-3">
          <h2 className="text-sm font-semibold text-zinc-200">Audit Log</h2>
          {data ? (
            <span className="text-xs text-zinc-500">
              {data.total} event{data.total !== 1 ? "s" : ""}
            </span>
          ) : null}
        </div>
        <button
          type="button"
          onClick={() => void fetchAudit(page)}
          disabled={loading}
          className="rounded-lg px-3 py-1.5 text-xs text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-200 disabled:opacity-40"
        >
          Refresh
        </button>
      </div>

      {error ? (
        <div className="rounded-lg border border-amber-900/60 bg-amber-950/40 px-4 py-3 text-sm text-amber-100">
          {error}
        </div>
      ) : null}

      {loading && !data ? (
        <div className="flex flex-1 items-center justify-center text-sm text-zinc-500">
          Loading…
        </div>
      ) : data && data.events.length === 0 ? (
        <div className="flex flex-1 items-center justify-center text-sm text-zinc-500">
          No events recorded yet.
        </div>
      ) : data ? (
        <>
          <div className="flex flex-col gap-1">
            {data.events.map((evt) => (
              <div
                key={evt.id}
                className="flex items-start gap-3 rounded-lg border border-zinc-800/50 bg-zinc-900/40 px-4 py-2.5 text-xs"
              >
                <span className="w-32 shrink-0 text-zinc-600">
                  {new Date(evt.created_at + "Z").toLocaleString(undefined, {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </span>
                <span className="w-20 shrink-0">
                  <EventBadge type={evt.event_type} />
                </span>
                <span className="min-w-0 flex-1 truncate">
                  <DetailDisplay detail={evt.detail} />
                </span>
              </div>
            ))}
          </div>

          {totalPages > 1 ? (
            <div className="flex items-center justify-center gap-2 pt-2">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="rounded-lg px-3 py-1.5 text-xs text-zinc-400 hover:bg-zinc-800 disabled:opacity-30"
              >
                Previous
              </button>
              <span className="text-xs text-zinc-500">
                Page {page + 1} of {totalPages}
              </span>
              <button
                type="button"
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="rounded-lg px-3 py-1.5 text-xs text-zinc-400 hover:bg-zinc-800 disabled:opacity-30"
              >
                Next
              </button>
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
