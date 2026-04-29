/**
 * Comparison view — side-by-side as-is vs to-be forecast charts + diff summary.
 * Responsive: side-by-side on desktop, tabs on mobile.
 */

import { useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useMediaQuery } from "@/hooks/use-media-query";
import {
  formatMoney,
  formatMoneyCompact,
  formatDateCompact,
  formatDays,
} from "@/lib/format";
import type { ScenarioForecastResponse, DailyBalance } from "@/types/api";
import { TrendingDown, TrendingUp, Calendar } from "lucide-react";
import { CHART } from "@/lib/chart-colors";

interface ComparisonViewProps {
  data: ScenarioForecastResponse | undefined;
  isLoading: boolean;
}

function toChartData(points: DailyBalance[]) {
  return points.map((p) => ({
    date: p.date,
    balance: Number(p.balance),
  }));
}

function ForecastChart({
  title,
  points,
  color,
}: {
  title: string;
  points: DailyBalance[];
  color: string;
}) {
  const chartData = toChartData(points);
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[240px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient
                  id={`grad-${color}`}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="date"
                tickFormatter={formatDateCompact}
                tick={{ fontSize: 11 }}
                className="fill-muted-foreground"
              />
              <YAxis
                tickFormatter={(v: number) =>
                  formatMoneyCompact(String(v))
                }
                tick={{ fontSize: 11 }}
                width={80}
                className="fill-muted-foreground"
              />
              <Tooltip
                labelFormatter={(label) => formatDateCompact(String(label))}
                formatter={(value) => [
                  formatMoney(String(value)),
                  "Баланс",
                ]}
                contentStyle={{
                  borderRadius: "8px",
                  border: "1px solid var(--border)",
                  background: "var(--popover)",
                  color: "var(--popover-foreground)",
                }}
              />
              <Area
                type="monotone"
                dataKey="balance"
                stroke={color}
                fill={`url(#grad-${color})`}
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

function DiffSummary({ data }: { data: ScenarioForecastResponse }) {
  const diff = data.diff;
  const totalPaid = Number(diff.total_paid_difference);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">Разница</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Total paid difference */}
        <div className="flex items-center gap-3">
          {totalPaid <= 0 ? (
            <TrendingDown className="h-5 w-5 text-success" />
          ) : (
            <TrendingUp className="h-5 w-5 text-danger" />
          )}
          <div>
            <p className="text-xs text-muted-foreground">Общие выплаты</p>
            <p
              className={`text-lg font-semibold ${
                totalPaid <= 0 ? "text-success" : "text-danger"
              }`}
            >
              {totalPaid <= 0 ? "−" : "+"}
              {formatMoney(String(Math.abs(totalPaid)))}
            </p>
          </div>
        </div>

        {/* Interest saved */}
        <div className="flex items-center gap-3">
          <TrendingDown className="h-5 w-5 text-success" />
          <div>
            <p className="text-xs text-muted-foreground">Экономия процентов</p>
            <p className="text-lg font-semibold text-success">
              {formatMoney(diff.total_interest_saved)}
            </p>
          </div>
        </div>

        {/* Zero balance date */}
        {diff.first_zero_balance_date_change && (
          <div className="flex items-center gap-3">
            <Calendar className="h-5 w-5 text-primary" />
            <div>
              <p className="text-xs text-muted-foreground">
                Дата полного погашения
              </p>
              <Badge variant="outline" className="mt-0.5">
                {formatDays(diff.first_zero_balance_date_change)}
              </Badge>
            </div>
          </div>
        )}

        {/* Payment counts */}
        <div className="mt-2 grid grid-cols-2 gap-3 text-center">
          <div className="rounded-md border p-2">
            <p className="text-xs text-muted-foreground">Текущий план</p>
            <p className="text-lg font-semibold">
              {data.current.payments.length}
            </p>
            <p className="text-xs text-muted-foreground">платежей</p>
          </div>
          <div className="rounded-md border p-2">
            <p className="text-xs text-muted-foreground">По сценарию</p>
            <p className="text-lg font-semibold">
              {data.scenario.payments.length}
            </p>
            <p className="text-xs text-muted-foreground">платежей</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function ComparisonView({ data, isLoading }: ComparisonViewProps) {
  const isDesktop = useMediaQuery("(min-width: 1024px)");
  const [mobileTab, setMobileTab] = useState("current");

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-[300px]" />
        <Skeleton className="h-[300px]" />
      </div>
    );
  }

  if (!data) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          Выберите сценарий и настройте параметры для просмотра прогноза
        </CardContent>
      </Card>
    );
  }

  if (isDesktop) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <ForecastChart
            title="Текущий план"
            points={data.current.balance_by_day}
            color={CHART.current}
          />
          <ForecastChart
            title="По сценарию"
            points={data.scenario.balance_by_day}
            color={CHART.scenario}
          />
        </div>
        <DiffSummary data={data} />
      </div>
    );
  }

  // Mobile: tabs
  return (
    <div className="space-y-4">
      <Tabs value={mobileTab} onValueChange={setMobileTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="current">Текущий</TabsTrigger>
          <TabsTrigger value="scenario">Сценарий</TabsTrigger>
          <TabsTrigger value="diff">Разница</TabsTrigger>
        </TabsList>
        <TabsContent value="current">
          <ForecastChart
            title="Текущий план"
            points={data.current.balance_by_day}
            color={CHART.current}
          />
        </TabsContent>
        <TabsContent value="scenario">
          <ForecastChart
            title="По сценарию"
            points={data.scenario.balance_by_day}
            color={CHART.scenario}
          />
        </TabsContent>
        <TabsContent value="diff">
          <DiffSummary data={data} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
