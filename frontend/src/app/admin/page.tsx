"use client";

import { ChevronDown, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import type { AdminTable } from "@/lib/types";
import { cn } from "@/lib/utils";

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function TableSection({ table }: { table: AdminTable }) {
  const [open, setOpen] = useState(table.count > 0);
  const columns =
    table.rows.length > 0 ? Object.keys(table.rows[0]) : [];

  return (
    <Card className="overflow-hidden rounded-2xl shadow-sm">
      <CardHeader className="cursor-pointer select-none pb-3" onClick={() => setOpen(!open)}>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <ChevronDown
              className={cn(
                "size-4 text-muted-foreground transition-transform",
                !open && "-rotate-90",
              )}
            />
            <CardTitle className="font-mono text-base">{table.name}</CardTitle>
          </div>
          <Badge variant={table.count > 0 ? "secondary" : "outline"}>
            {table.count} {table.count === 1 ? "row" : "rows"}
          </Badge>
        </div>
      </CardHeader>
      {open ? (
        <CardContent className="pt-0">
          {table.rows.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">No rows yet.</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    {columns.map((col) => (
                      <TableHead key={col} className="whitespace-nowrap font-mono text-xs">
                        {col}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {table.rows.map((row, i) => (
                    <TableRow key={i}>
                      {columns.map((col) => (
                        <TableCell
                          key={col}
                          className="max-w-xs truncate font-mono text-xs"
                          title={formatCell(row[col])}
                        >
                          {formatCell(row[col])}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          {table.count > table.rows.length ? (
            <p className="mt-2 text-xs text-muted-foreground">
              Showing {table.rows.length} of {table.count} rows.
            </p>
          ) : null}
        </CardContent>
      ) : null}
    </Card>
  );
}

export default function AdminPage() {
  const [tables, setTables] = useState<AdminTable[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAdminTables();
      setTables(data.tables);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load tables");
      setTables(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const totalRows = tables?.reduce((sum, t) => sum + t.count, 0) ?? 0;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Admin"
        description="Browse database tables and inspect stored records."
        action={
          <Button variant="outline" size="sm" disabled={loading} onClick={() => void load()}>
            <RefreshCw className={cn("size-4", loading && "animate-spin")} />
            Refresh
          </Button>
        }
      />

      {error ? (
        <p className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {error}
        </p>
      ) : null}

      {loading && !tables ? (
        <p className="text-sm text-muted-foreground">Loading tables…</p>
      ) : null}

      {tables ? (
        <>
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">{tables.length} tables</Badge>
            <Badge variant="outline">{totalRows} total rows</Badge>
          </div>
          <div className="space-y-4">
            {tables.map((table) => (
              <TableSection key={table.name} table={table} />
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}
