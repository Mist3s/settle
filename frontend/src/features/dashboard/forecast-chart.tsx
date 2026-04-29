/**
 * Forecast balance-by-day chart using Recharts AreaChart.
 * Gradient fill with tooltip showing date and amount.
 */

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatMoneyCompact, formatDateCompact, formatMoney } from "@/lib/format";
import { useForecast } from "./hooks";
import { CHART } from "@/lib/chart-colors";

interface Props {
  startingBalance: string;
}

interface ChartPoint {
  date: string;
  label: string;
  balance: number;
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: ChartPoint }>;
}) {
  if (!active || !payload?.[0]) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-lg border bg-card px-3 py-2 shadow-md">
      <p className="text-xs text-muted-foreground">{p.date}</p>
      <p className="text-sm font-semibold">{formatMoney(String(p.balance))}</p>
    </div>
  );
}

export function ForecastChart({ startingBalance }: Props) {
  const { data, isLoading, isError } = useForecast(startingBalance);

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Прогноз баланса
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[250px] w-full rounded-lg" />
        </CardContent>
      </Card>
    );
  }

  if (isError || !data?.points?.length) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          {isError
            ? "Не удалось загрузить прогноз"
            : "Недостаточно данных для прогноза"}
        </CardContent>
      </Card>
    );
  }

  const chartData: ChartPoint[] = data.points.map((p) => ({
    date: p.date,
    label: formatDateCompact(p.date),
    balance: Number(p.balance),
  }));

  const minBalance = Math.min(...chartData.map((d) => d.balance));
  const hasDeficit = minBalance < 0;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Прогноз баланса
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <AreaChart
            data={chartData}
            margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id="forecastGradient" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="5%"
                  stopColor={CHART.forecast}
                  stopOpacity={0.3}
                />
                <stop
                  offset="95%"
                  stopColor={CHART.forecast}
                  stopOpacity={0}
                />
              </linearGradient>
              {hasDeficit && (
                <linearGradient id="deficitGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="5%"
                    stopColor={CHART.deficit}
                    stopOpacity={0.3}
                  />
                  <stop
                    offset="95%"
                    stopColor={CHART.deficit}
                    stopOpacity={0}
                  />
                </linearGradient>
              )}
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              vertical={false}
              stroke="#d4d4d8"
            />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tickFormatter={(v: number) => formatMoneyCompact(String(v))}
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={80}
            />
            <RechartsTooltip content={<CustomTooltip />} />
            {hasDeficit && (
              <Area
                type="monotone"
                dataKey="balance"
                stroke={CHART.deficit}
                fill="url(#deficitGradient)"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
                baseValue={0}
              />
            )}
            <Area
              type="monotone"
              dataKey="balance"
              stroke={CHART.forecast}
              fill="url(#forecastGradient)"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
