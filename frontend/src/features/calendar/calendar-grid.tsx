/**
 * Calendar grid — month view with day cells and payment dots.
 *
 * Desktop: 7-column grid (Mon–Sun)
 * Mobile: vertical list of days with payments
 */

import { useMemo, useState, useCallback } from "react";
import {
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  eachDayOfInterval,
  format,
  isSameDay,
} from "date-fns";
import { ru } from "date-fns/locale";
import { useMediaQuery } from "@/hooks/use-media-query";
import { DayCell } from "./day-cell";
import { DayDetail } from "./day-detail";
import { Badge } from "@/components/ui/badge";
import {
  formatMoney,
  paymentStatusLabel,
  loanTypeLabel,
  loanTypeColor,
} from "@/lib/format";
import { cn } from "@/lib/utils";
import type { PlannedPaymentResponse, LoanResponse } from "@/types/api";

interface CalendarGridProps {
  month: Date;
  payments: PlannedPaymentResponse[];
  loansMap: Map<string, LoanResponse>;
}

const WEEKDAY_LABELS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

export function CalendarGrid({ month, payments, loansMap }: CalendarGridProps) {
  const isDesktop = useMediaQuery("(min-width: 640px)");
  const [selectedDay, setSelectedDay] = useState<{
    date: Date;
    payments: PlannedPaymentResponse[];
  } | null>(null);

  // Build payment lookup by date string
  const paymentsByDate = useMemo(() => {
    const map = new Map<string, PlannedPaymentResponse[]>();
    for (const p of payments) {
      const key = p.due_date;
      const list = map.get(key) ?? [];
      list.push(p);
      map.set(key, list);
    }
    return map;
  }, [payments]);

  // Calendar days grid (6 weeks to always fill)
  const days = useMemo(() => {
    const start = startOfWeek(startOfMonth(month), { weekStartsOn: 1 });
    const end = endOfWeek(endOfMonth(month), { weekStartsOn: 1 });
    return eachDayOfInterval({ start, end });
  }, [month]);

  // Days with payments (for mobile list)
  const daysWithPayments = useMemo(() => {
    const monthStart = startOfMonth(month);
    const monthEnd = endOfMonth(month);
    return days
      .filter((d) => {
        const key = format(d, "yyyy-MM-dd");
        return (
          d >= monthStart &&
          d <= monthEnd &&
          (paymentsByDate.get(key)?.length ?? 0) > 0
        );
      })
      .map((d) => ({
        date: d,
        payments: paymentsByDate.get(format(d, "yyyy-MM-dd")) ?? [],
      }));
  }, [days, month, paymentsByDate]);

  const handleDayClick = useCallback(
    (date: Date, dayPayments: PlannedPaymentResponse[]) => {
      if (
        selectedDay &&
        isSameDay(selectedDay.date, date)
      ) {
        setSelectedDay(null);
      } else {
        setSelectedDay({ date, payments: dayPayments });
      }
    },
    [selectedDay],
  );

  // -----------------------------------------------------------------------
  // Desktop: 7-column grid
  // -----------------------------------------------------------------------
  if (isDesktop) {
    return (
      <div className="space-y-3">
        {/* Weekday headers */}
        <div className="grid grid-cols-7 gap-px">
          {WEEKDAY_LABELS.map((d) => (
            <div
              key={d}
              className="text-center text-xs font-medium text-muted-foreground py-1"
            >
              {d}
            </div>
          ))}
        </div>

        {/* Day cells */}
        <div className="grid grid-cols-7 gap-px rounded-lg border bg-border overflow-hidden">
          {days.map((date) => {
            const key = format(date, "yyyy-MM-dd");
            const dayPayments = paymentsByDate.get(key) ?? [];
            return (
              <div key={key} className="bg-card">
                <DayCell
                  date={date}
                  month={month}
                  payments={dayPayments}
                  loansMap={loansMap}
                  onClick={handleDayClick}
                />
              </div>
            );
          })}
        </div>

        {/* Day detail */}
        {selectedDay && (
          <DayDetail
            date={selectedDay.date}
            payments={selectedDay.payments}
            loansMap={loansMap}
            onClose={() => setSelectedDay(null)}
          />
        )}
      </div>
    );
  }

  // -----------------------------------------------------------------------
  // Mobile: vertical list of days with payments
  // -----------------------------------------------------------------------
  return (
    <div className="space-y-3">
      {daysWithPayments.length === 0 && (
        <p className="text-center text-sm text-muted-foreground py-8">
          Нет платежей в этом месяце
        </p>
      )}
      {daysWithPayments.map(({ date, payments: dayPayments }) => (
        <div
          key={format(date, "yyyy-MM-dd")}
          className="rounded-lg border bg-card p-3 space-y-2"
        >
          <p className="text-sm font-semibold">
            {format(date, "d MMMM, EEEE", { locale: ru })}
          </p>
          {dayPayments.map((p) => {
            const loan = loansMap.get(p.loan_id);
            const color = loan
              ? loanTypeColor(loan.loan_type)
              : "bg-gray-400";
            return (
              <div
                key={p.id}
                className="flex items-center justify-between gap-2"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className={cn("size-2 rounded-full shrink-0", color)} />
                  <span className="text-sm truncate">
                    {loan?.name ?? "—"}
                    {loan && (
                      <span className="text-muted-foreground ml-1 text-xs">
                        {loanTypeLabel(loan.loan_type)}
                      </span>
                    )}
                  </span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {p.can_pay_early && (
                    <span className="text-xs" title="Можно заранее">
                      ⏩
                    </span>
                  )}
                  <Badge
                    variant={
                      p.status === "overdue"
                        ? "destructive"
                        : p.status === "paid"
                          ? "default"
                          : "outline"
                    }
                    className="text-[10px]"
                  >
                    {paymentStatusLabel(p.status)}
                  </Badge>
                  <span className="font-medium tabular-nums text-sm">
                    {formatMoney(p.amount)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
