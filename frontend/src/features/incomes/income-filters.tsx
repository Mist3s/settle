/**
 * Income filters — status select + text search.
 */

import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export interface IncomeFilterValues {
  search: string;
  status: string;
}

interface IncomeFiltersProps {
  filters: IncomeFilterValues;
  onChange: (filters: IncomeFilterValues) => void;
}

export function IncomeFilters({ filters, onChange }: IncomeFiltersProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <Input
        placeholder="Поиск по коду или названию…"
        value={filters.search}
        onChange={(e) => onChange({ ...filters, search: e.target.value })}
        className="sm:max-w-xs"
      />
      <Select
        value={filters.status}
        onValueChange={(v) => v && onChange({ ...filters, status: v })}
      >
        <SelectTrigger className="w-44">
          <SelectValue placeholder="Статус">
            {(v: string) => {
              const labels: Record<string, string> = {
                all: "Все статусы", expected: "Ожидается",
                received: "Получено", cancelled: "Отменено",
              };
              return labels[v] ?? v;
            }}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Все статусы</SelectItem>
          <SelectItem value="expected">Ожидается</SelectItem>
          <SelectItem value="received">Получено</SelectItem>
          <SelectItem value="cancelled">Отменено</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}
