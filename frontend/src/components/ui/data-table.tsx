"use client";

import { useState, useMemo, ReactNode } from "react";
import { Card, CardContent } from "./card";
import { ChevronDown, ChevronUp, ChevronsUpDown } from "lucide-react";

export interface Column<T> {
  key: string;
  label: string;
  sortable?: boolean;
  align?: "left" | "right" | "center";
  render?: (row: T) => ReactNode;
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  expandable?: (row: T) => ReactNode;
  defaultSortKey?: string;
  defaultSortDir?: "asc" | "desc";
  pageSize?: number;
}

export default function DataTable<T extends Record<string, unknown>>({
  data,
  columns,
  expandable,
  defaultSortKey,
  defaultSortDir = "desc",
  pageSize = 50,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(defaultSortKey ?? null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">(defaultSortDir);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [page, setPage] = useState(0);

  const sorted = useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const av = a[sortKey] as number | string | null;
      const bv = b[sortKey] as number | string | null;
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === "number" && typeof bv === "number") {
        return sortDir === "asc" ? av - bv : bv - av;
      }
      return sortDir === "asc"
        ? String(av).localeCompare(String(bv))
        : String(bv).localeCompare(String(av));
    });
  }, [data, sortKey, sortDir]);

  const totalPages = Math.ceil(sorted.length / pageSize);
  const paged = sorted.slice(page * pageSize, (page + 1) * pageSize);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  return (
    <Card>
      <CardContent className="pt-4">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                {expandable && <th className="w-8 pb-2" />}
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className={`pb-2 font-medium ${col.align === "right" ? "text-right" : col.align === "center" ? "text-center" : "text-left"} ${col.sortable ? "cursor-pointer select-none hover:text-foreground" : ""}`}
                    onClick={() => col.sortable && handleSort(col.key)}
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.label}
                      {col.sortable && (
                        sortKey === col.key ? (
                          sortDir === "asc" ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
                        ) : (
                          <ChevronsUpDown className="h-3 w-3 opacity-30" />
                        )
                      )}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paged.map((row, i) => {
                const globalIdx = page * pageSize + i;
                const isExpanded = expandedRow === globalIdx;
                return (
                  <tbody key={globalIdx}>
                    <tr
                      className={`border-b hover:bg-muted/50 ${expandable ? "cursor-pointer" : ""}`}
                      onClick={() => expandable && setExpandedRow(isExpanded ? null : globalIdx)}
                    >
                      {expandable && (
                        <td className="py-2 w-8">
                          <ChevronDown className={`h-4 w-4 transition-transform ${isExpanded ? "rotate-180" : ""}`} />
                        </td>
                      )}
                      {columns.map((col) => (
                        <td
                          key={col.key}
                          className={`py-2 ${col.align === "right" ? "text-right" : col.align === "center" ? "text-center" : ""}`}
                        >
                          {col.render ? col.render(row) : String(row[col.key] ?? "N/A")}
                        </td>
                      ))}
                    </tr>
                    {isExpanded && expandable && (
                      <tr className="border-b bg-muted/30">
                        <td colSpan={columns.length + 1} className="p-4">
                          {expandable(row)}
                        </td>
                      </tr>
                    )}
                  </tbody>
                );
              })}
              {paged.length === 0 && (
                <tr>
                  <td colSpan={columns.length + (expandable ? 1 : 0)} className="py-8 text-center text-muted-foreground">
                    No data
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between pt-4 text-sm">
            <span className="text-muted-foreground">
              {sorted.length} rows &middot; Page {page + 1} of {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                className="rounded border px-3 py-1 hover:bg-muted disabled:opacity-40"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
              >
                Prev
              </button>
              <button
                className="rounded border px-3 py-1 hover:bg-muted disabled:opacity-40"
                disabled={page >= totalPages - 1}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
