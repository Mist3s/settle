/**
 * Day detail panel — shows list of payments for a selected day.
 * Displayed as a card below the calendar grid.
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { format } from "date-fns";
import {
  formatMoney,
  formatDate,
  paymentStatusLabel,
  loanTypeLabel,
} from "@/lib/format";
import type { PlannedPaymentResponse, LoanResponse } from "@/types/api";

interface DayDetailProps {
  date: Date;
  payments: PlannedPaymentResponse[];
  loansMap: Map<string, LoanResponse>;
  onClose: () => void;
}

const STATUS_VARIANT: Record<
  string,
  "default" | "secondary" | "outline" | "destructive"
> = {
  pending: "outline",
  paid: "default",
  partial: "secondary",
  overdue: "destructive",
  skipped: "secondary",
  cancelled: "secondary",
};

export function DayDetail({ date, payments, loansMap, onClose }: DayDetailProps) {
  const total = payments.reduce((s, p) => s + Number(p.amount), 0);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-base">
          {formatDate(format(date, "yyyy-MM-dd"))}
        </CardTitle>
        <button
          type="button"
          onClick={onClose}
          className="text-muted-foreground hover:text-foreground text-sm"
          aria-label="Закрыть"
        >
          ✕
        </button>
      </CardHeader>
      <CardContent className="space-y-3">
        {payments.map((p) => {
          const loan = loansMap.get(p.loan_id);
          return (
            <div
              key={p.id}
              className="flex items-center justify-between gap-3 rounded-lg border p-3"
            >
              <div className="min-w-0 flex-1">
                <p className="font-medium text-sm truncate">
                  {loan?.name ?? "—"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {loan ? `${loan.creditor} · ${loanTypeLabel(loan.loan_type)}` : "—"}
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {p.can_pay_early && (
                  <span
                    className="text-xs"
                    title="Можно оплатить заранее"
                  >
                    ⏩
                  </span>
                )}
                <Badge variant={STATUS_VARIANT[p.status] ?? "outline"}>
                  {paymentStatusLabel(p.status)}
                </Badge>
                <span className="font-semibold tabular-nums text-sm">
                  {formatMoney(p.amount)}
                </span>
              </div>
            </div>
          );
        })}

        {/* Total */}
        <div className="flex items-center justify-between border-t pt-3">
          <span className="text-sm text-muted-foreground">Итого</span>
          <span className="font-bold tabular-nums">
            {formatMoney(total.toFixed(2))}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
