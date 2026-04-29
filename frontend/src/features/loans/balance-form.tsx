/**
 * Dialog for manually updating loan balance (POST /loans/{id}/balance).
 */

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
import { useCreateBalance } from "@/features/loans/hooks";
import { format } from "date-fns";

const balanceSchema = z.object({
  amount: z.string().min(1, "Укажите сумму"),
  snapshot_date: z.string().min(1, "Укажите дату"),
  notes: z.string().optional(),
});

type BalanceFormValues = z.infer<typeof balanceSchema>;

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  loanId: string;
}

export function BalanceFormDialog({ open, onOpenChange, loanId }: Props) {
  const mutation = useCreateBalance(loanId);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<BalanceFormValues>({
    resolver: zodResolver(balanceSchema),
    defaultValues: {
      amount: "",
      snapshot_date: format(new Date(), "yyyy-MM-dd"),
      notes: "",
    },
  });

  const onSubmit = async (values: BalanceFormValues) => {
    await mutation.mutateAsync({
      amount: values.amount,
      snapshot_date: values.snapshot_date,
      source: "manual",
      notes: values.notes || null,
    });
    reset();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Обновить остаток</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <Label htmlFor="balance-amount">Текущий остаток, ₽</Label>
            <Input
              id="balance-amount"
              {...register("amount")}
              placeholder="123456.78"
              autoFocus
            />
            {errors.amount && (
              <p className="text-xs text-danger mt-1">{errors.amount.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="balance-date">Дата снимка</Label>
            <Input
              id="balance-date"
              type="date"
              {...register("snapshot_date")}
            />
            {errors.snapshot_date && (
              <p className="text-xs text-danger mt-1">{errors.snapshot_date.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="balance-notes">Заметка</Label>
            <Input
              id="balance-notes"
              {...register("notes")}
              placeholder="Необязательно"
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Отмена
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              Сохранить
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
