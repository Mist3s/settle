/**
 * TanStack Query hooks for payments (planned + actual).
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getPlannedPayments,
  updatePlannedPayment,
  registerPayment,
  getActualPayments,
  deleteActualPayment,
} from "@/api/payments";
import type { PlannedPaymentUpdate, ActualPaymentCreate } from "@/types/api";
import { toast } from "sonner";

export function usePlannedPayments(params?: {
  from?: string;
  to?: string;
  loan_id?: string;
  income_id?: string;
}) {
  return useQuery({
    queryKey: ["payments", "planned", params],
    queryFn: () => getPlannedPayments(params),
  });
}

export function useActualPayments(params?: {
  from?: string;
  to?: string;
  loan_id?: string;
}) {
  return useQuery({
    queryKey: ["payments", "actual", params],
    queryFn: () => getActualPayments(params),
  });
}

export function useUpdatePlannedPayment(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: PlannedPaymentUpdate) => updatePlannedPayment(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["payments"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["forecast"] });
      toast.success("Плановый платёж обновлён");
    },
    onError: () => toast.error("Не удалось обновить платёж"),
  });
}

export function useRegisterPayment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ActualPaymentCreate) => registerPayment(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["payments"] });
      qc.invalidateQueries({ queryKey: ["loans"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["forecast"] });
      toast.success("Платёж зарегистрирован");
    },
    onError: () => toast.error("Не удалось зарегистрировать платёж"),
  });
}

export function useDeleteActualPayment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteActualPayment(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["payments"] });
      qc.invalidateQueries({ queryKey: ["loans"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["forecast"] });
      toast.success("Платёж удалён");
    },
    onError: () => toast.error("Не удалось удалить платёж"),
  });
}
