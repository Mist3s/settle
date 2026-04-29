/**
 * Register actual payment dialog — with auto-type detection.
 *
 * Compares entered amount against the selected planned payment to
 * auto-suggest payment type (regular / overpayment / underpayment / etc.)
 */

import { useEffect, useMemo } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useLoans } from "@/features/loans/hooks";
import { usePlannedPayments, useRegisterPayment } from "@/features/payments/hooks";
import { formatMoney } from "@/lib/format";
import type { ActualPaymentType } from "@/types/api";

// ---------------------------------------------------------------------------
// Schema
// ---------------------------------------------------------------------------

const paymentSchema = z.object({
  loan_id: z.string().min(1, "Выберите кредит"),
  planned_payment_id: z.string().optional(),
  amount: z.string().min(1, "Обязательное поле"),
  payment_date: z.string().min(1, "Обязательное поле"),
  payment_type: z.enum([
    "regular",
    "early_partial",
    "early_full",
    "overpayment",
    "underpayment",
    "missed",
  ]),
  notes: z.string().optional(),
});

type PaymentFormValues = z.infer<typeof paymentSchema>;

// ---------------------------------------------------------------------------
// Auto-detect payment type from amount vs planned
// ---------------------------------------------------------------------------

function detectPaymentType(
  amount: number,
  plannedAmount: number | null,
): ActualPaymentType {
  if (amount === 0) return "missed";
  if (plannedAmount == null) return "regular";
  const diff = amount - plannedAmount;
  const tolerance = plannedAmount * 0.005; // 0.5% tolerance
  if (Math.abs(diff) <= tolerance) return "regular";
  if (diff > 0) return "overpayment";
  return "underpayment";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Pre-fill loan_id when opening from loan detail */
  defaultLoanId?: string;
}

const PAYMENT_TYPES: { value: ActualPaymentType; label: string }[] = [
  { value: "regular", label: "Регулярный" },
  { value: "early_partial", label: "Досрочный частичный" },
  { value: "early_full", label: "Досрочный полный" },
  { value: "overpayment", label: "Переплата" },
  { value: "underpayment", label: "Недоплата" },
  { value: "missed", label: "Пропущен" },
];

export function RegisterPaymentDialog({
  open,
  onOpenChange,
  defaultLoanId,
}: Props) {
  const registerMutation = useRegisterPayment();
  const { data: loans } = useLoans();

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<PaymentFormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(paymentSchema) as any,
    defaultValues: {
      loan_id: defaultLoanId ?? "",
      planned_payment_id: "",
      amount: "",
      payment_date: new Date().toISOString().slice(0, 10),
      payment_type: "regular",
      notes: "",
    },
  });

  const loanId = watch("loan_id");
  const amount = watch("amount");
  const plannedPaymentId = watch("planned_payment_id");
  const paymentType = watch("payment_type");

  // Fetch planned payments for selected loan (only pending)
  const { data: plannedPayments } = usePlannedPayments(
    loanId ? { loan_id: loanId } : undefined,
  );

  const pendingPayments = useMemo(
    () =>
      (plannedPayments ?? []).filter(
        (p) => p.status === "pending" || p.status === "overdue",
      ),
    [plannedPayments],
  );

  // Selected planned payment
  const selectedPlanned = useMemo(
    () => pendingPayments.find((p) => p.id === plannedPaymentId),
    [pendingPayments, plannedPaymentId],
  );

  // Auto-detect type when amount changes
  useEffect(() => {
    const numAmount = Number(amount);
    if (Number.isNaN(numAmount) || numAmount < 0) return;
    const plannedAmt = selectedPlanned ? Number(selectedPlanned.amount) : null;
    const detected = detectPaymentType(numAmount, plannedAmt);
    setValue("payment_type", detected);
  }, [amount, selectedPlanned, setValue]);

  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      reset({
        loan_id: defaultLoanId ?? "",
        planned_payment_id: "",
        amount: "",
        payment_date: new Date().toISOString().slice(0, 10),
        payment_type: "regular",
        notes: "",
      });
    }
  }, [open, defaultLoanId, reset]);

  const onSubmit = async (values: PaymentFormValues) => {
    await registerMutation.mutateAsync({
      loan_id: values.loan_id,
      planned_payment_id: values.planned_payment_id || null,
      amount: values.amount,
      payment_date: values.payment_date,
      payment_type: values.payment_type,
      notes: values.notes || null,
    });
    onOpenChange(false);
  };

  // Warning for overpayment/underpayment
  const showWarning =
    paymentType === "overpayment" || paymentType === "underpayment";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Зарегистрировать платёж</DialogTitle>
        </DialogHeader>

        <form
          onSubmit={(e) => void handleSubmit(onSubmit)(e)}
          className="space-y-4"
        >
          {/* Loan select */}
          <div>
            <Label>Кредит</Label>
            <Select
              value={loanId}
              onValueChange={(v) => {
                if (v) {
                  setValue("loan_id", v);
                  setValue("planned_payment_id", "");
                }
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Выберите кредит" />
              </SelectTrigger>
              <SelectContent>
                {(loans ?? [])
                  .filter((l) => l.status === "active")
                  .map((l) => (
                    <SelectItem key={l.id} value={l.id}>
                      {l.name} ({l.creditor})
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
            {errors.loan_id && (
              <p className="text-xs text-danger mt-1">
                {errors.loan_id.message}
              </p>
            )}
          </div>

          {/* Planned payment select */}
          {pendingPayments.length > 0 && (
            <div>
              <Label>Плановый платёж</Label>
              <Select
                value={plannedPaymentId ?? ""}
                onValueChange={(v) => {
                  if (v) setValue("planned_payment_id", v);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Без привязки" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Без привязки</SelectItem>
                  {pendingPayments.map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.due_date} — {formatMoney(p.amount)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Amount + date */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="pay-amount">Сумма</Label>
              <Input
                id="pay-amount"
                {...register("amount")}
                placeholder="15000"
              />
              {errors.amount && (
                <p className="text-xs text-danger mt-1">
                  {errors.amount.message}
                </p>
              )}
            </div>
            <div>
              <Label htmlFor="pay-date">Дата платежа</Label>
              <Input
                id="pay-date"
                type="date"
                {...register("payment_date")}
              />
              {errors.payment_date && (
                <p className="text-xs text-danger mt-1">
                  {errors.payment_date.message}
                </p>
              )}
            </div>
          </div>

          {/* Type (auto-detected, but editable) */}
          <div>
            <Label>
              Тип платежа{" "}
              <Badge variant="outline" className="ml-2 text-[10px]">
                авто
              </Badge>
            </Label>
            <Select
              value={paymentType}
              onValueChange={(v) => {
                if (v) setValue("payment_type", v as ActualPaymentType);
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PAYMENT_TYPES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Warning for non-regular */}
          {showWarning && selectedPlanned && (
            <div className="rounded-lg border border-warning/30 bg-warning/5 p-3 text-sm">
              {paymentType === "overpayment" ? (
                <p>
                  ⚠️ Сумма превышает плановый платёж (
                  {formatMoney(selectedPlanned.amount)}). Излишек будет
                  направлен на досрочное погашение тела долга.
                </p>
              ) : (
                <p>
                  ⚠️ Сумма меньше планового платежа (
                  {formatMoney(selectedPlanned.amount)}). Плановый платёж
                  будет отмечен как частично оплаченный.
                </p>
              )}
            </div>
          )}

          {/* Notes */}
          <div>
            <Label htmlFor="pay-notes">Заметки</Label>
            <Input
              id="pay-notes"
              {...register("notes")}
              placeholder="Необязательно"
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Отмена
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              Зарегистрировать
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
