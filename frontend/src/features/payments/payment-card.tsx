/**
 * Payment card — single actual payment entry.
 */

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  formatMoney,
  formatDate,
  actualPaymentTypeLabel,
} from "@/lib/format";
import type { ActualPaymentResponse, LoanResponse } from "@/types/api";

const TYPE_VARIANT: Record<
  string,
  "default" | "secondary" | "outline" | "destructive"
> = {
  regular: "default",
  early_partial: "secondary",
  early_full: "secondary",
  overpayment: "outline",
  underpayment: "destructive",
  missed: "destructive",
};

interface PaymentCardProps {
  payment: ActualPaymentResponse;
  loan?: LoanResponse;
  onDelete: (id: string) => void;
}

export function PaymentCard({ payment, loan, onDelete }: PaymentCardProps) {
  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardContent className="flex flex-col gap-2 p-4">
        {/* Header: loan name + type badge */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <p className="font-medium text-sm truncate">
              {loan?.name ?? "—"}
            </p>
            <p className="text-xs text-muted-foreground">
              {loan?.creditor ?? "—"}
            </p>
          </div>
          <Badge variant={TYPE_VARIANT[payment.payment_type] ?? "outline"}>
            {actualPaymentTypeLabel(payment.payment_type)}
          </Badge>
        </div>

        {/* Amount + date */}
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-lg font-semibold tabular-nums">
            {formatMoney(payment.amount)}
          </span>
          <span className="text-sm text-muted-foreground">
            {formatDate(payment.payment_date)}
          </span>
        </div>

        {/* Parts breakdown */}
        {(payment.principal_part || payment.interest_part) && (
          <div className="flex gap-4 text-xs text-muted-foreground">
            {payment.principal_part && (
              <span>Тело: {formatMoney(payment.principal_part)}</span>
            )}
            {payment.interest_part && (
              <span>Проценты: {formatMoney(payment.interest_part)}</span>
            )}
          </div>
        )}

        {/* Notes */}
        {payment.notes && (
          <p className="text-xs text-muted-foreground line-clamp-2">
            {payment.notes}
          </p>
        )}

        {/* Actions */}
        <div className="flex justify-end pt-1">
          <Button
            size="sm"
            variant="ghost"
            className="text-danger hover:text-danger"
            onClick={() => onDelete(payment.id)}
          >
            Удалить
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
