/**
 * Payments API module.
 */

import client from "./client";
import type {
  PlannedPaymentResponse,
  PlannedPaymentUpdate,
  ActualPaymentCreate,
  ActualPaymentResponse,
} from "@/types/api";

// -- Planned Payments -------------------------------------------------------

export async function getPlannedPayments(params?: {
  from?: string;
  to?: string;
  loan_id?: string;
  income_id?: string;
}): Promise<PlannedPaymentResponse[]> {
  const { data } = await client.get<PlannedPaymentResponse[]>(
    "/payments/planned",
    { params },
  );
  return data;
}

export async function getPlannedPayment(
  id: string,
): Promise<PlannedPaymentResponse> {
  const { data } = await client.get<PlannedPaymentResponse>(
    `/payments/planned/${id}`,
  );
  return data;
}

export async function updatePlannedPayment(
  id: string,
  update: PlannedPaymentUpdate,
): Promise<PlannedPaymentResponse> {
  const { data } = await client.patch<PlannedPaymentResponse>(
    `/payments/planned/${id}`,
    update,
  );
  return data;
}

// -- Actual Payments --------------------------------------------------------

export async function registerPayment(
  payment: ActualPaymentCreate,
): Promise<ActualPaymentResponse> {
  const { data } = await client.post<ActualPaymentResponse>(
    "/payments/actual",
    payment,
  );
  return data;
}

export async function getActualPayments(params?: {
  from?: string;
  to?: string;
  loan_id?: string;
}): Promise<ActualPaymentResponse[]> {
  const { data } = await client.get<ActualPaymentResponse[]>(
    "/payments/actual",
    { params },
  );
  return data;
}

export async function deleteActualPayment(id: string): Promise<void> {
  await client.delete(`/payments/actual/${id}`);
}
