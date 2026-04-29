/**
 * Settings page — placeholder.
 */

import { Card, CardContent } from "@/components/ui/card";

export function SettingsPage() {
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-semibold tracking-tight">Настройки</h2>
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          Настройки будут здесь
        </CardContent>
      </Card>
    </div>
  );
}
