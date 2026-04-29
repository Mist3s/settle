/**
 * Simulator page — two-panel layout:
 * Left: scenario list + actions editor.
 * Right: comparison view (as-is vs to-be).
 * Mobile: tabs between panels.
 */

import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LoadingState } from "@/components/loading-state";
import { useMediaQuery } from "@/hooks/use-media-query";
import { ScenarioList } from "@/features/simulator/scenario-list";
import { ActionCard } from "@/features/simulator/action-card";
import { ActionFormDialog } from "@/features/simulator/action-form-dialog";
import { ComparisonView } from "@/features/simulator/comparison-view";
import {
  useScenario,
  useScenarioActions,
  useScenarioForecast,
  useDeleteAction,
  useApplyScenario,
  useArchiveScenario,
} from "@/features/simulator/hooks";
import { useLoans } from "@/features/loans/hooks";
import type { ScenarioActionResponse } from "@/types/api";
import { format, addMonths } from "date-fns";
import { Play, Archive, Plus } from "lucide-react";

export function SimulatorPage() {
  const isDesktop = useMediaQuery("(min-width: 1024px)");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [mobileTab, setMobileTab] = useState("scenarios");
  const [actionFormOpen, setActionFormOpen] = useState(false);
  const [editAction, setEditAction] = useState<ScenarioActionResponse | null>(
    null,
  );
  const [startingBalance, setStartingBalance] = useState("0");

  const { data: scenario } = useScenario(selectedId);
  const { data: actions, isLoading: actionsLoading } =
    useScenarioActions(selectedId);
  const { data: loans } = useLoans();
  const deleteActionMut = useDeleteAction(selectedId ?? "");
  const applyMut = useApplyScenario();
  const archiveMut = useArchiveScenario();

  // Forecast date range: from today to +3 months
  const forecastParams = useMemo(() => {
    const from = format(new Date(), "yyyy-MM-dd");
    const to = format(addMonths(new Date(), 3), "yyyy-MM-dd");
    return { from, to };
  }, []);

  const {
    data: forecastData,
    isLoading: forecastLoading,
  } = useScenarioForecast(
    selectedId,
    forecastParams.from,
    forecastParams.to,
    startingBalance || undefined,
  );

  const isDraft = scenario?.status === "draft";

  // --- Left panel content ---
  const leftPanel = (
    <div className="space-y-4">
      <ScenarioList selectedId={selectedId} onSelect={setSelectedId} />

      {selectedId && scenario && (
        <>
          <Separator />

          {/* Starting balance */}
          <div className="space-y-2">
            <Label htmlFor="starting-balance" className="text-sm">
              Начальный баланс (₽)
            </Label>
            <Input
              id="starting-balance"
              type="number"
              step="0.01"
              value={startingBalance}
              onChange={(e) => setStartingBalance(e.target.value)}
              placeholder="0.00"
            />
          </div>

          <Separator />

          {/* Actions */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold">Действия</h4>
              {isDraft && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setEditAction(null);
                    setActionFormOpen(true);
                  }}
                >
                  <Plus className="mr-1 h-3.5 w-3.5" />
                  Добавить
                </Button>
              )}
            </div>

            <LoadingState
              isLoading={actionsLoading}
              isError={false}
              isEmpty={!actions?.length}
            >
              <div className="space-y-2">
                {actions?.map((a) => (
                  <ActionCard
                    key={a.id}
                    action={a}
                    loans={loans ?? []}
                    disabled={!isDraft}
                    onEdit={(act) => {
                      setEditAction(act);
                      setActionFormOpen(true);
                    }}
                    onDelete={(id) => deleteActionMut.mutate(id)}
                  />
                ))}
              </div>
            </LoadingState>
          </div>

          {/* Apply / Archive buttons */}
          {isDraft && (
            <div className="flex gap-2">
              <Button
                className="flex-1"
                onClick={() => applyMut.mutate(selectedId!)}
                disabled={
                  applyMut.isPending || !actions?.length
                }
              >
                <Play className="mr-1 h-4 w-4" />
                {applyMut.isPending ? "Применение…" : "Применить"}
              </Button>
              <Button
                variant="outline"
                onClick={() => archiveMut.mutate(selectedId!)}
                disabled={archiveMut.isPending}
              >
                <Archive className="mr-1 h-4 w-4" />
                Архив
              </Button>
            </div>
          )}
        </>
      )}

      {/* Action form dialog */}
      {selectedId && (
        <ActionFormDialog
          open={actionFormOpen}
          onOpenChange={setActionFormOpen}
          scenarioId={selectedId}
          editAction={editAction}
        />
      )}
    </div>
  );

  // --- Right panel content ---
  const rightPanel = (
    <ComparisonView data={forecastData} isLoading={forecastLoading} />
  );

  // --- Layout ---
  if (isDesktop) {
    return (
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold tracking-tight">Симулятор</h2>
        <div className="grid grid-cols-[360px_1fr] gap-6">
          <div className="max-h-[calc(100vh-120px)] overflow-y-auto pr-2">
            {leftPanel}
          </div>
          <div>{rightPanel}</div>
        </div>
      </div>
    );
  }

  // Mobile: tabs
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-semibold tracking-tight">Симулятор</h2>
      <Tabs value={mobileTab} onValueChange={setMobileTab}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="scenarios">Сценарии</TabsTrigger>
          <TabsTrigger value="comparison">Сравнение</TabsTrigger>
        </TabsList>
        <TabsContent value="scenarios">{leftPanel}</TabsContent>
        <TabsContent value="comparison">{rightPanel}</TabsContent>
      </Tabs>
    </div>
  );
}
