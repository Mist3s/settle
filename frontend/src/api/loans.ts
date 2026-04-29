/**
 * Loans API module.
 */

import client from "./client";
import type {
  LoanCreate,
  LoanUpdate,
  LoanResponse,
  BalanceCreate,
  BalanceResponse,
} from "@/types/api";

export async function getLoans(params?: {
  status?: string;
  type?: string;
}): Promise<LoanResponse[]> {
  const { data } = await client.get<LoanResponse[]>("/loans", { params });
  return data;
}

export async function getLoan(id: string): Promise<LoanResponse> {
  const { data } = await client.get<LoanResponse>(`/loans/${id}`);
  return data;
}

export async function createLoan(loan: LoanCreate): Promise<LoanResponse> {
  const { data } = await client.post<LoanResponse>("/loans", loan);
  return data;
}

export async function updateLoan(id: string, loan: LoanUpdate): Promise<LoanResponse> {
  const { data } = await client.patch<LoanResponse>(`/loans/${id}`, loan);
  return data;
}

export async function deleteLoan(id: string): Promise<void> {
  await client.delete(`/loans/${id}`);
}

export async function createBalance(
  loanId: string,
  balance: BalanceCreate,
): Promise<BalanceResponse> {
  const { data } = await client.post<BalanceResponse>(
    `/loans/${loanId}/balance`,
    balance,
  );
  return data;
}

export async function getLoanSchedule(loanId: string) {
  const { data } = await client.get(`/loans/${loanId}/schedule`);
  return data;
}
