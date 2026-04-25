import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { GeneratedItem } from "../api/types";

export default function Generated() {
  const [items, setItems] = useState<GeneratedItem[]>([]);
  const [total, setTotal] = useState(0);
  const [formatFilter, setFormatFilter] = useState("");
  const [toneFilter, setToneFilter] = useState("");
  const [selectedItem, setSelectedItem] = useState<GeneratedItem | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const params: Record<string, string | number> = { limit: 50 };
    if (formatFilter) params.format = formatFilter;
    if (toneFilter) params.tone = toneFilter;
    api.listGenerated(params).then((r) => {
      setItems(r.items);
      setTotal(r.total);
    });
  }, [formatFilter, toneFilter]);

  return (
    <div className="flex h-full gap-4">
      <div className="flex-1 flex flex-col min-w-0">
        <h1 className="text-2xl font-semibold mb-4">Generated Content</h1>
        <div className="flex gap-2 mb-4 flex-wrap">
          <select
            value={formatFilter}
            onChange={(e) => setFormatFilter(e.target.value)}
            className="rounded-md border border-border bg-background px-2 py-1.5 text-sm"
          >
            <option value="">All Formats</option>
            {["linkedin", "email", "twitter", "summary"].map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
          <select
            value={toneFilter}
            onChange={(e) => setToneFilter(e.target.value)}
            className="rounded-md border border-border bg-background px-2 py-1.5 text-sm"
          >
            <option value="">All Tones</option>
            {["professional", "casual", "technical", "friendly"].map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
        <div className="border border-border rounded-lg overflow-auto flex-1">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 sticky top-0">
              <tr>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground">
                  Source
                </th>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground">
                  Format
                </th>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground">
                  Tone
                </th>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground">
                  Quality
                </th>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground">
                  Date
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.id}
                  onClick={() => setSelectedItem(item)}
                  className={`border-t border-border cursor-pointer hover:bg-accent/50 ${selectedItem?.id === item.id ? "bg-accent" : ""}`}
                >
                  <td className="px-3 py-2 font-medium">{item.source_title}</td>
                  <td className="px-3 py-2">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-muted">
                      {item.format}
                    </span>
                  </td>
                  <td className="px-3 py-2">{item.tone}</td>
                  <td className="px-3 py-2">
                    {item.quality_score != null
                      ? `${Math.round(item.quality_score * 100)}%`
                      : "-"}
                  </td>
                  <td className="px-3 py-2 text-muted-foreground whitespace-nowrap">
                    {new Date(item.created_at).toLocaleString(undefined, {
                      dateStyle: "short",
                      timeStyle: "short",
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {items.length === 0 && (
            <p className="text-center text-muted-foreground py-8 text-sm">
              No generated content yet. Repurpose content from the Library.
            </p>
          )}
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          {total} items total
        </p>
      </div>
      {selectedItem && (
        <div className="w-96 border border-border rounded-lg p-4 overflow-auto flex-shrink-0">
          <div className="flex justify-between items-start mb-3">
            <div>
              <p className="text-xs text-muted-foreground">Source</p>
              <button
                onClick={() =>
                  navigate(`/content/${selectedItem.source_content_id}`)
                }
                className="text-sm font-medium text-primary hover:underline"
              >
                {selectedItem.source_title}
              </button>
            </div>
            <div className="flex gap-1">
              <span className="text-xs px-2 py-0.5 rounded-full bg-muted">
                {selectedItem.format}
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-muted">
                {selectedItem.tone}
              </span>
            </div>
          </div>
          <pre className="whitespace-pre-wrap text-sm font-sans leading-relaxed">
            {selectedItem.body}
          </pre>
        </div>
      )}
    </div>
  );
}
