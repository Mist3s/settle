/**
 * Calendar header — month navigation: < Month Year >
 */

import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { format } from "date-fns";
import { ru } from "date-fns/locale";

interface CalendarHeaderProps {
  currentMonth: Date;
  onPrev: () => void;
  onNext: () => void;
  onToday: () => void;
}

export function CalendarHeader({
  currentMonth,
  onPrev,
  onNext,
  onToday,
}: CalendarHeaderProps) {
  const label = format(currentMonth, "LLLL yyyy", { locale: ru });

  return (
    <div className="flex items-center justify-between gap-2">
      <div className="flex items-center gap-1">
        <Button variant="outline" size="icon" onClick={onPrev} aria-label="Предыдущий месяц">
          <ChevronLeft className="size-4" />
        </Button>
        <Button variant="outline" size="icon" onClick={onNext} aria-label="Следующий месяц">
          <ChevronRight className="size-4" />
        </Button>
        <h3 className="ml-2 text-lg font-semibold capitalize">{label}</h3>
      </div>
      <Button variant="ghost" size="sm" onClick={onToday}>
        Сегодня
      </Button>
    </div>
  );
}
