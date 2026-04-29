/**
 * Widget: Dashboard warnings feed — overdue payments, fixed-date alerts, etc.
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DashboardWarning } from "@/types/api";

interface Props {
  warnings: DashboardWarning[];
}

const WARNING_ICONS: Record<string, string> = {
  overdue_payment: "🔴",
  fixed_date_payment: "📌",
  cash_gap_risk: "⚠️",
  accuracy_mismatch: "📐",
};

export function WarningsWidget({ warnings }: Props) {
  if (warnings.length === 0) return null;

  return (
    <Card className="border-warning/30">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-warning">
          Предупреждения
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {warnings.map((w, i) => (
          <div
            key={i}
            className="flex items-start gap-2 text-sm rounded-md bg-warning/5 px-3 py-2"
          >
            <span className="flex-shrink-0 mt-0.5">
              {WARNING_ICONS[w.type] ?? "⚠️"}
            </span>
            <span className="text-foreground">{w.message}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
