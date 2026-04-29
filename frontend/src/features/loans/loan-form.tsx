/**
 * Loan create/edit dialog — react-hook-form + zod validation.
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
import { useCreateLoan, useUpdateLoan } from "@/features/loans/hooks";
import { loanTypeLabel } from "@/lib/format";
import type { LoanResponse, LoanType, PaymentMethod, PrepaymentStrategy } from "@/types/api";

// ---------------------------------------------------------------------------
// Schema
// ---------------------------------------------------------------------------

const loanSchema = z.object({
  code: z.string().min(1, "Обязательное поле"),
  creditor: z.string().min(1, "Обязательное поле"),
  name: z.string().min(1, "Обязательное поле"),
  loan_type: z.enum(["credit", "installment", "split", "utilities", "other_debt"]),
  payment_method: z.enum(["annuity", "differentiated", "installment", "split", "one_time"]),
  original_amount: z.string().optional(),
  interest_rate: z.string().default("0"),
  opening_date: z.string().optional(),
  closing_date: z.string().optional(),
  prepayment_strategy: z.enum(["reduce_payment", "shorten_term"]).default("reduce_payment"),
  priority: z.coerce.number().int().optional(),
  months_remaining: z.coerce.number().int().optional(),
  payment_day: z.coerce.number().int().min(1).max(31).optional(),
  contract_number: z.string().optional(),
  notes: z.string().optional(),
});

type LoanFormValues = z.infer<typeof loanSchema>;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  loan?: LoanResponse; // if provided — edit mode
}

const LOAN_TYPES: LoanType[] = ["credit", "installment", "split", "utilities", "other_debt"];
const PAYMENT_METHODS: { value: PaymentMethod; label: string }[] = [
  { value: "annuity", label: "Аннуитет" },
  { value: "differentiated", label: "Дифференцированный" },
  { value: "installment", label: "Рассрочка" },
  { value: "split", label: "Сплит" },
  { value: "one_time", label: "Разовый" },
];
const STRATEGIES: { value: PrepaymentStrategy; label: string }[] = [
  { value: "reduce_payment", label: "Уменьшить платёж" },
  { value: "shorten_term", label: "Сократить срок" },
];

export function LoanFormDialog({ open, onOpenChange, loan }: Props) {
  const isEdit = !!loan;
  const createMutation = useCreateLoan();
  const updateMutation = useUpdateLoan(loan?.id ?? "");

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<LoanFormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(loanSchema) as any,
    defaultValues: {
      code: "",
      creditor: "",
      name: "",
      loan_type: "credit",
      payment_method: "annuity",
      original_amount: "",
      interest_rate: "0",
      prepayment_strategy: "reduce_payment",
    },
  });

  // Populate form in edit mode
  useEffect(() => {
    if (loan && open) {
      reset({
        code: loan.code,
        creditor: loan.creditor,
        name: loan.name,
        loan_type: loan.loan_type,
        payment_method: loan.payment_method,
        original_amount: loan.original_amount ?? "",
        interest_rate: loan.interest_rate,
        opening_date: loan.opening_date ?? "",
        closing_date: loan.closing_date ?? "",
        prepayment_strategy: loan.prepayment_strategy,
        priority: loan.priority ?? undefined,
        months_remaining: loan.months_remaining ?? undefined,
        payment_day: loan.payment_day ?? undefined,
        contract_number: loan.contract_number ?? "",
        notes: loan.notes ?? "",
      });
    } else if (!loan && open) {
      reset({
        code: "",
        creditor: "",
        name: "",
        loan_type: "credit",
        payment_method: "annuity",
        original_amount: "",
        interest_rate: "0",
        prepayment_strategy: "reduce_payment",
      });
    }
  }, [loan, open, reset]);

  const onSubmit = async (values: LoanFormValues) => {
    const payload = {
      ...values,
      original_amount: values.original_amount || null,
      opening_date: values.opening_date || null,
      closing_date: values.closing_date || null,
      contract_number: values.contract_number || null,
      notes: values.notes || null,
      priority: values.priority ?? null,
      months_remaining: values.months_remaining ?? null,
      payment_day: values.payment_day ?? null,
    };

    if (isEdit) {
      await updateMutation.mutateAsync(payload);
    } else {
      await createMutation.mutateAsync(payload);
    }
    onOpenChange(false);
  };

  const loanType = watch("loan_type");
  const paymentMethod = watch("payment_method");
  const strategy = watch("prepayment_strategy");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Редактировать кредит" : "Новый кредит"}</DialogTitle>
        </DialogHeader>

        <form onSubmit={(e) => void handleSubmit(onSubmit)(e)} className="space-y-4">
          {/* Row 1: code + creditor */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="code">Код</Label>
              <Input id="code" {...register("code")} placeholder="ALFA-1" />
              {errors.code && (
                <p className="text-xs text-danger mt-1">{errors.code.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="creditor">Кредитор</Label>
              <Input id="creditor" {...register("creditor")} placeholder="Альфа-Банк" />
              {errors.creditor && (
                <p className="text-xs text-danger mt-1">{errors.creditor.message}</p>
              )}
            </div>
          </div>

          {/* Name */}
          <div>
            <Label htmlFor="name">Название</Label>
            <Input id="name" {...register("name")} placeholder="Кредит наличными" />
            {errors.name && (
              <p className="text-xs text-danger mt-1">{errors.name.message}</p>
            )}
          </div>

          {/* Type + method */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Тип</Label>
              <Select
                value={loanType}
                onValueChange={(v) => { if (v) setValue("loan_type", v as LoanType); }}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {LOAN_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {loanTypeLabel(t)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Метод платежа</Label>
              <Select
                value={paymentMethod}
                onValueChange={(v) => { if (v) setValue("payment_method", v as PaymentMethod); }}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PAYMENT_METHODS.map((m) => (
                    <SelectItem key={m.value} value={m.value}>
                      {m.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Amount + rate */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="original_amount">Сумма кредита</Label>
              <Input
                id="original_amount"
                {...register("original_amount")}
                placeholder="500000"
              />
            </div>
            <div>
              <Label htmlFor="interest_rate">Ставка, %</Label>
              <Input
                id="interest_rate"
                {...register("interest_rate")}
                placeholder="12.5"
              />
            </div>
          </div>

          {/* Dates */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="opening_date">Дата открытия</Label>
              <Input id="opening_date" type="date" {...register("opening_date")} />
            </div>
            <div>
              <Label htmlFor="closing_date">Дата закрытия</Label>
              <Input id="closing_date" type="date" {...register("closing_date")} />
            </div>
          </div>

          {/* Months + payment day */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <Label htmlFor="months_remaining">Месяцев</Label>
              <Input
                id="months_remaining"
                type="number"
                {...register("months_remaining")}
                placeholder="24"
              />
            </div>
            <div>
              <Label htmlFor="payment_day">День платежа</Label>
              <Input
                id="payment_day"
                type="number"
                {...register("payment_day")}
                placeholder="15"
              />
            </div>
            <div>
              <Label htmlFor="priority">Приоритет</Label>
              <Input
                id="priority"
                type="number"
                {...register("priority")}
                placeholder="1"
              />
            </div>
          </div>

          {/* Strategy */}
          <div>
            <Label>Стратегия досрочного</Label>
            <Select
              value={strategy}
              onValueChange={(v) => { if (v) setValue("prepayment_strategy", v as PrepaymentStrategy); }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STRATEGIES.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Contract + notes */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="contract_number">№ договора</Label>
              <Input
                id="contract_number"
                {...register("contract_number")}
                placeholder="Необязательно"
              />
            </div>
            <div>
              <Label htmlFor="notes">Заметки</Label>
              <Input id="notes" {...register("notes")} placeholder="Необязательно" />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
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
