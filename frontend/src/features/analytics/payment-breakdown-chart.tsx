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
import { formatMoneyCompact, formatMoney } from "@/lib/format";
import { CHART } from "@/lib/chart-colors";

const LABELS: Record<string, string> = {
  installment: "Рассрочки",
  interest: "Проценты",
  principal: "Тело",
};

const COLORS: Record<string, string> = {
  principal: CHART.principal,
  interest: CHART.interest,
  installment: CHART.installment,
};

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
  const total = payload.reduce((sum, entry) => sum + entry.value, 0);
  return (
    <div className="rounded-lg border bg-card px-3 py-2 shadow-md text-xs">
      <p className="font-medium mb-1">{label}</p>
      {payload.map((entry) => (
        <div key={entry.name} className="flex justify-between gap-4">
          <span style={{ color: COLORS[entry.name] ?? entry.color }}>
            {LABELS[entry.name] ?? entry.name}
          </span>
          <span className="font-medium">{formatMoney(String(entry.value))}</span>
        </div>
      ))}
      <div className="border-t mt-1 pt-1 flex justify-between gap-4 font-semibold">
        <span>Итого</span>
        <span>{formatMoney(String(total))}</span>
      </div>
    </div>
  );
}

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
              <Tooltip content={<CustomTooltip />} />
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
