/**
 * Analytics hooks — local computations from existing API data.
 * No new backend endpoints needed.
 */

import { useMemo } from "react";
import { useLoans } from "@/features/loans/hooks";
import { usePlannedPayments } from "@/features/payments/hooks";

// ---------------------------------------------------------------------------
// Payment breakdown by month (principal vs interest vs installment)
// ---------------------------------------------------------------------------

export interface MonthlyBreakdown {
  month: string; // "2026-05"
  principal: number;
  interest: number;
  installment: number;
}

export function usePaymentBreakdown() {
  const { data: payments } = usePlannedPayments({});

  return useMemo(() => {
    if (!payments) return [];
    const map = new Map<string, MonthlyBreakdown>();
    for (const p of payments) {
      const month = p.due_date.slice(0, 7); // "YYYY-MM"
      if (!map.has(month)) {
        map.set(month, { month, principal: 0, interest: 0, installment: 0 });
      }
      const entry = map.get(month)!;
      const principal = Number(p.principal_part ?? "0");
      const interest = Number(p.interest_part ?? "0");
      const amount = Number(p.amount);

      if (principal > 0 || interest > 0) {
        entry.principal += principal;
        entry.interest += interest;
      } else {
        // installment / split — no breakdown available
        entry.installment += amount;
      }
    }
    return [...map.values()].sort((a, b) => a.month.localeCompare(b.month));
  }, [payments]);
}

// ---------------------------------------------------------------------------
// Debt breakdown by creditor
// ---------------------------------------------------------------------------

export interface CreditorDebt {
  creditor: string;
  total: number;
  count: number;
}

export function useDebtByCreditor() {
  const { data: loans } = useLoans();

  return useMemo(() => {
    if (!loans) return [];
    const map = new Map<string, CreditorDebt>();
    for (const l of loans) {
      if (l.status !== "active") continue;
      if (!map.has(l.creditor)) {
        map.set(l.creditor, { creditor: l.creditor, total: 0, count: 0 });
      }
      const entry = map.get(l.creditor)!;
      entry.total += Number(l.original_amount ?? "0");
      entry.count++;
    }
    return [...map.values()].sort((a, b) => b.total - a.total);
  }, [loans]);
}

// ---------------------------------------------------------------------------
// Avalanche optimizer — sort by interest rate descending
// ---------------------------------------------------------------------------

export interface OptimizedLoan {
  id: string;
  creditor: string;
  name: string;
  rate: number;
  balance: string | null;
  monthlyPayment: number;
  rank: number;
}

export function useOptimizer() {
  const { data: loans } = useLoans();
  const { data: payments } = usePlannedPayments({});

  return useMemo(() => {
    if (!loans) return [];
    const activeLoans = loans.filter(
      (l) => l.status === "active" && Number(l.interest_rate) > 0,
    );

    // Calculate average monthly payment per loan
    const loanPaymentMap = new Map<string, number[]>();
    if (payments) {
      for (const p of payments) {
        if (p.status === "cancelled") continue;
        if (!loanPaymentMap.has(p.loan_id)) {
          loanPaymentMap.set(p.loan_id, []);
        }
        loanPaymentMap.get(p.loan_id)!.push(Number(p.amount));
      }
    }

    const result: OptimizedLoan[] = activeLoans
      .map((l) => {
        const pmts = loanPaymentMap.get(l.id) ?? [];
        const avg =
          pmts.length > 0 ? pmts.reduce((a, b) => a + b, 0) / pmts.length : 0;
        return {
          id: l.id,
          creditor: l.creditor,
          name: l.name,
          rate: Number(l.interest_rate),
          balance: l.original_amount,
          monthlyPayment: avg,
          rank: 0,
        };
      })
      .sort((a, b) => b.rate - a.rate);

    // Assign ranks
    result.forEach((l, i) => {
      l.rank = i + 1;
    });

    return result;
  }, [loans, payments]);
}
