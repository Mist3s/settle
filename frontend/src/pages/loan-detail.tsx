/**
 * Loan detail page — full info, current balance, schedule chart,
 * planned payments table, action buttons.
 */

import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { LoadingState } from "@/components/loading-state";
import { useLoan, useLoanSchedule } from "@/features/loans/hooks";
import { ScheduleChart } from "@/features/loans/schedule-chart";
import { LoanFormDialog } from "@/features/loans/loan-form";
import { BalanceFormDialog } from "@/features/loans/balance-form";
import { StrategyToggle } from "@/features/loans/strategy-toggle";
import { RegisterPaymentDialog } from "@/features/payments/register-payment-dialog";
import {
  formatMoney,
  formatDate,
  formatPercent,
  loanTypeLabel,
  loanStatusLabel,
  accuracyLabel,
} from "@/lib/format";

const ACCURACY_ICONS: Record<string, string> = {
  exact_contract: "📄",
  exact_screenshot: "📸",
  calculated_annuity: "🧮",
  estimate: "❓",
};

export function LoanDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: loan, isLoading, isError } = useLoan(id ?? "");
  const { data: schedule, isLoading: scheduleLoading } = useLoanSchedule(id ?? "");
  const [showEdit, setShowEdit] = useState(false);
  const [showBalance, setShowBalance] = useState(false);
  const [showRegisterPayment, setShowRegisterPayment] = useState(false);

  return (
    <div className="space-y-4">
      <Button variant="ghost" size="sm" onClick={() => navigate("/loans")}>
        ← Назад к списку
      </Button>

      <LoadingState isLoading={isLoading} isError={isError} skeletonCount={2} skeletonHeight="h-40">
        {loan && (
          <>
            {/* Header card */}
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <CardTitle className="text-xl">{loan.name}</CardTitle>
                    <p className="text-sm text-muted-foreground mt-1">
                      {loan.creditor}
                      {loan.contract_number && ` · №${loan.contract_number}`}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{loanTypeLabel(loan.loan_type)}</Badge>
                    <Badge variant="outline">{loanStatusLabel(loan.status)}</Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                  {loan.original_amount && (
                    <div>
                      <span className="text-muted-foreground text-xs">Сумма кредита</span>
                      <p className="font-semibold">{formatMoney(loan.original_amount)}</p>
                    </div>
                  )}
                  <div>
                    <span className="text-muted-foreground text-xs">Ставка</span>
                    <p className="font-semibold">{formatPercent(loan.interest_rate)}</p>
                  </div>
                  {loan.months_remaining != null && (
                    <div>
                      <span className="text-muted-foreground text-xs">Осталось</span>
                      <p className="font-semibold">{loan.months_remaining} мес.</p>
                    </div>
                  )}
                  {loan.payment_day != null && (
                    <div>
                      <span className="text-muted-foreground text-xs">День платежа</span>
                      <p className="font-semibold">{loan.payment_day} числа</p>
                    </div>
                  )}
                  {loan.opening_date && (
                    <div>
                      <span className="text-muted-foreground text-xs">Открыт</span>
                      <p className="font-semibold">{formatDate(loan.opening_date)}</p>
                    </div>
                  )}
                  {loan.closing_date && (
                    <div>
                      <span className="text-muted-foreground text-xs">Закрытие</span>
                      <p className="font-semibold">{formatDate(loan.closing_date)}</p>
                    </div>
                  )}
                  {loan.priority != null && (
                    <div>
                      <span className="text-muted-foreground text-xs">Приоритет</span>
                      <p className="font-semibold">#{loan.priority}</p>
                    </div>
                  )}
                </div>

                <Separator className="my-4" />

                {/* Actions row */}
                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" size="sm" onClick={() => setShowEdit(true)}>
                    Редактировать
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setShowBalance(true)}>
                    Обновить остаток
                  </Button>
                  <Button size="sm" onClick={() => setShowRegisterPayment(true)}>
                    Зарегистрировать платёж
                  </Button>
                  <StrategyToggle loan={loan} />
                </div>

                {loan.notes && (
                  <p className="mt-3 text-xs text-muted-foreground italic">{loan.notes}</p>
                )}
              </CardContent>
            </Card>

            {/* Schedule chart */}
            <ScheduleChart
              schedule={schedule as Array<{ due_date: string; amount: string; principal_part: string; interest_part: string; balance_after: string }> | undefined}
              isLoading={scheduleLoading}
            />

            {/* Planned payments table */}
            {schedule && Array.isArray(schedule) && schedule.length > 0 && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Плановые платежи
                  </CardTitle>
                </CardHeader>
                <CardContent className="overflow-x-auto">
                  {/* Mobile: card layout */}
                  <div className="sm:hidden space-y-2">
                    {(schedule as Array<{ due_date: string; amount: string; principal_part: string; interest_part: string; balance_after: string; status?: string; accuracy?: string }>).map(
                      (entry, idx) => (
                        <div
                          key={idx}
                          className="rounded-md border px-3 py-2 text-sm space-y-1"
                        >
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">
                              {formatDate(entry.due_date)}
                            </span>
                            <span className="font-semibold">
                              {formatMoney(entry.amount)}
                            </span>
                          </div>
                          <div className="flex justify-between text-xs text-muted-foreground">
                            <span>Тело: {formatMoney(entry.principal_part)}</span>
                            <span>%: {formatMoney(entry.interest_part)}</span>
                          </div>
                          <div className="flex justify-between text-xs">
                            <span className="text-muted-foreground">
                              Остаток: {formatMoney(entry.balance_after)}
                            </span>
                            {entry.accuracy && (
                              <Tooltip>
                                <TooltipTrigger>
                                  <span className="cursor-help">
                                    {ACCURACY_ICONS[entry.accuracy] ?? "❓"}
                                  </span>
                                </TooltipTrigger>
                                <TooltipContent>{accuracyLabel(entry.accuracy)}</TooltipContent>
                              </Tooltip>
                            )}
                          </div>
                        </div>
                      ),
                    )}
                  </div>

                  {/* Desktop: table layout */}
                  <table className="hidden sm:table w-full text-sm">
                    <thead>
                      <tr className="border-b text-muted-foreground text-xs">
                        <th className="text-left py-2 font-medium">Дата</th>
                        <th className="text-right py-2 font-medium">Платёж</th>
                        <th className="text-right py-2 font-medium">Тело</th>
                        <th className="text-right py-2 font-medium">Проценты</th>
                        <th className="text-right py-2 font-medium">Остаток</th>
                        <th className="text-center py-2 font-medium">Точность</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(schedule as Array<{ due_date: string; amount: string; principal_part: string; interest_part: string; balance_after: string; status?: string; accuracy?: string }>).map(
                        (entry, idx) => (
                          <tr key={idx} className="border-b last:border-0 hover:bg-muted/30">
                            <td className="py-2">{formatDate(entry.due_date)}</td>
                            <td className="py-2 text-right font-medium">
                              {formatMoney(entry.amount)}
                            </td>
                            <td className="py-2 text-right">
                              {formatMoney(entry.principal_part)}
                            </td>
                            <td className="py-2 text-right">
                              {formatMoney(entry.interest_part)}
                            </td>
                            <td className="py-2 text-right">
                              {formatMoney(entry.balance_after)}
                            </td>
                            <td className="py-2 text-center">
                              {entry.accuracy && (
                                <Tooltip>
                                  <TooltipTrigger>
                                    <span className="cursor-help">
                                      {ACCURACY_ICONS[entry.accuracy] ?? "❓"}
                                    </span>
                                  </TooltipTrigger>
                                  <TooltipContent>{accuracyLabel(entry.accuracy)}</TooltipContent>
                                </Tooltip>
                              )}
                            </td>
                          </tr>
                        ),
                      )}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            )}

            {/* Dialogs */}
            <LoanFormDialog
              open={showEdit}
              onOpenChange={setShowEdit}
              loan={loan}
            />
            <BalanceFormDialog
              open={showBalance}
              onOpenChange={setShowBalance}
              loanId={loan.id}
            />
            <RegisterPaymentDialog
              open={showRegisterPayment}
              onOpenChange={setShowRegisterPayment}
              defaultLoanId={loan.id}
            />
          </>
        )}
      </LoadingState>
    </div>
  );
}
