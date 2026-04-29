/**
 * Widget: "Остаток на жизнь" — remaining money for living until next income.
 * Shows current period full-size and next period as a compact summary below.
 * Traffic-light indicator: comfortable (green), tight (yellow), deficit (red).
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatMoney, formatDate } from "@/lib/format";
import type { CurrentPeriod } from "@/types/api";

interface Props {
  current: CurrentPeriod;
  next?: CurrentPeriod | null;
}

const STATUS_CONFIG = {
  comfortable: {
    color: "text-success",
    bg: "bg-success/10",
    border: "border-success/30",
    label: "Комфортно",
    icon: "✓",
  },
  tight: {
    color: "text-warning",
    bg: "bg-warning/10",
    border: "border-warning/30",
    label: "Тесно",
    icon: "⚠",
  },
  deficit: {
    color: "text-danger",
    bg: "bg-danger/10",
    border: "border-danger/30",
    label: "Дефицит",
    icon: "✕",
  },
} as const;

export function CurrentPeriodWidget({ current, next }: Props) {
  const cfg = STATUS_CONFIG[current.status] ?? STATUS_CONFIG.tight;

  return (
    <Card className={`${cfg.border} border`}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Остаток на жизнь
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Current period — full size, original style */}
        <div className="flex items-baseline gap-2">
          <span className={`text-3xl font-bold tracking-tight ${cfg.color}`}>
            {formatMoney(current.remaining_for_living)}
          </span>
          <span className={`text-sm ${cfg.color}`}>{cfg.icon}</span>
        </div>
        <div className="mt-3 space-y-1 text-xs text-muted-foreground">
          <div className="flex justify-between">
            <span>Доход</span>
            <span className="font-medium text-foreground">
              {formatMoney(current.income)}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Платежи</span>
            <span className="font-medium text-foreground">
              −{formatMoney(current.planned_payments_total)}
            </span>
          </div>
          <div className="border-t border-border pt-1 flex justify-between">
            <span>Период</span>
            <span>
              {formatDate(current.from_date)} — {formatDate(current.to_date)}
            </span>
          </div>
        </div>

        {/* Next period — compact summary */}
        {next && (
          <NextPeriodSummary period={next} />
        )}
      </CardContent>
    </Card>
  );
}

function NextPeriodSummary({ period }: { period: CurrentPeriod }) {
  const cfg = STATUS_CONFIG[period.status] ?? STATUS_CONFIG.tight;

  return (
    <div className={`mt-3 rounded-md ${cfg.bg} px-3 py-2`}>
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          {formatDate(period.from_date)} — {formatDate(period.to_date)}
        </span>
        <span className={`text-sm font-semibold ${cfg.color}`}>
          {formatMoney(period.remaining_for_living)}
        </span>
      </div>
      <div className="flex gap-3 mt-0.5 text-[10px] text-muted-foreground">
        <span>Доход {formatMoney(period.income)}</span>
        <span>Платежи −{formatMoney(period.planned_payments_total)}</span>
      </div>
    </div>
  );
}
