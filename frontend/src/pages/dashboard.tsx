/**
 * Dashboard page — main landing screen.
 *
 * Widgets: NextPayments, CurrentPeriod (1–2 salary periods), Totals,
 * Warnings, ForecastChart.
 */

import { useDashboard } from "@/features/dashboard/hooks";
import { NextPaymentsWidget } from "@/features/dashboard/next-payments";
import { CurrentPeriodWidget } from "@/features/dashboard/current-period";
import { TotalsWidget } from "@/features/dashboard/totals-widget";
import { WarningsWidget } from "@/features/dashboard/warnings-widget";
import { ForecastChart } from "@/features/dashboard/forecast-chart";
import { LoadingState } from "@/components/loading-state";

export function DashboardPage() {
  const { data, isLoading, isError } = useDashboard();

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-semibold tracking-tight">Дашборд</h2>

      <LoadingState
        isLoading={isLoading}
        isError={isError}
        errorMessage="Не удалось загрузить данные дашборда"
        skeletonCount={3}
        skeletonHeight="h-32"
      >
        {data && (
          <>
            {/* Metric widgets */}
            <div className="grid gap-4 sm:grid-cols-2">
              <NextPaymentsWidget payments={data.next_payments} />
              <TotalsWidget totals={data.totals} />
            </div>

            {/* Salary periods — one card, two columns inside */}
            <CurrentPeriodWidget
              current={data.current_period}
              next={data.next_period}
            />

            {/* Warnings */}
            <WarningsWidget warnings={data.warnings} />

            {/* Forecast chart */}
            <ForecastChart
              startingBalance={data.current_period.remaining_for_living}
            />
          </>
        )}
      </LoadingState>
    </div>
  );
}
