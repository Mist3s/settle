/**
 * TanStack Query hooks for the Simulator feature.
 * Covers scenarios CRUD, actions CRUD, forecast, apply, archive.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getScenarios,
  getScenario,
  createScenario,
  updateScenario,
  deleteScenario,
  getActions,
  addAction,
  updateAction,
  deleteAction,
  getScenarioForecast,
  applyScenario,
  archiveScenario,
} from "@/api/scenarios";
import type {
  ScenarioCreate,
  ScenarioUpdate,
  ScenarioActionCreate,
  ScenarioActionUpdate,
} from "@/types/api";
import { toast } from "sonner";

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const scenarioKeys = {
  all: ["scenarios"] as const,
  list: (status?: string) => [...scenarioKeys.all, "list", status] as const,
  detail: (id: string) => [...scenarioKeys.all, "detail", id] as const,
  actions: (id: string) => [...scenarioKeys.all, "actions", id] as const,
  forecast: (id: string, from: string, to: string) =>
    [...scenarioKeys.all, "forecast", id, from, to] as const,
};

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

export function useScenarios(status?: string) {
  return useQuery({
    queryKey: scenarioKeys.list(status),
    queryFn: () => getScenarios(status ? { status } : undefined),
  });
}

export function useScenario(id: string | null) {
  return useQuery({
    queryKey: scenarioKeys.detail(id ?? ""),
    queryFn: () => getScenario(id!),
    enabled: !!id,
  });
}

export function useScenarioActions(scenarioId: string | null) {
  return useQuery({
    queryKey: scenarioKeys.actions(scenarioId ?? ""),
    queryFn: () => getActions(scenarioId!),
    enabled: !!scenarioId,
  });
}

export function useScenarioForecast(
  scenarioId: string | null,
  from: string,
  to: string,
  startingBalance?: string,
) {
  return useQuery({
    queryKey: scenarioKeys.forecast(scenarioId ?? "", from, to),
    queryFn: () =>
      getScenarioForecast(scenarioId!, {
        from,
        to,
        starting_balance: startingBalance,
      }),
    enabled: !!scenarioId && !!from && !!to,
  });
}

// ---------------------------------------------------------------------------
// Scenario mutations
// ---------------------------------------------------------------------------

export function useCreateScenario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ScenarioCreate) => createScenario(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: scenarioKeys.all });
      toast.success("Сценарий создан");
    },
    onError: () => toast.error("Ошибка создания сценария"),
  });
}

export function useUpdateScenario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ScenarioUpdate }) =>
      updateScenario(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: scenarioKeys.all });
      toast.success("Сценарий обновлён");
    },
    onError: () => toast.error("Ошибка обновления сценария"),
  });
}

export function useDeleteScenario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteScenario(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: scenarioKeys.all });
      toast.success("Сценарий удалён");
    },
    onError: () => toast.error("Ошибка удаления сценария"),
  });
}

// ---------------------------------------------------------------------------
// Action mutations
// ---------------------------------------------------------------------------

export function useAddAction(scenarioId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ScenarioActionCreate) => addAction(scenarioId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: scenarioKeys.actions(scenarioId) });
      qc.invalidateQueries({ queryKey: scenarioKeys.all });
      toast.success("Действие добавлено");
    },
    onError: () => toast.error("Ошибка добавления действия"),
  });
}

export function useUpdateAction(scenarioId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      actionId,
      data,
    }: {
      actionId: string;
      data: ScenarioActionUpdate;
    }) => updateAction(scenarioId, actionId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: scenarioKeys.actions(scenarioId) });
      qc.invalidateQueries({ queryKey: scenarioKeys.all });
      toast.success("Действие обновлено");
    },
    onError: () => toast.error("Ошибка обновления действия"),
  });
}

export function useDeleteAction(scenarioId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (actionId: string) => deleteAction(scenarioId, actionId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: scenarioKeys.actions(scenarioId) });
      qc.invalidateQueries({ queryKey: scenarioKeys.all });
      toast.success("Действие удалено");
    },
    onError: () => toast.error("Ошибка удаления действия"),
  });
}

// ---------------------------------------------------------------------------
// Apply / Archive
// ---------------------------------------------------------------------------

export function useApplyScenario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => applyScenario(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: scenarioKeys.all });
      qc.invalidateQueries({ queryKey: ["loans"] });
      qc.invalidateQueries({ queryKey: ["payments"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Сценарий применён");
    },
    onError: () => toast.error("Ошибка применения сценария"),
  });
}

export function useArchiveScenario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => archiveScenario(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: scenarioKeys.all });
      toast.success("Сценарий архивирован");
    },
    onError: () => toast.error("Ошибка архивации сценария"),
  });
}
