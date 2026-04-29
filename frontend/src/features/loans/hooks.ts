/**
 * TanStack Query hooks for loans CRUD.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getLoans,
  getLoan,
  createLoan,
  updateLoan,
  deleteLoan,
  createBalance,
  getLoanSchedule,
} from "@/api/loans";
import type { LoanCreate, LoanUpdate, BalanceCreate } from "@/types/api";
import { toast } from "sonner";

export function useLoans(params?: { status?: string; type?: string }) {
  return useQuery({
    queryKey: ["loans", params],
    queryFn: () => getLoans(params),
  });
}

export function useLoan(id: string) {
  return useQuery({
    queryKey: ["loans", id],
    queryFn: () => getLoan(id),
    enabled: !!id,
  });
}

export function useLoanSchedule(loanId: string) {
  return useQuery({
    queryKey: ["loans", loanId, "schedule"],
    queryFn: () => getLoanSchedule(loanId),
    enabled: !!loanId,
  });
}

export function useCreateLoan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: LoanCreate) => createLoan(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["loans"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Кредит создан");
    },
    onError: () => toast.error("Не удалось создать кредит"),
  });
}

export function useUpdateLoan(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: LoanUpdate) => updateLoan(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["loans"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Кредит обновлён");
    },
    onError: () => toast.error("Не удалось обновить кредит"),
  });
}

export function useDeleteLoan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteLoan(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["loans"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Кредит удалён");
    },
    onError: () => toast.error("Не удалось удалить кредит"),
  });
}

export function useCreateBalance(loanId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: BalanceCreate) => createBalance(loanId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["loans", loanId] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Баланс обновлён");
    },
    onError: () => toast.error("Не удалось обновить баланс"),
  });
}
