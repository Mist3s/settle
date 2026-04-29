/**
 * Widget: Next 3 upcoming payments with urgency color coding.
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { formatMoney, formatDateShort } from "@/lib/format";
import type { NextPayment } from "@/types/api";
import { differenceInDays, parseISO } from "date-fns";

interface Props {
  payments: NextPayment[];
}

function urgencyClass(dueDate: string, status: string): string {
  if (status === "overdue") return "border-l-danger";
  const days = differenceInDays(parseISO(dueDate), new Date());
  if (days <= 3) return "border-l-warning";
  return "border-l-primary-400";
}

function urgencyBadge(dueDate: string, status: string) {
  if (status === "overdue") {
    return <Badge variant="destructive">Просрочен</Badge>;
  }
  const days = differenceInDays(parseISO(dueDate), new Date());
  if (days <= 0) {
    return (
      <Badge className="bg-warning/15 text-warning border-warning/30">
        Сегодня
      </Badge>
    );
  }
  if (days <= 3) {
    return (
      <Badge className="bg-warning/15 text-warning border-warning/30">
        {days} дн.
      </Badge>
    );
  }
  return (
    <Badge variant="secondary">
      {days} дн.
    </Badge>
  );
}

export function NextPaymentsWidget({ payments }: Props) {
  if (payments.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Следующие платежи
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Нет предстоящих платежей</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Следующие платежи
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {payments.slice(0, 3).map((p) => (
          <div
            key={`${p.loan_id}-${p.due_date}`}
            className={`flex items-center justify-between rounded-md border-l-4 px-3 py-2 bg-muted/30 ${urgencyClass(p.due_date, p.status)}`}
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium truncate">{p.loan_name}</p>
                {p.can_pay_early && (
                  <Tooltip>
                    <TooltipTrigger>
                      <span className="text-xs text-primary-400 cursor-help">⚡</span>
                    </TooltipTrigger>
                    <TooltipContent>Можно погасить заранее</TooltipContent>
                  </Tooltip>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                {p.creditor} · {formatDateShort(p.due_date)}
              </p>
            </div>
            <div className="flex items-center gap-2 ml-3">
              <span className="text-sm font-semibold whitespace-nowrap">
                {formatMoney(p.amount)}
              </span>
              {urgencyBadge(p.due_date, p.status)}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
