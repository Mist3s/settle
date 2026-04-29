/**
 * Calendar page — monthly view of planned payments.
 */

import { useState, useMemo, useCallback } from "react";
import {
  addMonths,
  subMonths,
  startOfMonth,
  endOfMonth,
  format,
} from "date-fns";
import { Button } from "@/components/ui/button";
import { LoadingState } from "@/components/loading-state";
import { CalendarHeader } from "@/features/calendar/calendar-header";
import { CalendarGrid } from "@/features/calendar/calendar-grid";
import { useCalendarPayments, useCalendarLoans } from "@/features/calendar/hooks";
import { RegisterPaymentDialog } from "@/features/payments/register-payment-dialog";
import type { LoanResponse } from "@/types/api";

export function CalendarPage() {
  const [month, setMonth] = useState(() => startOfMonth(new Date()));
  const [showRegister, setShowRegister] = useState(false);

  // Date range for query
  const from = format(startOfMonth(month), "yyyy-MM-dd");
  const to = format(endOfMonth(month), "yyyy-MM-dd");

  const {
    data: payments,
    isLoading: paymentsLoading,
    isError: paymentsError,
  } = useCalendarPayments(from, to);

  const { data: loans } = useCalendarLoans();

  // Loan lookup map
  const loansMap = useMemo(() => {
    const m = new Map<string, LoanResponse>();
    for (const l of loans ?? []) {
      m.set(l.id, l);
    }
    return m;
  }, [loans]);

  const handlePrev = useCallback(() => setMonth((m) => subMonths(m, 1)), []);
  const handleNext = useCallback(() => setMonth((m) => addMonths(m, 1)), []);
  const handleToday = useCallback(
    () => setMonth(startOfMonth(new Date())),
    [],
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-2xl font-semibold tracking-tight">
          Календарь платежей
        </h2>
        <Button onClick={() => setShowRegister(true)}>
          + Платёж
        </Button>
      </div>

      <CalendarHeader
        currentMonth={month}
        onPrev={handlePrev}
        onNext={handleNext}
        onToday={handleToday}
      />

      <LoadingState
        isLoading={paymentsLoading}
        isError={paymentsError}
        isEmpty={(payments ?? []).length === 0}
        emptyMessage="Нет плановых платежей в этом месяце"
        skeletonCount={6}
        skeletonHeight="h-16"
      >
        <CalendarGrid
          month={month}
          payments={payments ?? []}
          loansMap={loansMap}
        />
      </LoadingState>

      <RegisterPaymentDialog
        open={showRegister}
        onOpenChange={setShowRegister}
      />
    </div>
  );
}
