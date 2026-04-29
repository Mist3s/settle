/**
 * Settings form — key-value parameter editor grouped by category.
 */

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useSettings, useUpdateSettings } from "./hooks";
import { LoadingState } from "@/components/loading-state";
import { Save } from "lucide-react";

// Known settings keys with labels and categories
const SETTING_DEFS: {
  key: string;
  label: string;
  category: string;
  placeholder: string;
  type?: string;
}[] = [
  {
    key: "usd_rub_rate",
    label: "Курс USD/RUB",
    category: "Валюта",
    placeholder: "90.00",
    type: "number",
  },
  {
    key: "unavailable_balance",
    label: "Недоступный резерв (₽)",
    category: "Баланс",
    placeholder: "0.00",
    type: "number",
  },
  {
    key: "utilities_amount",
    label: "Коммунальные платежи (₽)",
    category: "Платежи",
    placeholder: "5000.00",
    type: "number",
  },
  {
    key: "living_threshold_green",
    label: "Порог «комфортно» (₽)",
    category: "Пороги",
    placeholder: "15000",
    type: "number",
  },
  {
    key: "living_threshold_yellow",
    label: "Порог «тесно» (₽)",
    category: "Пороги",
    placeholder: "5000",
    type: "number",
  },
];

type FormValues = Record<string, string>;

export function SettingsForm() {
  const { data: settings, isLoading, error } = useSettings();
  const updateMut = useUpdateSettings();

  const { register, handleSubmit, reset } = useForm<FormValues>();

  // Populate form from fetched settings
  useEffect(() => {
    if (settings) {
      const values: FormValues = {};
      for (const s of settings) {
        values[s.key] = s.value;
      }
      reset(values);
    }
  }, [settings, reset]);

  function onSubmit(values: FormValues) {
    const items = Object.entries(values)
      .filter(([, v]) => v !== undefined && v !== "")
      .map(([key, value]) => ({ key, value }));
    updateMut.mutate({ items });
  }

  // Group setting defs by category
  const categories = [...new Set(SETTING_DEFS.map((d) => d.category))];

  return (
    <LoadingState isLoading={isLoading} isError={!!error} isEmpty={false}>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {categories.map((cat) => (
          <Card key={cat}>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">{cat}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {SETTING_DEFS.filter((d) => d.category === cat).map((def) => (
                <div key={def.key} className="grid gap-2 sm:grid-cols-2 sm:items-center">
                  <Label htmlFor={`setting-${def.key}`}>{def.label}</Label>
                  <Input
                    id={`setting-${def.key}`}
                    type={def.type ?? "text"}
                    step={def.type === "number" ? "0.01" : undefined}
                    placeholder={def.placeholder}
                    {...register(def.key)}
                  />
                </div>
              ))}
            </CardContent>
          </Card>
        ))}

        {/* Custom settings from DB that aren't in SETTING_DEFS */}
        {settings && settings.filter((s) => !SETTING_DEFS.some((d) => d.key === s.key)).length > 0 && (
          <>
            <Separator />
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Прочие</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {settings
                  .filter((s) => !SETTING_DEFS.some((d) => d.key === s.key))
                  .map((s) => (
                    <div
                      key={s.key}
                      className="grid gap-2 sm:grid-cols-2 sm:items-center"
                    >
                      <Label htmlFor={`setting-${s.key}`}>
                        {s.description || s.key}
                      </Label>
                      <Input
                        id={`setting-${s.key}`}
                        placeholder={s.value}
                        {...register(s.key)}
                      />
                    </div>
                  ))}
              </CardContent>
            </Card>
          </>
        )}

        <Button type="submit" disabled={updateMut.isPending}>
          <Save className="mr-2 h-4 w-4" />
          {updateMut.isPending ? "Сохранение…" : "Сохранить настройки"}
        </Button>
      </form>
    </LoadingState>
  );
}
