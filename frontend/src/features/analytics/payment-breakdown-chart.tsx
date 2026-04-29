/**
 * Payment breakdown chart — stacked bar by month.
 * Shows principal vs interest vs installment portions.
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { usePaymentBreakdown } from "./hooks";
import { formatMoneyCompact } from "@/lib/format";
import { CHART } from "@/lib/chart-colors";

export function PaymentBreakdownChart() {
  const data = usePaymentBreakdown();

  if (!data.length) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          Нет данных для отображения
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Структура выплат по месяцам</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 11 }}
                className="fill-muted-foreground"
              />
              <YAxis
                tickFormatter={(v: number) => formatMoneyCompact(String(v))}
                tick={{ fontSize: 11 }}
                width={80}
                className="fill-muted-foreground"
              />
              <Tooltip
                formatter={(value, name) => [
                  formatMoneyCompact(String(value)),
                  name === "principal"
                    ? "Тело"
                    : name === "interest"
                      ? "Проценты"
                      : "Рассрочки",
                ]}
                contentStyle={{
                  borderRadius: "8px",
                  border: "1px solid var(--border)",
                  background: "var(--popover)",
                  color: "var(--popover-foreground)",
                }}
              />
              <Legend
                formatter={(value: string) =>
                  value === "principal"
                    ? "Тело"
                    : value === "interest"
                      ? "Проценты"
                      : "Рассрочки"
                }
              />
              <Bar
                dataKey="principal"
                stackId="a"
                fill={CHART.principal}
                radius={[0, 0, 0, 0]}
              />
              <Bar
                dataKey="interest"
                stackId="a"
                fill={CHART.interest}
                radius={[0, 0, 0, 0]}
              />
              <Bar
                dataKey="installment"
                stackId="a"
                fill={CHART.installment}
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
