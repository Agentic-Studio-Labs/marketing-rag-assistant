import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type DragEvent,
  type ReactElement,
} from "react";

interface ChunkInfo {
  id: number;
  section_title: string | null;
  content_type: string | null;
  persona: string | null;
  funnel_stage: string | null;
  body_len: number;
}

interface DocInfo {
  source_path: string;
  chunk_count: number;
  total_chars: number;
  chunks: ChunkInfo[];
}

interface CorpusData {
  total_documents: number;
  total_chunks: number;
  documents: DocInfo[];
}

interface Props {
  sidecarBase: string;
}

function Badge({
  children,
  color,
}: {
  children: React.ReactNode;
  color?: string;
}): ReactElement {
  const bg = color ?? "bg-zinc-800";
  return (
    <span
      className={`rounded-md ${bg} px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-zinc-300`}
    >
      {children}
    </span>
  );
}

function StatCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}): ReactElement {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 px-4 py-3">
      <div className="text-xl font-semibold text-zinc-100">{value}</div>
      <div className="mt-0.5 text-xs text-zinc-500">{label}</div>
    </div>
  );
}

function TagCloud({
  label,
  counts,
}: {
  label: string;
  counts: Record<string, number>;
}): ReactElement {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) return <></>;
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 px-4 py-3">
      <div className="mb-2 text-xs font-medium text-zinc-500">{label}</div>
      <div className="flex flex-wrap gap-1.5">
        {entries.map(([tag, count]) => (
          <span
            key={tag}
            className="rounded-md bg-zinc-800 px-2 py-0.5 text-xs text-zinc-300"
          >
            {tag} <span className="text-zinc-500">{count}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

const ACCEPT = ".md,.pdf";

export function LibraryPanel({ sidecarBase }: Props): ReactElement {
  const [data, setData] = useState<CorpusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [reindexing, setReindexing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [previewChunkId, setPreviewChunkId] = useState<number | null>(null);
  const [previewBody, setPreviewBody] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchCorpus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${sidecarBase}/api/corpus`);
      if (!res.ok) throw new Error(await res.text());
      setData((await res.json()) as CorpusData);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load corpus");
    } finally {
      setLoading(false);
    }
  }, [sidecarBase]);

  useEffect(() => {
    void fetchCorpus();
  }, [fetchCorpus]);

  const handleReindex = useCallback(async () => {
    setReindexing(true);
    try {
      const res = await fetch(`${sidecarBase}/api/reindex`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      await fetchCorpus();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reindex failed");
    } finally {
      setReindexing(false);
    }
  }, [sidecarBase, fetchCorpus]);

  const uploadFiles = useCallback(
    async (files: FileList | File[]) => {
      setUploading(true);
      setError(null);
      try {
        for (const file of Array.from(files)) {
          const form = new FormData();
          form.append("file", file);
          const res = await fetch(`${sidecarBase}/api/upload`, {
            method: "POST",
            body: form,
          });
          if (!res.ok) {
            const t = await res.text();
            throw new Error(`${file.name}: ${t}`);
          }
        }
        await fetchCorpus();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [sidecarBase, fetchCorpus],
  );

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length > 0) {
        void uploadFiles(e.dataTransfer.files);
      }
    },
    [uploadFiles],
  );

  const fetchChunkBody = useCallback(
    async (chunkId: number) => {
      if (previewChunkId === chunkId) {
        setPreviewChunkId(null);
        setPreviewBody(null);
        return;
      }
      setPreviewChunkId(chunkId);
      setPreviewBody(null);
      setPreviewLoading(true);
      try {
        const res = await fetch(`${sidecarBase}/api/chunks/${chunkId}`);
        if (!res.ok) throw new Error("Failed to load chunk");
        const json = (await res.json()) as { body: string };
        setPreviewBody(json.body);
      } catch {
        setPreviewBody("(failed to load)");
      } finally {
        setPreviewLoading(false);
      }
    },
    [sidecarBase, previewChunkId],
  );

  const toggle = useCallback((path: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
    setPreviewChunkId(null);
    setPreviewBody(null);
  }, []);

  // Stats aggregation
  const stats = (() => {
    if (!data) return null;
    const byType: Record<string, number> = {};
    const byFunnel: Record<string, number> = {};
    const byPersona: Record<string, number> = {};
    let totalChars = 0;
    for (const doc of data.documents) {
      totalChars += doc.total_chars;
      for (const c of doc.chunks) {
        if (c.content_type)
          byType[c.content_type] = (byType[c.content_type] || 0) + 1;
        if (c.funnel_stage)
          byFunnel[c.funnel_stage] = (byFunnel[c.funnel_stage] || 0) + 1;
        if (c.persona) byPersona[c.persona] = (byPersona[c.persona] || 0) + 1;
      }
    }
    return { byType, byFunnel, byPersona, totalChars };
  })();

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center text-sm text-zinc-500">
        Loading corpus…
      </div>
    );
  }

  return (
    <div
      className={`flex flex-1 flex-col gap-5 overflow-y-auto p-6 ${dragOver ? "ring-2 ring-inset ring-emerald-600/50" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      {error ? (
        <div className="flex items-center justify-between rounded-lg border border-amber-900/60 bg-amber-950/40 px-4 py-3 text-sm text-amber-100">
          <span>{error}</span>
          <button
            type="button"
            onClick={() => setError(null)}
            className="ml-3 text-amber-400 hover:text-amber-200"
          >
            &times;
          </button>
        </div>
      ) : null}

      {/* Stats bar */}
      {data && data.total_chunks > 0 && stats ? (
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-3 gap-3">
            <StatCard label="Documents" value={data.total_documents} />
            <StatCard label="Chunks" value={data.total_chunks} />
            <StatCard
              label="Total characters"
              value={`${(stats.totalChars / 1000).toFixed(1)}k`}
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <TagCloud label="Content type" counts={stats.byType} />
            <TagCloud label="Funnel stage" counts={stats.byFunnel} />
            <TagCloud label="Persona" counts={stats.byPersona} />
          </div>
        </div>
      ) : null}

      {/* Upload + actions bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPT}
            multiple
            className="hidden"
            onChange={(e) => {
              if (e.target.files && e.target.files.length > 0) {
                void uploadFiles(e.target.files);
              }
              e.target.value = "";
            }}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="flex items-center gap-2 rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-600 disabled:opacity-40"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-4 w-4"
            >
              <path d="M9.25 13.25a.75.75 0 0 0 1.5 0V4.636l2.955 3.129a.75.75 0 0 0 1.09-1.03l-4.25-4.5a.75.75 0 0 0-1.09 0l-4.25 4.5a.75.75 0 1 0 1.09 1.03L9.25 4.636v8.614Z" />
              <path d="M3.5 12.75a.75.75 0 0 0-1.5 0v2.5A2.75 2.75 0 0 0 4.75 18h10.5A2.75 2.75 0 0 0 18 15.25v-2.5a.75.75 0 0 0-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5Z" />
            </svg>
            {uploading ? "Uploading…" : "Upload"}
          </button>
          <span className="text-xs text-zinc-500">
            or drag and drop .md / .pdf files
          </span>
        </div>
        <button
          type="button"
          onClick={() => void handleReindex()}
          disabled={reindexing}
          className="rounded-lg px-3 py-1.5 text-xs text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-200 disabled:opacity-40"
        >
          {reindexing ? "Reindexing…" : "Reindex all"}
        </button>
      </div>

      {/* Document list */}
      {!data || data.total_chunks === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-zinc-800 py-16 text-sm text-zinc-500">
          <p>No documents indexed yet.</p>
          <p>Upload files or click Reindex to scan the corpus directory.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {data.documents.map((doc) => {
            const isExpanded = expanded.has(doc.source_path);
            const name = doc.source_path.split("/").pop() ?? doc.source_path;
            const ext = name.endsWith(".pdf") ? "PDF" : "MD";

            return (
              <div
                key={doc.source_path}
                className="rounded-xl border border-zinc-800 bg-zinc-900/50"
              >
                <button
                  type="button"
                  onClick={() => toggle(doc.source_path)}
                  className="flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-zinc-800/50"
                >
                  <span className="shrink-0 rounded bg-zinc-800 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-zinc-400">
                    {ext}
                  </span>
                  <span className="flex-1 truncate text-sm font-medium text-zinc-200">
                    {name}
                  </span>
                  <span className="text-xs text-zinc-500">
                    {doc.chunk_count} chunk{doc.chunk_count !== 1 ? "s" : ""} ·{" "}
                    {(doc.total_chars / 1000).toFixed(1)}k chars
                  </span>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className={`h-4 w-4 text-zinc-500 transition ${isExpanded ? "rotate-180" : ""}`}
                  >
                    <path
                      fillRule="evenodd"
                      d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>

                {isExpanded ? (
                  <div className="border-t border-zinc-800">
                    {doc.chunks.map((chunk) => (
                      <div
                        key={chunk.id}
                        className="border-b border-zinc-800/40 last:border-b-0"
                      >
                        <button
                          type="button"
                          onClick={() => void fetchChunkBody(chunk.id)}
                          className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-xs transition hover:bg-zinc-800/30"
                        >
                          <span className="w-8 shrink-0 text-zinc-600">
                            #{chunk.id}
                          </span>
                          <span className="flex-1 truncate text-zinc-300">
                            {chunk.section_title ?? "—"}
                          </span>
                          <div className="flex gap-1.5">
                            {chunk.content_type ? (
                              <Badge>{chunk.content_type}</Badge>
                            ) : null}
                            {chunk.persona ? (
                              <Badge color="bg-zinc-700">{chunk.persona}</Badge>
                            ) : null}
                            {chunk.funnel_stage ? (
                              <Badge color="bg-zinc-700/60">
                                {chunk.funnel_stage}
                              </Badge>
                            ) : null}
                          </div>
                          <span className="w-14 text-right text-zinc-600">
                            {chunk.body_len} ch
                          </span>
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            viewBox="0 0 16 16"
                            fill="currentColor"
                            className={`h-3 w-3 text-zinc-600 transition ${previewChunkId === chunk.id ? "rotate-180" : ""}`}
                          >
                            <path
                              fillRule="evenodd"
                              d="M4.22 6.22a.75.75 0 0 1 1.06 0L8 8.94l2.72-2.72a.75.75 0 1 1 1.06 1.06l-3.25 3.25a.75.75 0 0 1-1.06 0L4.22 7.28a.75.75 0 0 1 0-1.06Z"
                              clipRule="evenodd"
                            />
                          </svg>
                        </button>
                        {previewChunkId === chunk.id ? (
                          <div className="border-t border-zinc-800/30 bg-zinc-950/50 px-4 py-3">
                            {previewLoading ? (
                              <p className="text-xs text-zinc-500">Loading…</p>
                            ) : (
                              <pre className="max-h-60 overflow-auto whitespace-pre-wrap text-xs leading-relaxed text-zinc-400">
                                {previewBody}
                              </pre>
                            )}
                          </div>
                        ) : null}
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      )}

      {/* Drag overlay hint */}
      {dragOver ? (
        <div className="pointer-events-none fixed inset-0 z-40 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="rounded-2xl border-2 border-dashed border-emerald-500/60 bg-zinc-900/90 px-12 py-8 text-center">
            <p className="text-lg font-medium text-emerald-300">
              Drop files to upload
            </p>
            <p className="mt-1 text-sm text-zinc-400">.md and .pdf supported</p>
          </div>
        </div>
      ) : null}
    </div>
  );
}
