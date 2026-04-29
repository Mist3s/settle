/**
 * Loans page — filterable list of loan cards with "Add" button.
 */

import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { LoadingState } from "@/components/loading-state";
import { useLoans } from "@/features/loans/hooks";
import { LoanCard } from "@/features/loans/loan-card";
import { LoanFilters, type LoanFilterValues } from "@/features/loans/loan-filters";
import { LoanFormDialog } from "@/features/loans/loan-form";

export function LoansPage() {
  const [showCreate, setShowCreate] = useState(false);
  const [filters, setFilters] = useState<LoanFilterValues>({
    search: "",
    type: "all",
    status: "all",
  });

  // Fetch with server-side filters when available
  const queryParams = useMemo(() => {
    const p: { status?: string; type?: string } = {};
    if (filters.status !== "all") p.status = filters.status;
    if (filters.type !== "all") p.type = filters.type;
    return p;
  }, [filters.status, filters.type]);

  const { data: loans, isLoading, isError } = useLoans(queryParams);

  // Client-side text search filter
  const filtered = useMemo(() => {
    if (!loans) return [];
    if (!filters.search.trim()) return loans;
    const q = filters.search.toLowerCase();
    return loans.filter(
      (l) =>
        l.name.toLowerCase().includes(q) ||
        l.creditor.toLowerCase().includes(q) ||
        l.code.toLowerCase().includes(q),
    );
  }, [loans, filters.search]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-2xl font-semibold tracking-tight">Кредиты</h2>
        <Button onClick={() => setShowCreate(true)}>+ Добавить</Button>
      </div>

      <LoanFilters filters={filters} onChange={setFilters} />

      <LoadingState
        isLoading={isLoading}
        isError={isError}
        isEmpty={filtered.length === 0}
        emptyMessage="Нет кредитов, соответствующих фильтрам"
        skeletonCount={4}
        skeletonHeight="h-28"
      >
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {filtered.map((loan) => (
            <LoanCard key={loan.id} loan={loan} />
          ))}
        </div>
      </LoadingState>

      <LoanFormDialog
        open={showCreate}
        onOpenChange={setShowCreate}
      />
    </div>
  );
}
