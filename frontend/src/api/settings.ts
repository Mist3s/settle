/**
 * Settings API module.
 */

import client from "./client";
import type { SettingResponse, SettingsUpdate } from "@/types/api";

export async function getSettings(): Promise<SettingResponse[]> {
  const { data } = await client.get<SettingResponse[]>("/settings");
  return data;
}

export async function updateSettings(
  update: SettingsUpdate,
): Promise<SettingResponse[]> {
  const { data } = await client.patch<SettingResponse[]>("/settings", update);
  return data;
}
