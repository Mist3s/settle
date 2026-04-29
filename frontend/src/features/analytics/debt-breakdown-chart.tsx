/**
 * Debt breakdown chart — pie chart by creditor.
 */

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useDebtByCreditor } from "./hooks";
import { formatMoneyCompact } from "@/lib/format";

const COLORS = [
  "hsl(var(--primary))",
  "hsl(var(--success))",
  "hsl(var(--warning))",
  "hsl(var(--danger))",
  "hsl(270, 50%, 60%)",
  "hsl(200, 60%, 50%)",
  "hsl(340, 60%, 55%)",
  "hsl(160, 50%, 45%)",
];

export function DebtBreakdownChart() {
  const data = useDebtByCreditor();

  if (!data.length) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          Нет активных кредитов
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Долг по кредиторам</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="total"
                nameKey="creditor"
                cx="50%"
                cy="50%"
                outerRadius={100}
                innerRadius={50}
                paddingAngle={2}
                label={((props: any) =>  // eslint-disable-line @typescript-eslint/no-explicit-any
                  `${props.creditor ?? ""} ${(((props.percent as number) ?? 0) * 100).toFixed(0)}%`
                ) as any}
                labelLine={false}
              >
                {data.map((_, i) => (
                  <Cell
                    key={i}
                    fill={COLORS[i % COLORS.length]}
                    stroke="var(--background)"
                    strokeWidth={2}
                  />
                ))}
              </Pie>
              <Tooltip
                formatter={(value) =>
                  formatMoneyCompact(String(value))
                }
                contentStyle={{
                  borderRadius: "8px",
                  border: "1px solid var(--border)",
                  background: "var(--popover)",
                  color: "var(--popover-foreground)",
                }}
              />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
