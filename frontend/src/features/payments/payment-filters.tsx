/**
 * Payment filters — loan select + date range + type select.
 */

import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useLoans } from "@/features/loans/hooks";

export interface PaymentFilterValues {
  loan_id: string;
  type: string;
  from: string;
  to: string;
}

interface PaymentFiltersProps {
  filters: PaymentFilterValues;
  onChange: (filters: PaymentFilterValues) => void;
}

export function PaymentFilters({ filters, onChange }: PaymentFiltersProps) {
  const { data: loans } = useLoans();

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:flex-wrap">
      {/* Loan select */}
      <Select
        value={filters.loan_id}
        onValueChange={(v) => v && onChange({ ...filters, loan_id: v })}
      >
        <SelectTrigger className="w-52">
          <SelectValue placeholder="Кредит" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Все кредиты</SelectItem>
          {(loans ?? []).map((l) => (
            <SelectItem key={l.id} value={l.id}>
              {l.name} ({l.creditor})
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Type select */}
      <Select
        value={filters.type}
        onValueChange={(v) => v && onChange({ ...filters, type: v })}
      >
        <SelectTrigger className="w-44">
          <SelectValue placeholder="Тип" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Все типы</SelectItem>
          <SelectItem value="regular">Регулярный</SelectItem>
          <SelectItem value="early_partial">Досрочный частичный</SelectItem>
          <SelectItem value="early_full">Досрочный полный</SelectItem>
          <SelectItem value="overpayment">Переплата</SelectItem>
          <SelectItem value="underpayment">Недоплата</SelectItem>
          <SelectItem value="missed">Пропущен</SelectItem>
        </SelectContent>
      </Select>

      {/* Date range */}
      <div className="flex items-center gap-2">
        <Input
          type="date"
          value={filters.from}
          onChange={(e) => onChange({ ...filters, from: e.target.value })}
          className="w-36"
          aria-label="Дата от"
        />
        <span className="text-muted-foreground text-sm">—</span>
        <Input
          type="date"
          value={filters.to}
          onChange={(e) => onChange({ ...filters, to: e.target.value })}
          className="w-36"
          aria-label="Дата до"
        />
      </div>
    </div>
  );
}
