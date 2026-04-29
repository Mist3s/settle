/**
 * Loan card for list view — shows key info at a glance.
 * Clickable, navigates to detail page.
 */

import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatMoney, formatPercent, loanTypeLabel, loanStatusLabel } from "@/lib/format";
import type { LoanResponse } from "@/types/api";

interface Props {
  loan: LoanResponse;
}

const TYPE_COLORS: Record<string, string> = {
  credit: "bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300",
  installment: "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300",
  split: "bg-violet-100 text-violet-700 dark:bg-violet-900 dark:text-violet-300",
  utilities: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
  other_debt: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
};

const STATUS_COLORS: Record<string, string> = {
  active: "bg-success/15 text-success border-success/30",
  paid_off: "bg-muted text-muted-foreground",
  defaulted: "bg-danger/15 text-danger border-danger/30",
  cancelled: "bg-muted text-muted-foreground",
};

export function LoanCard({ loan }: Props) {
  const navigate = useNavigate();

  return (
    <Card
      className="cursor-pointer transition-all hover:shadow-md hover:border-primary/30 active:scale-[0.99]"
      onClick={() => navigate(`/loans/${loan.id}`)}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-sm font-semibold truncate">{loan.name}</h3>
              <Badge
                variant="outline"
                className={`text-[10px] px-1.5 py-0 ${TYPE_COLORS[loan.loan_type] ?? ""}`}
              >
                {loanTypeLabel(loan.loan_type)}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              {loan.creditor}
              {loan.contract_number && ` · ${loan.contract_number}`}
            </p>
          </div>
          <Badge
            variant="outline"
            className={`text-[10px] shrink-0 ${STATUS_COLORS[loan.status] ?? ""}`}
          >
            {loanStatusLabel(loan.status)}
          </Badge>
        </div>

        <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          {loan.original_amount && (
            <div>
              <span className="text-muted-foreground">Сумма</span>
              <p className="font-medium">{formatMoney(loan.original_amount)}</p>
            </div>
          )}
          {loan.current_balance != null && (
            <div>
              <span className="text-muted-foreground">Остаток</span>
              <p className="font-semibold text-primary">{formatMoney(loan.current_balance)}</p>
            </div>
          )}
          <div>
            <span className="text-muted-foreground">Ставка</span>
            <p className="font-medium">{formatPercent(loan.interest_rate)}</p>
          </div>
          {loan.months_remaining != null && (
            <div>
              <span className="text-muted-foreground">Осталось</span>
              <p className="font-medium">{loan.months_remaining} мес.</p>
            </div>
          )}
          {loan.priority != null && (
            <div>
              <span className="text-muted-foreground">Приоритет</span>
              <p className="font-medium">#{loan.priority}</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
