/**
 * TanStack Query hooks for Settings and Import/Export features.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getSettings, updateSettings } from "@/api/settings";
import {
  uploadExcel,
  commitImport,
  downloadTemplate,
  exportExcel,
} from "@/api/import-export";
import type { SettingsUpdate } from "@/types/api";
import { toast } from "sonner";

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const settingsKeys = {
  all: ["settings"] as const,
};

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

export function useSettings() {
  return useQuery({
    queryKey: settingsKeys.all,
    queryFn: getSettings,
  });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: SettingsUpdate) => updateSettings(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: settingsKeys.all });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["forecast"] });
      toast.success("Настройки сохранены");
    },
    onError: () => toast.error("Ошибка сохранения настроек"),
  });
}

// ---------------------------------------------------------------------------
// Import
// ---------------------------------------------------------------------------

export function useUploadImport() {
  return useMutation({
    mutationFn: (file: File) => uploadExcel(file),
    onError: () => toast.error("Ошибка загрузки файла"),
  });
}

export function useCommitImport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (importId: string) => commitImport(importId),
    onSuccess: () => {
      qc.invalidateQueries();
      toast.success("Импорт завершён");
    },
    onError: () => toast.error("Ошибка применения импорта"),
  });
}

// ---------------------------------------------------------------------------
// Export / Template (non-mutation — trigger download)
// ---------------------------------------------------------------------------

export function useDownloadTemplate() {
  return useMutation({
    mutationFn: (withExamples: boolean) => downloadTemplate(withExamples),
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "settle_template.xlsx";
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Шаблон скачан");
    },
    onError: () => toast.error("Ошибка скачивания шаблона"),
  });
}

export function useExportExcel() {
  return useMutation({
    mutationFn: (since?: string) => exportExcel(since),
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `settle_export_${new Date().toISOString().slice(0, 10)}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Экспорт скачан");
    },
    onError: () => toast.error("Ошибка экспорта"),
  });
}
