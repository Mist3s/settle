/**
 * Day cell for the calendar grid.
 * Shows colored dots for each payment on that day.
 */

import { cn } from "@/lib/utils";
import { loanTypeColor } from "@/lib/format";
import { isToday, isSameMonth } from "date-fns";
import type { PlannedPaymentResponse, LoanResponse } from "@/types/api";

interface DayCellProps {
  date: Date;
  month: Date;
  payments: PlannedPaymentResponse[];
  loansMap: Map<string, LoanResponse>;
  onClick: (date: Date, payments: PlannedPaymentResponse[]) => void;
}

export function DayCell({
  date,
  month,
  payments,
  loansMap,
  onClick,
}: DayCellProps) {
  const inMonth = isSameMonth(date, month);
  const today = isToday(date);
  const hasPayments = payments.length > 0;
  const totalAmount = payments.reduce((s, p) => s + Number(p.amount), 0);

  return (
    <button
      type="button"
      onClick={() => hasPayments && onClick(date, payments)}
      className={cn(
        "relative flex flex-col items-center justify-start gap-0.5 rounded-lg p-1.5 text-sm transition-colors min-h-[4.5rem]",
        inMonth
          ? "text-foreground hover:bg-accent/50"
          : "text-muted-foreground/40",
        today && "ring-2 ring-primary/50 bg-primary/5",
        hasPayments && inMonth && "cursor-pointer",
        !hasPayments && "cursor-default",
      )}
    >
      {/* Day number */}
      <span
        className={cn(
          "text-xs font-medium",
          today && "text-primary font-bold",
        )}
      >
        {date.getDate()}
      </span>

      {/* Payment dots */}
      {hasPayments && inMonth && (
        <>
          <div className="flex flex-wrap gap-0.5 justify-center">
            {payments.slice(0, 4).map((p) => {
              const loan = loansMap.get(p.loan_id);
              const color = loan ? loanTypeColor(loan.loan_type) : "bg-gray-400";
              return (
                <span
                  key={p.id}
                  className={cn("size-1.5 rounded-full", color)}
                />
              );
            })}
            {payments.length > 4 && (
              <span className="text-[8px] text-muted-foreground">
                +{payments.length - 4}
              </span>
            )}
          </div>
          <span className="text-[10px] tabular-nums text-muted-foreground mt-auto">
            {Math.round(totalAmount).toLocaleString("ru-RU")} ₽
          </span>
        </>
      )}
    </button>
  );
}
