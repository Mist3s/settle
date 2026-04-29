/**
 * Prepayment strategy toggle: reduce_payment ↔ shorten_term.
 * Inline on loan detail card.
 */

import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useUpdateLoan } from "@/features/loans/hooks";
import type { LoanResponse, PrepaymentStrategy } from "@/types/api";

interface Props {
  loan: LoanResponse;
}

const STRATEGY_CONFIG: Record<
  PrepaymentStrategy,
  { label: string; icon: string; tooltip: string; next: PrepaymentStrategy }
> = {
  reduce_payment: {
    label: "Уменьшить платёж",
    icon: "↓",
    tooltip: "Текущая стратегия: уменьшение платежа. Нажмите для переключения.",
    next: "shorten_term",
  },
  shorten_term: {
    label: "Сократить срок",
    icon: "⏩",
    tooltip: "Текущая стратегия: сокращение срока. Нажмите для переключения.",
    next: "reduce_payment",
  },
};

export function StrategyToggle({ loan }: Props) {
  const mutation = useUpdateLoan(loan.id);
  const cfg = STRATEGY_CONFIG[loan.prepayment_strategy];

  const toggle = () => {
    mutation.mutate({ prepayment_strategy: cfg.next });
  };

  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Button
            variant="outline"
            size="sm"
            onClick={toggle}
            disabled={mutation.isPending}
            className="gap-1"
          />
        }
      >
        <span>{cfg.icon}</span>
        <span className="hidden sm:inline">{cfg.label}</span>
      </TooltipTrigger>
      <TooltipContent>{cfg.tooltip}</TooltipContent>
    </Tooltip>
  );
}
