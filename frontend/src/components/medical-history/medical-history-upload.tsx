"use client";

import {
  CheckCircle2,
  FileText,
  Loader2,
  RotateCcw,
  Sparkles,
  Trash2,
  UploadCloud,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api, ApiError } from "@/lib/api";
import { DEFAULT_PATIENT_ID } from "@/lib/profile-storage";
import type {
  LabReport,
  LabReportDetail,
  MedicalHistoryExtraction,
} from "@/lib/types";
import { cn } from "@/lib/utils";

const MAX_BYTES = 25 * 1024 * 1024; // mirrors the backend's 25 MB guard.

function statusBadge(status: string) {
  switch (status) {
    case "parsed":
      return <Badge variant="secondary">Parsed</Badge>;
    case "raw_only":
      return <Badge variant="outline">Text only</Badge>;
    case "needs_review":
      return <Badge variant="destructive">Needs review</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

function fmtDate(ts?: string | null) {
  if (!ts) return "—";
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleDateString();
}

function fmtBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function ExtractedTable({ detail }: { detail: LabReportDetail }) {
  if (detail.observations.length === 0) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">
          No structured values were extracted from this document
          {detail.status === "raw_only" ? " — only raw text was captured." : "."}
        </p>
        {detail.raw_text ? (
          <pre className="max-h-72 overflow-auto rounded-lg bg-muted/40 p-3 text-xs leading-relaxed text-muted-foreground">
            {detail.raw_text.slice(0, 4000)}
          </pre>
        ) : null}
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Test</TableHead>
          <TableHead>Result</TableHead>
          <TableHead>Unit</TableHead>
          <TableHead>Reference</TableHead>
          <TableHead>Flag</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {detail.observations.map((obs) => (
          <TableRow key={obs.id}>
            <TableCell className="font-medium">{obs.test_name}</TableCell>
            <TableCell className="tabular-nums">
              {obs.value_text ?? (obs.value_num != null ? String(obs.value_num) : "—")}
            </TableCell>
            <TableCell className="text-muted-foreground">{obs.unit ?? "—"}</TableCell>
            <TableCell className="text-muted-foreground">
              {obs.reference_range ?? "—"}
            </TableCell>
            <TableCell>
              {obs.flag ? (
                <Badge variant="destructive">{obs.flag}</Badge>
              ) : (
                <span className="text-muted-foreground">—</span>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function ProfileExtractionCard({
  extraction,
}: {
  extraction: MedicalHistoryExtraction;
}) {
  const addedCount =
    (extraction.name ? 1 : 0) +
    (extraction.age ? 1 : 0) +
    extraction.conditions_added.length +
    extraction.allergies_added.length +
    extraction.medications_added.length +
    (extraction.notes_added ? 1 : 0);

  return (
    <Card>
      <CardHeader className="border-b">
        <div className="flex items-center gap-2">
          <Sparkles className="size-4 text-violet-600 dark:text-violet-400" />
          <CardTitle>Profile updated from this document</CardTitle>
        </div>
        <CardDescription>
          The AI read the document and added only the fields it actually found —
          nothing was invented.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 pt-4">
        {extraction.error ? (
          <p className="text-sm text-muted-foreground">
            Automatic extraction was unavailable for this upload
            {extraction.error ? ` (${extraction.error})` : ""}. The document and any
            lab values were still saved.
          </p>
        ) : addedCount === 0 ? (
          <p className="text-sm text-muted-foreground">
            No new profile fields were found in this document — everything it
            contains is already on file.
          </p>
        ) : (
          <div className="space-y-3">
            {extraction.name || extraction.age ? (
              <div className="flex flex-wrap gap-2">
                {extraction.name ? (
                  <Badge variant="secondary">Name: {extraction.name}</Badge>
                ) : null}
                {extraction.age ? (
                  <Badge variant="secondary">Age: {extraction.age}</Badge>
                ) : null}
              </div>
            ) : null}
            {extraction.conditions_added.length > 0 ? (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-muted-foreground">
                  Conditions added
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {extraction.conditions_added.map((c) => (
                    <Badge key={c} variant="outline">
                      {c}
                    </Badge>
                  ))}
                </div>
              </div>
            ) : null}
            {extraction.allergies_added.length > 0 ? (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-muted-foreground">
                  Allergies added
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {extraction.allergies_added.map((a) => (
                    <Badge key={a} variant="destructive">
                      {a}
                    </Badge>
                  ))}
                </div>
              </div>
            ) : null}
            {extraction.medications_added.length > 0 ? (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-muted-foreground">
                  Medications added
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {extraction.medications_added.map((m) => (
                    <Badge key={m} variant="outline">
                      {m}
                    </Badge>
                  ))}
                </div>
              </div>
            ) : null}
            {extraction.notes_added ? (
              <p className="text-sm text-muted-foreground">Care notes were updated.</p>
            ) : null}
            <Link
              href="/profile"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
            >
              View updated profile
            </Link>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function MedicalHistoryUpload() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<LabReportDetail | null>(null);
  const [duplicate, setDuplicate] = useState(false);
  const [extraction, setExtraction] = useState<MedicalHistoryExtraction | null>(null);

  const [records, setRecords] = useState<LabReport[]>([]);
  const [recordsLoading, setRecordsLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const loadRecords = useCallback(async () => {
    setRecordsLoading(true);
    try {
      const list = await api.listLabRecords(DEFAULT_PATIENT_ID);
      setRecords(list);
    } catch {
      setRecords([]);
    } finally {
      setRecordsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadRecords();
  }, [loadRecords]);

  const handleFile = useCallback(
    async (file: File) => {
      setError(null);
      setDetail(null);
      setDuplicate(false);
      setExtraction(null);

      const isPdf =
        file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
      if (!isPdf) {
        setError("Please choose a PDF file.");
        return;
      }
      if (file.size === 0) {
        setError("That file is empty.");
        return;
      }
      if (file.size > MAX_BYTES) {
        setError(`File is too large (max ${fmtBytes(MAX_BYTES)}).`);
        return;
      }

      setUploading(true);
      try {
        const result = await api.uploadLabRecord(file, DEFAULT_PATIENT_ID);
        setDuplicate(result.duplicate);
        setExtraction(result.profile ?? null);
        // Pull the parsed report so we can show the extracted information.
        const full = await api.getLabRecord(result.report_id);
        setDetail(full);
        await loadRecords();
      } catch (err: unknown) {
        if (err instanceof ApiError && err.status === 415) {
          setError("The server rejected the file — it must be a valid PDF.");
        } else if (err instanceof ApiError && err.status === 413) {
          setError("The server rejected the file — it is too large.");
        } else {
          setError(err instanceof Error ? err.message : "Upload failed.");
        }
      } finally {
        setUploading(false);
      }
    },
    [loadRecords],
  );

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (file) void handleFile(file);
    },
    [handleFile],
  );

  async function openRecord(reportId: number) {
    setError(null);
    setDuplicate(false);
    setExtraction(null);
    try {
      const full = await api.getLabRecord(reportId);
      setDetail(full);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load record.");
    }
  }

  async function removeRecord(rec: LabReport) {
    const label = rec.document_filename ?? `Report #${rec.id}`;
    const ok = window.confirm(
      `Remove "${label}" from this patient's records? This cannot be undone.`,
    );
    if (!ok) return;

    setError(null);
    setDeletingId(rec.id);
    try {
      await api.deleteLabRecord(rec.id);
      if (detail?.id === rec.id) {
        setDetail(null);
        setExtraction(null);
        setDuplicate(false);
      }
      await loadRecords();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to remove document.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="space-y-6 pb-12">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Medical history</h1>
        <p className="max-w-xl text-muted-foreground">
          Upload a lab results or medical-history PDF. Guardian reads it, extracts
          the patient details it finds — name, age, conditions, allergies,
          medications — into the profile, and keeps the original document. It only
          records what is actually in the file.
        </p>
      </div>

      {/* Upload card */}
      <Card>
        <CardHeader className="border-b">
          <div className="flex items-center gap-2">
            <UploadCloud className="size-4 text-muted-foreground" />
            <CardTitle>Upload a document</CardTitle>
          </div>
          <CardDescription>PDF files up to {fmtBytes(MAX_BYTES)}</CardDescription>
        </CardHeader>
        <CardContent className="pt-5">
          <div
            role="button"
            tabIndex={0}
            onClick={() => !uploading && inputRef.current?.click()}
            onKeyDown={(e) => {
              if ((e.key === "Enter" || e.key === " ") && !uploading) {
                e.preventDefault();
                inputRef.current?.click();
              }
            }}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            className={cn(
              "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-border/80 bg-muted/20 px-6 py-12 text-center transition-colors outline-none hover:border-primary/40 hover:bg-muted/40 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
              dragging && "border-primary/60 bg-primary/5",
              uploading && "pointer-events-none opacity-70",
            )}
          >
            {uploading ? (
              <Loader2 className="size-8 animate-spin text-primary" />
            ) : (
              <UploadCloud className="size-8 text-muted-foreground" />
            )}
            <div className="space-y-1">
              <p className="text-sm font-medium">
                {uploading
                  ? "Uploading and extracting…"
                  : "Drag & drop a PDF here, or click to browse"}
              </p>
              <p className="text-xs text-muted-foreground">
                We&apos;ll read the file and pull out the lab values automatically.
              </p>
            </div>
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void handleFile(file);
                e.target.value = ""; // allow re-selecting the same file
              }}
            />
          </div>

          {error ? (
            <p className="mt-4 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-2.5 text-sm text-destructive">
              {error}
            </p>
          ) : null}
        </CardContent>
      </Card>

      {/* AI profile extraction */}
      {extraction ? <ProfileExtractionCard extraction={extraction} /> : null}

      {/* Extracted information */}
      {detail ? (
        <Card>
          <CardHeader className="border-b">
            <div className="flex items-center justify-between gap-2">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="size-4 text-emerald-600 dark:text-emerald-500" />
                  <CardTitle>Extracted information</CardTitle>
                </div>
                <CardDescription>
                  {detail.document_filename ?? "Uploaded document"} ·{" "}
                  {detail.observation_count}{" "}
                  {detail.observation_count === 1 ? "value" : "values"} found
                  {duplicate ? " · already on file" : ""}
                </CardDescription>
              </div>
              {statusBadge(detail.status)}
            </div>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div className="grid gap-3 text-sm sm:grid-cols-3">
              <div>
                <p className="text-xs text-muted-foreground">Lab</p>
                <p className="font-medium">{detail.lab_name ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Collected</p>
                <p className="font-medium">{fmtDate(detail.collected_at)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Reported</p>
                <p className="font-medium">{fmtDate(detail.reported_at)}</p>
              </div>
            </div>
            <ExtractedTable detail={detail} />
          </CardContent>
        </Card>
      ) : null}

      {/* Previously uploaded records */}
      <Card>
        <CardHeader className="border-b">
          <div className="flex items-center justify-between gap-2">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <FileText className="size-4 text-muted-foreground" />
                <CardTitle>Uploaded records</CardTitle>
              </div>
              <CardDescription>Documents already on file for this patient</CardDescription>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void loadRecords()}
            >
              <RotateCcw />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          {recordsLoading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              Loading records…
            </p>
          ) : records.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No documents uploaded yet.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Document</TableHead>
                  <TableHead>Uploaded</TableHead>
                  <TableHead>Values</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {records.map((rec) => (
                  <TableRow key={rec.id}>
                    <TableCell className="font-medium">
                      {rec.document_filename ?? `Report #${rec.id}`}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {fmtDate(rec.created_at)}
                    </TableCell>
                    <TableCell className="tabular-nums">{rec.observation_count}</TableCell>
                    <TableCell>{statusBadge(rec.status)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => void openRecord(rec.id)}
                        >
                          View
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          disabled={deletingId === rec.id}
                          aria-label={`Remove ${rec.document_filename ?? `report ${rec.id}`}`}
                          onClick={() => void removeRecord(rec)}
                        >
                          {deletingId === rec.id ? (
                            <Loader2 className="size-4 animate-spin" />
                          ) : (
                            <Trash2 className="size-4 text-destructive" />
                          )}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
