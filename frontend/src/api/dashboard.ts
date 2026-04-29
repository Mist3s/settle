/**
 * Dashboard & Forecast API module.
 */

import client from "./client";
import type { DashboardResponse, ForecastResponse } from "@/types/api";

export async function getDashboard(): Promise<DashboardResponse> {
  const { data } = await client.get<DashboardResponse>("/dashboard");
  return data;
}

export async function getForecast(params: {
  from: string;
  to: string;
  starting_balance: string;
}): Promise<ForecastResponse> {
  const { data } = await client.get<ForecastResponse>(
    "/forecast/balance-by-day",
    { params },
  );
  return data;
}
