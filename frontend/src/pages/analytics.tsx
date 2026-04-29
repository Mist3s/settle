/**
 * Analytics page — payment breakdown, debt breakdown, optimizer.
 */

import { PaymentBreakdownChart } from "@/features/analytics/payment-breakdown-chart";
import { DebtBreakdownChart } from "@/features/analytics/debt-breakdown-chart";
import { Optimizer } from "@/features/analytics/optimizer";

export function AnalyticsPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold tracking-tight">Аналитика</h2>

      <div className="grid gap-6 lg:grid-cols-2">
        <PaymentBreakdownChart />
        <DebtBreakdownChart />
      </div>

      <Optimizer />
    </div>
  );
}
