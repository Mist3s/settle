/**
 * Loan list filters: type (multi), status, text search.
 */

import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { loanTypeLabel, loanStatusLabel } from "@/lib/format";
import type { LoanType, LoanStatus } from "@/types/api";

const LOAN_TYPES: LoanType[] = [
  "credit",
  "installment",
  "split",
  "utilities",
  "other_debt",
];

const LOAN_STATUSES: LoanStatus[] = ["active", "paid_off", "defaulted", "cancelled"];

interface Filters {
  search: string;
  type: string;
  status: string;
}

interface Props {
  filters: Filters;
  onChange: (filters: Filters) => void;
}

export function LoanFilters({ filters, onChange }: Props) {
  return (
    <div className="flex flex-col sm:flex-row gap-3">
      <Input
        placeholder="Поиск по названию…"
        value={filters.search}
        onChange={(e) => onChange({ ...filters, search: e.target.value })}
        className="sm:max-w-[240px]"
      />
      <Select
        value={filters.type}
        onValueChange={(v) => onChange({ ...filters, type: v ?? "all" })}
      >
        <SelectTrigger className="sm:w-[180px]">
          <SelectValue placeholder="Все типы">
            {(v: string) => v === "all" ? "Все типы" : loanTypeLabel(v)}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Все типы</SelectItem>
          {LOAN_TYPES.map((t) => (
            <SelectItem key={t} value={t}>
              {loanTypeLabel(t)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select
        value={filters.status}
        onValueChange={(v) => onChange({ ...filters, status: v ?? "all" })}
      >
        <SelectTrigger className="sm:w-[180px]">
          <SelectValue placeholder="Все статусы">
            {(v: string) => v === "all" ? "Все статусы" : loanStatusLabel(v)}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Все статусы</SelectItem>
          {LOAN_STATUSES.map((s) => (
            <SelectItem key={s} value={s}>
              {loanStatusLabel(s)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

export type { Filters as LoanFilterValues };
