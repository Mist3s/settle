/**
 * Import & Export API module.
 */

import client from "./client";
import type { DryRunReport, CommitResult } from "@/types/api";

export async function uploadExcel(file: File): Promise<DryRunReport> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await client.post<DryRunReport>("/import/excel", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function commitImport(importId: string): Promise<CommitResult> {
  const { data } = await client.post<CommitResult>("/import/excel/commit", {
    import_id: importId,
  });
  return data;
}

export async function downloadTemplate(
  withExamples = false,
): Promise<Blob> {
  const { data } = await client.get<Blob>("/import/template", {
    params: withExamples ? { with_examples: "true" } : undefined,
    responseType: "blob",
  });
  return data;
}

export async function exportExcel(since?: string): Promise<Blob> {
  const { data } = await client.get<Blob>("/export/excel", {
    params: since ? { since } : undefined,
    responseType: "blob",
  });
  return data;
}
