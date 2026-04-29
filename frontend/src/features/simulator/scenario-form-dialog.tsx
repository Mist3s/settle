/**
 * Dialog for creating / editing a scenario.
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useCreateScenario, useUpdateScenario } from "./hooks";
import type { ScenarioResponse } from "@/types/api";
import { format } from "date-fns";

const schema = z.object({
  name: z.string().min(1, "Введите название").max(255),
  base_date: z.string().min(1, "Выберите дату"),
});

type FormValues = z.infer<typeof schema>;

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  scenario: ScenarioResponse | null;
}

export function ScenarioFormDialog({ open, onOpenChange, scenario }: Props) {
  const isEdit = !!scenario;
  const createMut = useCreateScenario();
  const updateMut = useUpdateScenario();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema) as never,
    defaultValues: {
      name: "",
      base_date: format(new Date(), "yyyy-MM-dd"),
    },
  });

  useEffect(() => {
    if (open) {
      reset({
        name: scenario?.name ?? "",
        base_date: scenario?.base_date ?? format(new Date(), "yyyy-MM-dd"),
      });
    }
  }, [open, scenario, reset]);

  function onSubmit(values: FormValues) {
    if (isEdit) {
      updateMut.mutate(
        { id: scenario!.id, data: values },
        { onSuccess: () => onOpenChange(false) },
      );
    } else {
      createMut.mutate(values, {
        onSuccess: () => onOpenChange(false),
      });
    }
  }

  const isPending = createMut.isPending || updateMut.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? "Редактировать сценарий" : "Новый сценарий"}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="scenario-name">Название</Label>
            <Input
              id="scenario-name"
              placeholder="Закрыть Сплит в мае"
              {...register("name")}
            />
            {errors.name && (
              <p className="text-sm text-danger">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="scenario-date">Базовая дата</Label>
            <Input id="scenario-date" type="date" {...register("base_date")} />
            {errors.base_date && (
              <p className="text-sm text-danger">{errors.base_date.message}</p>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Отмена
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? "Сохранение…" : isEdit ? "Сохранить" : "Создать"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
