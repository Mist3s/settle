/**
 * Widget: "Общий долг" — total debt, active loans count, month-to-month delta.
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatMoney, formatDelta, deltaColor } from "@/lib/format";
import type { DashboardTotals } from "@/types/api";

interface Props {
  totals: DashboardTotals;
}

export function TotalsWidget({ totals }: Props) {
  const delta = formatDelta(totals.month_to_month_change);
  const dColor = deltaColor(totals.month_to_month_change);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Общий долг
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-bold tracking-tight">
            {formatMoney(totals.total_debt)}
          </span>
          {delta && (
            <span className={`text-sm font-medium ${dColor}`}>{delta}</span>
          )}
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          {totals.active_loans}{" "}
          {totals.active_loans === 1
            ? "активный кредит"
            : totals.active_loans < 5
              ? "активных кредита"
              : "активных кредитов"}
        </p>
      </CardContent>
    </Card>
  );
}
