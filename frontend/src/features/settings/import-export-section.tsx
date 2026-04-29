/**
 * Import/Export section for the Settings page.
 * - Download template (empty / with examples)
 * - Upload Excel → dry-run report → commit
 * - Export XLSX
 */

import { useState, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  useDownloadTemplate,
  useUploadImport,
  useCommitImport,
  useExportExcel,
} from "./hooks";
import type { DryRunReport, ImportError as IError } from "@/types/api";
import {
  Download,
  Upload,
  FileSpreadsheet,
  CheckCircle,
  AlertTriangle,
  XCircle,
} from "lucide-react";

function ErrorList({
  title,
  items,
  variant,
}: {
  title: string;
  items: IError[];
  variant: "danger" | "warning";
}) {
  if (!items.length) return null;
  return (
    <div className="space-y-1">
      <p className={`text-sm font-medium ${variant === "danger" ? "text-danger" : "text-warning"}`}>
        {title} ({items.length})
      </p>
      <div className="max-h-40 overflow-y-auto rounded border p-2 text-xs">
        {items.map((e, i) => (
          <div key={i} className="flex gap-2">
            {variant === "danger" ? (
              <XCircle className="mt-0.5 h-3 w-3 shrink-0 text-danger" />
            ) : (
              <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-warning" />
            )}
            <span>
              {e.sheet}
              {e.row != null && `:${e.row}`}
              {e.column && ` [${e.column}]`}
              {" — "}
              {e.message}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ImportExportSection() {
  const templateMut = useDownloadTemplate();
  const uploadMut = useUploadImport();
  const commitMut = useCommitImport();
  const exportMut = useExportExcel();

  const [report, setReport] = useState<DryRunReport | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    uploadMut.mutate(file, {
      onSuccess: (data) => setReport(data),
    });
    // Reset input so same file can be re-selected
    e.target.value = "";
  }

  function handleCommit() {
    if (!report) return;
    commitMut.mutate(report.import_id, {
      onSuccess: () => setReport(null),
    });
  }

  const hasErrors = (report?.errors?.length ?? 0) > 0;

  return (
    <div className="space-y-6">
      {/* Template download */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Шаблон импорта</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Button
            variant="outline"
            onClick={() => templateMut.mutate(false)}
            disabled={templateMut.isPending}
          >
            <Download className="mr-2 h-4 w-4" />
            Пустой шаблон
          </Button>
          <Button
            variant="outline"
            onClick={() => templateMut.mutate(true)}
            disabled={templateMut.isPending}
          >
            <Download className="mr-2 h-4 w-4" />
            С примерами
          </Button>
        </CardContent>
      </Card>

      {/* Import */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Импорт данных</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              ref={fileRef}
              type="file"
              accept=".xlsx"
              className="hidden"
              onChange={handleFileChange}
            />
            <Button
              variant="outline"
              onClick={() => fileRef.current?.click()}
              disabled={uploadMut.isPending}
            >
              <Upload className="mr-2 h-4 w-4" />
              {uploadMut.isPending ? "Загрузка…" : "Загрузить XLSX"}
            </Button>
          </div>

          {/* Dry-run report */}
          {report && (
            <div className="space-y-3 rounded-lg border p-4">
              <div className="flex items-center gap-2">
                <FileSpreadsheet className="h-5 w-5 text-primary" />
                <span className="font-medium">Результат проверки</span>
                {!hasErrors && (
                  <Badge
                    variant="outline"
                    className="border-success text-success"
                  >
                    <CheckCircle className="mr-1 h-3 w-3" />
                    Без ошибок
                  </Badge>
                )}
              </div>

              {/* Summary */}
              <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
                {Object.entries(report.summary).map(([key, diff]) => (
                  <div key={key} className="rounded border p-2 text-center">
                    <p className="text-xs text-muted-foreground">{key}</p>
                    <p className="font-medium">
                      +{diff.to_create} / ~{diff.to_update}
                    </p>
                  </div>
                ))}
              </div>

              <ErrorList
                title="Ошибки"
                items={report.errors}
                variant="danger"
              />
              <ErrorList
                title="Предупреждения"
                items={report.warnings}
                variant="warning"
              />

              <Separator />

              <div className="flex gap-2">
                <Button
                  onClick={handleCommit}
                  disabled={hasErrors || commitMut.isPending}
                >
                  <CheckCircle className="mr-2 h-4 w-4" />
                  {commitMut.isPending ? "Применение…" : "Применить импорт"}
                </Button>
                <Button variant="outline" onClick={() => setReport(null)}>
                  Отмена
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Export */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Экспорт данных</CardTitle>
        </CardHeader>
        <CardContent>
          <Button
            variant="outline"
            onClick={() => exportMut.mutate(undefined)}
            disabled={exportMut.isPending}
          >
            <FileSpreadsheet className="mr-2 h-4 w-4" />
            {exportMut.isPending ? "Экспорт…" : "Скачать XLSX"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
