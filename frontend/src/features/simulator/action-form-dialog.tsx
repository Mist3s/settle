/**
 * Dialog for adding / editing a scenario action.
 * Dynamic fields based on action_type.
 */

import { useEffect, useMemo } from "react";
import { useForm, Controller } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useLoans } from "@/features/loans/hooks";
import { usePlannedPayments } from "@/features/payments/hooks";
import { useAddAction, useUpdateAction } from "./hooks";
import type {
  ScenarioActionResponse,
  ScenarioActionType,
} from "@/types/api";
import { format } from "date-fns";
import { formatMoney, formatDateShort } from "@/lib/format";

// ---------------------------------------------------------------------------
// Schema — base validation; type-specific required fields checked in onSubmit
// ---------------------------------------------------------------------------

const schema = z.object({
  action_type: z.string().min(1, "Выберите тип"),
  effective_date: z.string().min(1, "Укажите дату"),
  loan_id: z.string().optional(),
  planned_payment_id: z.string().optional(),
  amount: z.string().optional(),
  new_amount: z.string().optional(),
  new_date: z.string().optional(),
  income_name: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

const ACTION_TYPES: { value: ScenarioActionType; label: string }[] = [
  { value: "close_early_full", label: "Полное досрочное погашение" },
  { value: "prepayment_partial", label: "Частичное досрочное погашение" },
  { value: "reduce_payment", label: "Уменьшить платёж" },
  { value: "skip", label: "Пропустить платёж" },
  { value: "add_income", label: "Добавить доход" },
  { value: "change_payment_date", label: "Перенести дату платежа" },
];

// Which action types require loan_id
const NEEDS_LOAN = new Set<string>([
  "close_early_full",
  "prepayment_partial",
]);
// Which need planned_payment_id
const NEEDS_PAYMENT = new Set<string>([
  "reduce_payment",
  "skip",
  "change_payment_date",
]);

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  scenarioId: string;
  editAction: ScenarioActionResponse | null;
}

export function ActionFormDialog({
  open,
  onOpenChange,
  scenarioId,
  editAction,
}: Props) {
  const isEdit = !!editAction;
  const addMut = useAddAction(scenarioId);
  const updateMut = useUpdateAction(scenarioId);

  const { data: loans } = useLoans();
  const { data: plannedPayments } = usePlannedPayments({
    from: format(new Date(), "yyyy-MM-dd"),
  });

  const {
    register,
    handleSubmit,
    reset,
    watch,
    control,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema) as never,
    defaultValues: {
      action_type: "",
      effective_date: format(new Date(), "yyyy-MM-dd"),
    },
  });

  const actionType = watch("action_type");

  useEffect(() => {
    if (open) {
      if (editAction) {
        const p = editAction.params ?? {};
        reset({
          action_type: editAction.action_type,
          effective_date: editAction.effective_date,
          loan_id: editAction.loan_id ?? undefined,
          planned_payment_id: editAction.planned_payment_id ?? undefined,
          amount: (p.amount as string) ?? undefined,
          new_amount: (p.new_amount as string) ?? undefined,
          new_date: (p.new_date as string) ?? undefined,
          income_name: (p.name as string) ?? undefined,
        });
      } else {
        reset({
          action_type: "",
          effective_date: format(new Date(), "yyyy-MM-dd"),
        });
      }
    }
  }, [open, editAction, reset]);

  // Filtered payments based on selected loan (for payment-based actions)
  const selectedLoanId = watch("loan_id");
  const filteredPayments = useMemo(() => {
    if (!plannedPayments) return [];
    if (selectedLoanId) {
      return plannedPayments.filter((p) => p.loan_id === selectedLoanId);
    }
    return plannedPayments;
  }, [plannedPayments, selectedLoanId]);

  function onSubmit(values: FormValues) {
    const params: Record<string, unknown> = {};
    if (values.amount) params.amount = values.amount;
    if (values.new_amount) params.new_amount = values.new_amount;
    if (values.new_date) params.new_date = values.new_date;
    if (values.income_name) params.name = values.income_name;

    const payload = {
      action_type: values.action_type as ScenarioActionType,
      effective_date: values.effective_date,
      loan_id: NEEDS_LOAN.has(values.action_type)
        ? values.loan_id ?? null
        : null,
      planned_payment_id: NEEDS_PAYMENT.has(values.action_type)
        ? values.planned_payment_id ?? null
        : null,
      params: Object.keys(params).length > 0 ? params : null,
    };

    if (isEdit) {
      updateMut.mutate(
        { actionId: editAction!.id, data: payload },
        { onSuccess: () => onOpenChange(false) },
      );
    } else {
      addMut.mutate(payload, {
        onSuccess: () => onOpenChange(false),
      });
    }
  }

  const isPending = addMut.isPending || updateMut.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? "Редактировать действие" : "Добавить действие"}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Action type */}
          <div className="space-y-2">
            <Label>Тип действия</Label>
            <Controller
              name="action_type"
              control={control}
              render={({ field }) => (
                <Select
                  value={field.value}
                  onValueChange={(v) => v && field.onChange(v)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Выберите тип" />
                  </SelectTrigger>
                  <SelectContent>
                    {ACTION_TYPES.map((t) => (
                      <SelectItem key={t.value} value={t.value}>
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {errors.action_type && (
              <p className="text-sm text-danger">
                {errors.action_type.message}
              </p>
            )}
          </div>

          {/* Effective date */}
          <div className="space-y-2">
            <Label htmlFor="action-date">Дата</Label>
            <Input
              id="action-date"
              type="date"
              {...register("effective_date")}
            />
          </div>

          {/* Loan select — for close_early_full, prepayment_partial */}
          {NEEDS_LOAN.has(actionType) && (
            <div className="space-y-2">
              <Label>Кредит</Label>
              <Controller
                name="loan_id"
                control={control}
                render={({ field }) => (
                  <Select
                    value={field.value ?? ""}
                    onValueChange={(v) => v && field.onChange(v)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Выберите кредит" />
                    </SelectTrigger>
                    <SelectContent>
                      {loans
                        ?.filter((l) => l.status === "active")
                        .map((l) => (
                          <SelectItem key={l.id} value={l.id}>
                            {l.creditor} — {l.name}
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
          )}

          {/* Payment select — for reduce_payment, skip, change_payment_date */}
          {NEEDS_PAYMENT.has(actionType) && (
            <div className="space-y-2">
              <Label>Плановый платёж</Label>
              <Controller
                name="planned_payment_id"
                control={control}
                render={({ field }) => (
                  <Select
                    value={field.value ?? ""}
                    onValueChange={(v) => v && field.onChange(v)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Выберите платёж" />
                    </SelectTrigger>
                    <SelectContent>
                      {filteredPayments
                        .filter((p) => p.status === "pending")
                        .slice(0, 50)
                        .map((p) => {
                          const loan = loans?.find(
                            (l) => l.id === p.loan_id,
                          );
                          return (
                            <SelectItem key={p.id} value={p.id}>
                              {loan?.name ?? "?"} — {formatDateShort(p.due_date)}{" "}
                              ({formatMoney(p.amount)})
                            </SelectItem>
                          );
                        })}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
          )}

          {/* Amount — for prepayment_partial, add_income */}
          {(actionType === "prepayment_partial" ||
            actionType === "add_income") && (
            <div className="space-y-2">
              <Label htmlFor="action-amount">Сумма</Label>
              <Input
                id="action-amount"
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                {...register("amount")}
              />
            </div>
          )}

          {/* New amount — for reduce_payment */}
          {actionType === "reduce_payment" && (
            <div className="space-y-2">
              <Label htmlFor="action-new-amount">Новая сумма платежа</Label>
              <Input
                id="action-new-amount"
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                {...register("new_amount")}
              />
            </div>
          )}

          {/* New date — for change_payment_date */}
          {actionType === "change_payment_date" && (
            <div className="space-y-2">
              <Label htmlFor="action-new-date">Новая дата</Label>
              <Input
                id="action-new-date"
                type="date"
                {...register("new_date")}
              />
            </div>
          )}

          {/* Income name — for add_income */}
          {actionType === "add_income" && (
            <div className="space-y-2">
              <Label htmlFor="action-income-name">Название дохода</Label>
              <Input
                id="action-income-name"
                placeholder="Премия"
                {...register("income_name")}
              />
            </div>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Отмена
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending
                ? "Сохранение…"
                : isEdit
                  ? "Сохранить"
                  : "Добавить"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
