/**
 * Income create/edit dialog — react-hook-form + zod validation.
 */

import { useEffect } from "react";
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
import { useCreateIncome, useUpdateIncome } from "@/features/incomes/hooks";
import type { IncomeResponse, IncomeStatus } from "@/types/api";

// ---------------------------------------------------------------------------
// Schema
// ---------------------------------------------------------------------------

const incomeSchema = z.object({
  code: z.string().min(1, "Обязательное поле"),
  name: z.string().optional(),
  amount: z.string().min(1, "Обязательное поле"),
  expected_date: z.string().min(1, "Обязательное поле"),
  status: z.enum(["expected", "received", "cancelled"]).default("expected"),
  notes: z.string().optional(),
});

type IncomeFormValues = z.infer<typeof incomeSchema>;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  income?: IncomeResponse; // if provided — edit mode
}

const STATUSES: { value: IncomeStatus; label: string }[] = [
  { value: "expected", label: "Ожидается" },
  { value: "received", label: "Получено" },
  { value: "cancelled", label: "Отменено" },
];

export function IncomeFormDialog({ open, onOpenChange, income }: Props) {
  const isEdit = !!income;
  const createMutation = useCreateIncome();
  const updateMutation = useUpdateIncome(income?.id ?? "");

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<IncomeFormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(incomeSchema) as any,
    defaultValues: {
      code: "",
      name: "",
      amount: "",
      expected_date: "",
      status: "expected",
      notes: "",
    },
  });

  // Populate form in edit mode
  useEffect(() => {
    if (income && open) {
      reset({
        code: income.code,
        name: income.name ?? "",
        amount: income.amount,
        expected_date: income.expected_date,
        status: income.status,
        notes: income.notes ?? "",
      });
    } else if (!income && open) {
      reset({
        code: "",
        name: "",
        amount: "",
        expected_date: "",
        status: "expected",
        notes: "",
      });
    }
  }, [income, open, reset]);

  const onSubmit = async (values: IncomeFormValues) => {
    const payload = {
      ...values,
      name: values.name || null,
      notes: values.notes || null,
    };

    if (isEdit) {
      await updateMutation.mutateAsync(payload);
    } else {
      await createMutation.mutateAsync(payload);
    }
    onOpenChange(false);
  };

  const status = watch("status");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? "Редактировать поступление" : "Новое поступление"}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={(e) => void handleSubmit(onSubmit)(e)} className="space-y-4">
          {/* Code + name */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="income-code">Код</Label>
              <Input
                id="income-code"
                {...register("code")}
                placeholder="SALARY-1"
              />
              {errors.code && (
                <p className="text-xs text-danger mt-1">{errors.code.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="income-name">Название</Label>
              <Input
                id="income-name"
                {...register("name")}
                placeholder="Зарплата"
              />
            </div>
          </div>

          {/* Amount + date */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="income-amount">Сумма</Label>
              <Input
                id="income-amount"
                {...register("amount")}
                placeholder="45000"
              />
              {errors.amount && (
                <p className="text-xs text-danger mt-1">{errors.amount.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="income-date">Дата</Label>
              <Input
                id="income-date"
                type="date"
                {...register("expected_date")}
              />
              {errors.expected_date && (
                <p className="text-xs text-danger mt-1">
                  {errors.expected_date.message}
                </p>
              )}
            </div>
          </div>

          {/* Status */}
          <div>
            <Label>Статус</Label>
            <Select
              value={status}
              onValueChange={(v) => {
                if (v) setValue("status", v as IncomeStatus);
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATUSES.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Notes */}
          <div>
            <Label htmlFor="income-notes">Заметки</Label>
            <Input
              id="income-notes"
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
              {isEdit ? "Сохранить" : "Создать"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
