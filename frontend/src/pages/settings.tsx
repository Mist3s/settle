/**
 * Settings page — tabs: Parameters / Import & Export.
 */

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SettingsForm } from "@/features/settings/settings-form";
import { ImportExportSection } from "@/features/settings/import-export-section";

export function SettingsPage() {
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-semibold tracking-tight">Настройки</h2>

      <Tabs defaultValue="params">
        <TabsList className="grid w-full grid-cols-2 sm:w-auto sm:grid-cols-none sm:inline-flex">
          <TabsTrigger value="params">Параметры</TabsTrigger>
          <TabsTrigger value="import-export">Импорт и экспорт</TabsTrigger>
        </TabsList>

        <TabsContent value="params" className="mt-4">
          <SettingsForm />
        </TabsContent>

        <TabsContent value="import-export" className="mt-4">
          <ImportExportSection />
        </TabsContent>
      </Tabs>
    </div>
  );
}
