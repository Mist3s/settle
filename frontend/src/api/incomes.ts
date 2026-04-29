/**
 * Incomes API module.
 */

import client from "./client";
import type {
  IncomeCreate,
  IncomeUpdate,
  IncomeResponse,
} from "@/types/api";

export async function getIncomes(params?: {
  from?: string;
  to?: string;
}): Promise<IncomeResponse[]> {
  const { data } = await client.get<IncomeResponse[]>("/incomes", { params });
  return data;
}

export async function createIncome(
  income: IncomeCreate,
): Promise<IncomeResponse> {
  const { data } = await client.post<IncomeResponse>("/incomes", income);
  return data;
}

export async function updateIncome(
  id: string,
  update: IncomeUpdate,
): Promise<IncomeResponse> {
  const { data } = await client.patch<IncomeResponse>(
    `/incomes/${id}`,
    update,
  );
  return data;
}

export async function receiveIncome(id: string): Promise<IncomeResponse> {
  const { data } = await client.post<IncomeResponse>(
    `/incomes/${id}/receive`,
  );
  return data;
}

export async function deleteIncome(id: string): Promise<void> {
  await client.delete(`/incomes/${id}`);
}
