/**
 * Incomes page — filterable list of income cards with CRUD.
 */

import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { LoadingState } from "@/components/loading-state";
import { useIncomes, useReceiveIncome, useDeleteIncome } from "@/features/incomes/hooks";
import { IncomeCard } from "@/features/incomes/income-card";
import { IncomeFilters, type IncomeFilterValues } from "@/features/incomes/income-filters";
import { IncomeFormDialog } from "@/features/incomes/income-form";
import type { IncomeResponse } from "@/types/api";

export function IncomesPage() {
  const [showForm, setShowForm] = useState(false);
  const [editIncome, setEditIncome] = useState<IncomeResponse | undefined>();
  const [filters, setFilters] = useState<IncomeFilterValues>({
    search: "",
    status: "all",
  });

  const { data: incomes, isLoading, isError } = useIncomes();
  const receiveMutation = useReceiveIncome();
  const deleteMutation = useDeleteIncome();

  // Client-side filtering
  const filtered = useMemo(() => {
    if (!incomes) return [];
    let list = incomes;
    if (filters.status !== "all") {
      list = list.filter((i) => i.status === filters.status);
    }
    if (filters.search.trim()) {
      const q = filters.search.toLowerCase();
      list = list.filter(
        (i) =>
          i.code.toLowerCase().includes(q) ||
          (i.name?.toLowerCase().includes(q) ?? false),
      );
    }
    return list;
  }, [incomes, filters]);

  const handleEdit = (income: IncomeResponse) => {
    setEditIncome(income);
    setShowForm(true);
  };

  const handleCreate = () => {
    setEditIncome(undefined);
    setShowForm(true);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-2xl font-semibold tracking-tight">Поступления</h2>
        <Button onClick={handleCreate}>+ Добавить</Button>
      </div>

      <IncomeFilters filters={filters} onChange={setFilters} />

      <LoadingState
        isLoading={isLoading}
        isError={isError}
        isEmpty={filtered.length === 0}
        emptyMessage="Нет поступлений, соответствующих фильтрам"
        skeletonCount={4}
        skeletonHeight="h-28"
      >
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {filtered.map((income) => (
            <IncomeCard
              key={income.id}
              income={income}
              onEdit={handleEdit}
              onReceive={(id) => receiveMutation.mutate(id)}
              onDelete={(id) => deleteMutation.mutate(id)}
            />
          ))}
        </div>
      </LoadingState>

      <IncomeFormDialog
        open={showForm}
        onOpenChange={setShowForm}
        income={editIncome}
      />
    </div>
  );
}
