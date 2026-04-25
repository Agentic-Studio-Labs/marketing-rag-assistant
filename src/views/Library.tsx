import { useState, useEffect, useMemo } from "react";
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
import type { ContentItem } from "../api/types";

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
  const navigate = useNavigate();

  useEffect(() => {
    const params: Record<string, string | number> = { limit: 50 };
    if (filters.content_type) params.content_type = filters.content_type;
    if (filters.persona) params.persona = filters.persona;
    if (globalFilter) params.search = globalFilter;
    api.listContent(params).then((r) => {
      setData(r.items);
      setTotal(r.total);
    });
  }, [filters, globalFilter]);

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
    <div className="flex h-full gap-4">
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex gap-2 mb-4 flex-wrap">
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
            options={[
              "cto",
              "cfo",
              "developer",
              "marketing_leader",
              "engineer",
            ]}
            onChange={(v) => setFilters((f) => ({ ...f, persona: v }))}
          />
        </div>
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
                  onDoubleClick={() => navigate(`/content/${row.original.id}`)}
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
            <p className="text-center text-muted-foreground py-8 text-sm">
              No content found.
            </p>
          )}
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          {total} items total
        </p>
      </div>
      {selectedItem && (
        <div className="w-80 border border-border rounded-lg p-4 overflow-auto flex-shrink-0">
          <h3 className="font-semibold mb-2">{selectedItem.title}</h3>
          <div className="flex gap-1 mb-3 flex-wrap">
            <Tag>{selectedItem.content_type}</Tag>
            <Tag>{selectedItem.persona}</Tag>
            <Tag>{selectedItem.funnel_stage}</Tag>
          </div>
          <p className="text-sm text-muted-foreground mb-4">
            {selectedItem.summary}
          </p>
          <button
            onClick={() => navigate(`/content/${selectedItem.id}`)}
            className="w-full rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90"
          >
            View Details
          </button>
        </div>
      )}
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
