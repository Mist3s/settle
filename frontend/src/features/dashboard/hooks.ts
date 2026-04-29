/**
 * TanStack Query hooks for dashboard and forecast data.
 */

import { useQuery } from "@tanstack/react-query";
import { getDashboard, getForecast } from "@/api/dashboard";
import { format, addDays } from "date-fns";

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
  });
}

export function useForecast(startingBalance: string, days: number = 45) {
  const today = new Date();
  const from = format(today, "yyyy-MM-dd");
  const to = format(addDays(today, days), "yyyy-MM-dd");

  return useQuery({
    queryKey: ["forecast", from, to, startingBalance],
    queryFn: () => getForecast({ from, to, starting_balance: startingBalance }),
    enabled: startingBalance !== "",
  });
}
