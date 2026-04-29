/**
 * TanStack Query hooks for calendar — planned payments in a date range.
 */

import { useQuery } from "@tanstack/react-query";
import { getPlannedPayments } from "@/api/payments";
import { getLoans } from "@/api/loans";

export function useCalendarPayments(from: string, to: string) {
  return useQuery({
    queryKey: ["payments", "planned", { from, to }],
    queryFn: () => getPlannedPayments({ from, to }),
    enabled: !!from && !!to,
  });
}

/**
 * Fetch all loans to resolve loan_id → loan metadata (type, name, creditor).
 * Cached via TanStack Query — shared with other components.
 */
export function useCalendarLoans() {
  return useQuery({
    queryKey: ["loans"],
    queryFn: () => getLoans(),
  });
}
