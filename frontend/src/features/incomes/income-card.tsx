/**
 * Income card — displays a single income entry with status badge and actions.
 */

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { formatMoney, formatDate, incomeStatusLabel } from "@/lib/format";
import type { IncomeResponse } from "@/types/api";

const STATUS_VARIANT: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  expected: "outline",
  received: "default",
  cancelled: "secondary",
};

interface IncomeCardProps {
  income: IncomeResponse;
  onEdit: (income: IncomeResponse) => void;
  onReceive: (id: string) => void;
  onDelete: (id: string) => void;
}

export function IncomeCard({ income, onEdit, onReceive, onDelete }: IncomeCardProps) {
  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardContent className="flex flex-col gap-3 p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <p className="font-medium truncate">{income.name ?? income.code}</p>
            <p className="text-xs text-muted-foreground">{income.code}</p>
          </div>
          <Badge variant={STATUS_VARIANT[income.status] ?? "outline"}>
            {incomeStatusLabel(income.status)}
          </Badge>
        </div>

        {/* Amount + date */}
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-lg font-semibold tabular-nums">
            {formatMoney(income.amount)}
          </span>
          <span className="text-sm text-muted-foreground">
            {formatDate(income.expected_date)}
          </span>
        </div>

        {/* Notes */}
        {income.notes && (
          <p className="text-xs text-muted-foreground line-clamp-2">
            {income.notes}
          </p>
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-1">
          {income.status === "expected" && (
            <Button
              size="sm"
              variant="default"
              onClick={() => onReceive(income.id)}
            >
              ✓ Получено
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            onClick={() => onEdit(income)}
          >
            Изменить
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="text-danger hover:text-danger"
            onClick={() => onDelete(income.id)}
          >
            Удалить
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
