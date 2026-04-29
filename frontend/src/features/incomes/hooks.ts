/**
 * TanStack Query hooks for incomes CRUD + receive.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getIncomes,
  createIncome,
  updateIncome,
  receiveIncome,
  deleteIncome,
} from "@/api/incomes";
import type { IncomeCreate, IncomeUpdate } from "@/types/api";
import { toast } from "sonner";

export function useIncomes(params?: { from?: string; to?: string }) {
  return useQuery({
    queryKey: ["incomes", params],
    queryFn: () => getIncomes(params),
  });
}

export function useCreateIncome() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: IncomeCreate) => createIncome(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["incomes"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["forecast"] });
      toast.success("Поступление создано");
    },
    onError: () => toast.error("Не удалось создать поступление"),
  });
}

export function useUpdateIncome(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: IncomeUpdate) => updateIncome(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["incomes"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["forecast"] });
      toast.success("Поступление обновлено");
    },
    onError: () => toast.error("Не удалось обновить поступление"),
  });
}

export function useReceiveIncome() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => receiveIncome(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["incomes"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["forecast"] });
      toast.success("Поступление отмечено как полученное");
    },
    onError: () => toast.error("Не удалось обновить статус"),
  });
}

export function useDeleteIncome() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteIncome(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["incomes"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["forecast"] });
      toast.success("Поступление удалено");
    },
    onError: () => toast.error("Не удалось удалить поступление"),
  });
}
