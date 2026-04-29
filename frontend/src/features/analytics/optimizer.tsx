/**
 * Avalanche optimizer — table ranking loans by interest rate.
 * Recommends paying off highest-rate loans first.
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useOptimizer } from "./hooks";
import { formatMoney, formatPercent } from "@/lib/format";
import { Zap } from "lucide-react";

export function Optimizer() {
  const data = useOptimizer();

  if (!data.length) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          Нет кредитов с процентной ставкой для оптимизации
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Zap className="h-5 w-5 text-warning" />
          Оптимизатор приоритетов (метод лавины)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="mb-4 text-sm text-muted-foreground">
          Направляйте дополнительные средства на погашение кредитов в порядке
          убывания ставки. Это минимизирует общую переплату по процентам.
        </p>

        {/* Desktop table */}
        <div className="hidden sm:block">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">#</TableHead>
                <TableHead>Кредитор</TableHead>
                <TableHead>Название</TableHead>
                <TableHead className="text-right">Ставка</TableHead>
                <TableHead className="text-right">Остаток</TableHead>
                <TableHead className="text-right">Ср. платёж</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((l) => (
                <TableRow key={l.id}>
                  <TableCell>
                    <Badge
                      variant={l.rank <= 3 ? "default" : "outline"}
                      className="w-8 justify-center"
                    >
                      {l.rank}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-medium">{l.creditor}</TableCell>
                  <TableCell>{l.name}</TableCell>
                  <TableCell className="text-right font-mono">
                    {formatPercent(String(l.rate))}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatMoney(l.balance)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatMoney(String(l.monthlyPayment.toFixed(2)))}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Mobile cards */}
        <div className="space-y-2 sm:hidden">
          {data.map((l) => (
            <div
              key={l.id}
              className="flex items-center gap-3 rounded-lg border p-3"
            >
              <Badge
                variant={l.rank <= 3 ? "default" : "outline"}
                className="h-8 w-8 shrink-0 justify-center"
              >
                {l.rank}
              </Badge>
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">
                  {l.creditor} — {l.name}
                </p>
                <div className="flex gap-3 text-xs text-muted-foreground">
                  <span>{formatPercent(String(l.rate))}</span>
                  <span>{formatMoney(l.balance)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
