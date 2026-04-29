/**
 * Stacked bar chart: principal vs interest breakdown by month.
 * Uses loan schedule data from GET /api/loans/{id}/schedule.
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatMoneyCompact, formatMoney, formatDateCompact } from "@/lib/format";

interface ScheduleEntry {
  due_date: string;
  amount: string;
  principal_part: string;
  interest_part: string;
  balance_after: string;
}

interface Props {
  schedule: ScheduleEntry[] | undefined;
  isLoading: boolean;
}

interface ChartPoint {
  label: string;
  principal: number;
  interest: number;
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border bg-card px-3 py-2 shadow-md text-xs">
      <p className="font-medium mb-1">{label}</p>
      {payload.map((entry) => (
        <div key={entry.name} className="flex justify-between gap-4">
          <span style={{ color: entry.color }}>{entry.name}</span>
          <span className="font-medium">{formatMoney(String(entry.value))}</span>
        </div>
      ))}
    </div>
  );
}

export function ScheduleChart({ schedule, isLoading }: Props) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            График погашения
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[220px] w-full rounded-lg" />
        </CardContent>
      </Card>
    );
  }

  if (!schedule?.length) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground text-sm">
          Нет данных графика
        </CardContent>
      </Card>
    );
  }

  const chartData: ChartPoint[] = schedule.map((e) => ({
    label: formatDateCompact(e.due_date),
    principal: Number(e.principal_part),
    interest: Number(e.interest_part),
  }));

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          График погашения
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart
            data={chartData}
            margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              vertical={false}
              stroke="oklch(0.90 0.008 260 / 0.5)"
            />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tickFormatter={(v: number) => formatMoneyCompact(String(v))}
              tick={{ fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              width={70}
            />
            <RechartsTooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: 12 }}
              iconSize={10}
            />
            <Bar
              dataKey="principal"
              name="Тело"
              stackId="a"
              fill="oklch(0.58 0.19 260)"
              radius={[0, 0, 0, 0]}
            />
            <Bar
              dataKey="interest"
              name="Проценты"
              stackId="a"
              fill="oklch(0.80 0.18 80)"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
