import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from "@tanstack/react-table";
import { api } from "../api/client";
import type { ContentItem, JobDetail } from "../api/types";

const columnHelper = createColumnHelper<ContentItem>();

const columns = [
  columnHelper.accessor("title", {
    header: "Title",
    cell: (info) => (
      <span className="font-medium line-clamp-1">{info.getValue()}</span>
    ),
  }),
  columnHelper.accessor("content_type", {
    header: "Type",
    cell: (info) => (
      <span className="text-xs px-2 py-0.5 rounded-full bg-muted">
        {info.getValue()}
      </span>
    ),
  }),
  columnHelper.accessor("persona", { header: "Persona" }),
  columnHelper.accessor("funnel_stage", { header: "Funnel Stage" }),
  columnHelper.accessor("performance_score", {
    header: "Score",
    cell: (info) => `${info.getValue() ?? 0}%`,
  }),
  columnHelper.accessor("created_at", {
    header: "Date",
    cell: (info) => {
      const val = info.getValue();
      return val
        ? new Date(val).toLocaleString(undefined, {
            dateStyle: "short",
            timeStyle: "short",
          })
        : "";
    },
  }),
];

export default function Library() {
  const [data, setData] = useState<ContentItem[]>([]);
  const [total, setTotal] = useState(0);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);
  const [uploadOpen, setUploadOpen] = useState(false);
  const navigate = useNavigate();

  const refresh = useCallback(() => setRefreshTick((t) => t + 1), []);

  useEffect(() => {
    const params: Record<string, string | number> = { limit: 50 };
    if (filters.content_type) params.content_type = filters.content_type;
    if (filters.persona) params.persona = filters.persona;
    if (globalFilter) params.search = globalFilter;
    api.listContent(params).then((r) => {
      setData(r.items);
      setTotal(r.total);
    });
  }, [filters, globalFilter, refreshTick]);

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  const selectedItem = useMemo(
    () => data.find((d) => d.id === selectedId),
    [data, selectedId],
  );

  return (
    <div className="flex h-full flex-col gap-5">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Library</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {total} {total === 1 ? "item" : "items"} · drop files anywhere or
            click Upload to add more
          </p>
        </div>
        <button
          type="button"
          onClick={() => setUploadOpen((v) => !v)}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          {uploadOpen ? "Close" : "Upload content"}
        </button>
      </header>

      {uploadOpen && (
        <UploadPanel
          onIngested={refresh}
          onClose={() => setUploadOpen(false)}
        />
      )}

      <div className="flex flex-wrap gap-2">
        <input
          type="text"
          placeholder="Search library..."
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
          className="rounded-md border border-border bg-background px-3 py-1.5 text-sm flex-1 min-w-[200px] focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
        <FilterSelect
          label="Type"
          value={filters.content_type || ""}
          options={[
            "blog",
            "case_study",
            "email",
            "social_post",
            "landing_page",
            "whitepaper",
          ]}
          onChange={(v) => setFilters((f) => ({ ...f, content_type: v }))}
        />
        <FilterSelect
          label="Persona"
          value={filters.persona || ""}
          options={["cto", "cfo", "developer", "marketing_leader", "engineer"]}
          onChange={(v) => setFilters((f) => ({ ...f, persona: v }))}
        />
      </div>

      <DropZone onIngested={refresh} className="flex flex-1 gap-4 min-h-0">
        <div className="flex-1 flex flex-col min-w-0">
          <div className="border border-border rounded-lg overflow-auto flex-1">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 sticky top-0">
                {table.getHeaderGroups().map((hg) => (
                  <tr key={hg.id}>
                    {hg.headers.map((h) => (
                      <th
                        key={h.id}
                        onClick={h.column.getToggleSortingHandler()}
                        className="text-left px-3 py-2 font-medium text-muted-foreground cursor-pointer select-none"
                      >
                        {flexRender(h.column.columnDef.header, h.getContext())}
                        {{ asc: " ^", desc: " v" }[
                          h.column.getIsSorted() as string
                        ] ?? ""}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.map((row) => (
                  <tr
                    key={row.id}
                    onClick={() => setSelectedId(row.original.id)}
                    onDoubleClick={() =>
                      navigate(`/content/${row.original.id}`)
                    }
                    className={`border-t border-border cursor-pointer hover:bg-accent/50 ${selectedId === row.original.id ? "bg-accent" : ""}`}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-3 py-2">
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext(),
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {data.length === 0 && (
              <EmptyState onUpload={() => setUploadOpen(true)} />
            )}
          </div>
        </div>
        {selectedItem && (
          <div className="w-80 border border-border rounded-lg p-4 overflow-auto flex-shrink-0">
            <h3 className="font-semibold mb-2">{selectedItem.title}</h3>
            <div className="flex gap-1 mb-3 flex-wrap">
              <Tag>{selectedItem.content_type}</Tag>
              <Tag>{selectedItem.persona}</Tag>
              <Tag>{selectedItem.funnel_stage}</Tag>
            </div>
            <p className="text-sm text-muted-foreground mb-4 line-clamp-6">
              {selectedItem.summary}
            </p>
            <button
              onClick={() => navigate(`/content/${selectedItem.id}`)}
              className="w-full rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90"
            >
              Open
            </button>
          </div>
        )}
      </DropZone>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-md border border-border bg-background px-2 py-1.5 text-sm"
    >
      <option value="">All {label}s</option>
      {options.map((o) => (
        <option key={o} value={o}>
          {o.replace("_", " ")}
        </option>
      ))}
    </select>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
      {children}
    </span>
  );
}

function EmptyState({ onUpload }: { onUpload: () => void }) {
  return (
    <div className="text-center py-16 px-6">
      <p className="text-base font-medium">Your library is empty</p>
      <p className="text-sm text-muted-foreground mt-2 mb-4 max-w-md mx-auto">
        Drop files anywhere on this page or click below to add markdown, text,
        PDF, or DOCX. Once ingested they appear here.
      </p>
      <button
        type="button"
        onClick={onUpload}
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
      >
        Upload your first document
      </button>
    </div>
  );
}

function UploadPanel({
  onIngested,
  onClose,
}: {
  onIngested: () => void;
  onClose: () => void;
}) {
  const [files, setFiles] = useState<File[]>([]);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!job || job.status === "succeeded" || job.status === "failed") return;
    const interval = window.setInterval(async () => {
      try {
        const next = await api.getJob(job.id);
        setJob(next);
        if (next.status === "succeeded") {
          const ingested =
            (next.result as { ingested?: number } | null)?.ingested ?? 0;
          setMessage(
            `Ingested ${ingested} file${ingested === 1 ? "" : "s"}. Library refreshed.`,
          );
          setUploading(false);
          onIngested();
        } else if (next.status === "failed") {
          setError(next.error || "Ingest job failed");
          setUploading(false);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : String(err));
        setUploading(false);
      }
    }, 1500);
    return () => window.clearInterval(interval);
  }, [job, onIngested]);

  async function start() {
    if (files.length === 0) return;
    setUploading(true);
    setMessage("");
    setError("");
    try {
      const objectPaths: string[] = [];
      for (const file of files) {
        objectPaths.push(await api.uploadFile(file));
      }
      const next = await api.createIngestJob({
        object_paths: objectPaths,
        source_label: "library-upload",
      });
      setJob(next);
      if (next.status === "succeeded") {
        const ingested =
          (next.result as { ingested?: number } | null)?.ingested ?? 0;
        setMessage(
          `Ingested ${ingested} file${ingested === 1 ? "" : "s"}. Library refreshed.`,
        );
        setUploading(false);
        onIngested();
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
      setUploading(false);
    }
  }

  return (
    <section className="rounded-lg border border-border bg-muted/20 p-5 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold">Upload content</h2>
          <p className="text-xs text-muted-foreground mt-1">
            Markdown, text, PDF, or DOCX. Files upload to cloud storage and
            ingest in the background.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          Close
        </button>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".md,.markdown,.txt,.pdf,.docx"
          onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
          className="text-sm flex-1"
        />
        <button
          type="button"
          onClick={() => void start()}
          disabled={uploading || files.length === 0}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
        >
          {uploading ? "Uploading..." : `Upload ${files.length || ""}`.trim()}
        </button>
      </div>

      {files.length > 0 && (
        <ul className="text-xs text-muted-foreground space-y-1">
          {files.map((f) => (
            <li key={f.name}>· {f.name}</li>
          ))}
        </ul>
      )}

      {job && (
        <p className="text-xs">
          Job <span className="font-mono">{job.id.slice(0, 8)}</span> —{" "}
          <span className="font-medium">{job.status}</span>
        </p>
      )}
      {message && <p className="text-sm text-emerald-600">{message}</p>}
      {error && <p className="text-sm text-red-500">{error}</p>}
    </section>
  );
}

function DropZone({
  onIngested,
  children,
  className,
}: {
  onIngested: () => void;
  children: React.ReactNode;
  className?: string;
}) {
  const [active, setActive] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function onDragOver(e: React.DragEvent) {
    e.preventDefault();
    setActive(true);
  }
  function onDragLeave(e: React.DragEvent) {
    if (e.currentTarget === e.target) setActive(false);
  }
  async function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setActive(false);
    const files = Array.from(e.dataTransfer.files).filter((f) =>
      /\.(md|markdown|txt|pdf|docx)$/i.test(f.name),
    );
    if (files.length === 0) return;
    setBusy(true);
    setError("");
    try {
      const objectPaths: string[] = [];
      for (const f of files) objectPaths.push(await api.uploadFile(f));
      const job = await api.createIngestJob({
        object_paths: objectPaths,
        source_label: "library-drop",
      });
      // poll a few times
      let current = job;
      const start = Date.now();
      while (
        current.status !== "succeeded" &&
        current.status !== "failed" &&
        Date.now() - start < 30_000
      ) {
        await new Promise((r) => setTimeout(r, 1500));
        current = await api.getJob(current.id);
      }
      onIngested();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      className={`relative ${className ?? ""}`}
    >
      {children}
      {(active || busy) && (
        <div className="absolute inset-0 z-10 flex items-center justify-center rounded-lg border-2 border-dashed border-primary/60 bg-background/80 pointer-events-none">
          <p className="text-sm font-medium">
            {busy ? "Uploading…" : "Drop to upload"}
          </p>
        </div>
      )}
      {error && (
        <p className="absolute bottom-2 left-2 text-xs text-red-500">{error}</p>
      )}
    </div>
  );
}
