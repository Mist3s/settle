/**
 * History page — feed of actual payments with filters.
 */

import { useState, useMemo } from "react";
import { LoadingState } from "@/components/loading-state";
import { useActualPayments, useDeleteActualPayment } from "@/features/payments/hooks";
import { useLoans } from "@/features/loans/hooks";
import { PaymentCard } from "@/features/payments/payment-card";
import {
  PaymentFilters,
  type PaymentFilterValues,
} from "@/features/payments/payment-filters";
import type { LoanResponse } from "@/types/api";

export function HistoryPage() {
  const [filters, setFilters] = useState<PaymentFilterValues>({
    loan_id: "all",
    type: "all",
    from: "",
    to: "",
  });

  const queryParams = useMemo(() => {
    const p: { loan_id?: string; from?: string; to?: string } = {};
    if (filters.loan_id !== "all") p.loan_id = filters.loan_id;
    if (filters.from) p.from = filters.from;
    if (filters.to) p.to = filters.to;
    return p;
  }, [filters]);

  const { data: payments, isLoading, isError } = useActualPayments(queryParams);
  const { data: loans } = useLoans();
  const deleteMutation = useDeleteActualPayment();

  // Loans lookup
  const loansMap = useMemo(() => {
    const m = new Map<string, LoanResponse>();
    for (const l of loans ?? []) m.set(l.id, l);
    return m;
  }, [loans]);

  // Client-side type filter
  const filtered = useMemo(() => {
    if (!payments) return [];
    if (filters.type === "all") return payments;
    return payments.filter((p) => p.payment_type === filters.type);
  }, [payments, filters.type]);

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-semibold tracking-tight">
        История платежей
      </h2>

      <PaymentFilters filters={filters} onChange={setFilters} />

      <LoadingState
        isLoading={isLoading}
        isError={isError}
        isEmpty={filtered.length === 0}
        emptyMessage="Нет платежей, соответствующих фильтрам"
        skeletonCount={5}
        skeletonHeight="h-24"
      >
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {filtered.map((payment) => (
            <PaymentCard
              key={payment.id}
              payment={payment}
              loan={loansMap.get(payment.loan_id)}
              onDelete={(id) => deleteMutation.mutate(id)}
            />
          ))}
        </div>
      </LoadingState>
    </div>
  );
}
