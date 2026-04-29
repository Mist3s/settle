/**
 * Action card — displays a single scenario action with edit/delete controls.
 */

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  formatDate,
  formatMoney,
  scenarioActionTypeLabel,
} from "@/lib/format";
import type { ScenarioActionResponse, LoanResponse } from "@/types/api";
import { Pencil, Trash2 } from "lucide-react";

interface ActionCardProps {
  action: ScenarioActionResponse;
  loans: LoanResponse[];
  onEdit: (action: ScenarioActionResponse) => void;
  onDelete: (actionId: string) => void;
  disabled?: boolean;
}

function loanName(loans: LoanResponse[], id: string | null): string {
  if (!id) return "";
  const loan = loans.find((l) => l.id === id);
  return loan ? `${loan.creditor} — ${loan.name}` : id.slice(0, 8);
}

function paramsDescription(
  action: ScenarioActionResponse,
  loans: LoanResponse[],
): string {
  const p = action.params ?? {};
  switch (action.action_type) {
    case "close_early_full":
      return loanName(loans, action.loan_id);
    case "prepayment_partial":
      return `${loanName(loans, action.loan_id)}, ${formatMoney(p.amount as string | undefined)}`;
    case "reduce_payment":
      return `Новая сумма: ${formatMoney(p.new_amount as string | undefined)}`;
    case "skip":
      return "Пропуск платежа";
    case "add_income":
      return `${p.name ?? "Доход"}: ${formatMoney(p.amount as string | undefined)}`;
    case "change_payment_date":
      return `Новая дата: ${formatDate(p.new_date as string | undefined)}`;
    default:
      return "";
  }
}

export function ActionCard({
  action,
  loans,
  onEdit,
  onDelete,
  disabled,
}: ActionCardProps) {
  return (
    <Card className="transition-colors hover:border-primary/30">
      <CardContent className="flex items-start justify-between gap-2 p-3">
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="shrink-0">
              {scenarioActionTypeLabel(action.action_type)}
            </Badge>
            <span className="truncate text-xs text-muted-foreground">
              {formatDate(action.effective_date)}
            </span>
          </div>
          <p className="truncate text-sm">
            {paramsDescription(action, loans)}
          </p>
        </div>
        {!disabled && (
          <div className="flex shrink-0 items-center gap-0.5">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => onEdit(action)}
            >
              <Pencil className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-danger hover:text-danger"
              onClick={() => onDelete(action.id)}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
