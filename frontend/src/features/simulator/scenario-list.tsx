/**
 * Scenario list — sidebar panel showing all scenarios with status badges.
 */

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { LoadingState } from "@/components/loading-state";
import { useScenarios, useDeleteScenario } from "./hooks";
import { ScenarioFormDialog } from "./scenario-form-dialog";
import { formatDate, scenarioStatusLabel } from "@/lib/format";
import type { ScenarioResponse } from "@/types/api";
import { Plus, Trash2, Pencil } from "lucide-react";

const STATUS_VARIANT: Record<string, "default" | "secondary" | "outline"> = {
  draft: "default",
  applied: "secondary",
  archived: "outline",
};

interface ScenarioListProps {
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function ScenarioList({ selectedId, onSelect }: ScenarioListProps) {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(
    undefined,
  );
  const [formOpen, setFormOpen] = useState(false);
  const [editScenario, setEditScenario] = useState<ScenarioResponse | null>(
    null,
  );

  const { data, isLoading, error } = useScenarios(statusFilter);
  const deleteMut = useDeleteScenario();

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-lg font-semibold">Сценарии</h3>
        <Button
          size="sm"
          onClick={() => {
            setEditScenario(null);
            setFormOpen(true);
          }}
        >
          <Plus className="mr-1 h-4 w-4" />
          Новый
        </Button>
      </div>

      {/* Filter */}
      <Select
        value={statusFilter ?? "__all__"}
        onValueChange={(v) =>
          setStatusFilter(!v || v === "__all__" ? undefined : v)
        }
      >
        <SelectTrigger className="w-full">
          <SelectValue placeholder="Все статусы" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="__all__">Все статусы</SelectItem>
          <SelectItem value="draft">Черновик</SelectItem>
          <SelectItem value="applied">Применён</SelectItem>
          <SelectItem value="archived">Архив</SelectItem>
        </SelectContent>
      </Select>

      {/* List */}
      <LoadingState isLoading={isLoading} isError={!!error} isEmpty={!data?.length}>
        <div className="space-y-2">
          {data?.map((s) => (
            <Card
              key={s.id}
              className={`cursor-pointer transition-colors hover:border-primary/50 ${
                selectedId === s.id ? "border-primary bg-primary/5" : ""
              }`}
              onClick={() => onSelect(s.id)}
            >
              <CardContent className="flex items-start justify-between gap-2 p-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{s.name}</p>
                  <p className="text-xs text-muted-foreground">
                    от {formatDate(s.base_date)}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <Badge variant={STATUS_VARIANT[s.status] ?? "outline"}>
                    {scenarioStatusLabel(s.status)}
                  </Badge>
                  {s.status === "draft" && (
                    <>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditScenario(s);
                          setFormOpen(true);
                        }}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-danger hover:text-danger"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteMut.mutate(s.id);
                        }}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </LoadingState>

      {/* Form dialog */}
      <ScenarioFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        scenario={editScenario}
      />
    </div>
  );
}
