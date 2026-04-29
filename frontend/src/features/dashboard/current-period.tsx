/**
 * Widget: "Остаток на жизнь" — remaining money for living until next income.
 * Shows current and (optionally) next salary period in a single card.
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

function PeriodBlock({
  period,
  large = false,
}: {
  period: CurrentPeriod;
  large?: boolean;
}) {
  const cfg = STATUS_CONFIG[period.status] ?? STATUS_CONFIG.tight;
  const amountClass = large
    ? "text-3xl font-bold tracking-tight"
    : "text-xl font-bold tracking-tight";

  return (
    <>
      <div className="flex items-baseline gap-2">
        <span className={`${amountClass} ${cfg.color}`}>
          {formatMoney(period.remaining_for_living)}
        </span>
        <span className={`text-sm ${cfg.color}`}>{cfg.icon}</span>
      </div>
      <div className="mt-3 space-y-1 text-xs text-muted-foreground">
        <div className="flex justify-between">
          <span>Доход</span>
          <span className="font-medium text-foreground">
            {formatMoney(period.income)}
          </span>
        </div>
        <div className="flex justify-between">
          <span>Платежи</span>
          <span className="font-medium text-foreground">
            −{formatMoney(period.planned_payments_total)}
          </span>
        </div>
        <div className="border-t border-border pt-1 flex justify-between">
          <span>Период</span>
          <span>
            {formatDate(period.from_date)} — {formatDate(period.to_date)}
          </span>
        </div>
      </div>
    </>
  );
}

export function CurrentPeriodWidget({ current, next }: Props) {
  // Card border uses the worst status
  const statuses = [current.status, next?.status].filter(Boolean) as Array<
    "comfortable" | "tight" | "deficit"
  >;
  const priority = { deficit: 0, tight: 1, comfortable: 2 } as const;
  const worstStatus = statuses.reduce((a, b) =>
    priority[a] <= priority[b] ? a : b,
  );
  const borderClass =
    STATUS_CONFIG[worstStatus]?.border ?? STATUS_CONFIG.tight.border;

  return (
    <Card className={`${borderClass} border`}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Остаток на жизнь
        </CardTitle>
      </CardHeader>
      <CardContent>
        {next ? (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <PeriodBlock period={current} />
            </div>
            <div className="border-l border-border pl-4">
              <PeriodBlock period={next} />
            </div>
          </div>
        ) : (
          <PeriodBlock period={current} large />
        )}
      </CardContent>
    </Card>
  );
}
