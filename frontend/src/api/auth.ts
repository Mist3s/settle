/**
 * Auth API functions.
 */

import type { LoginRequest, TokenResponse } from "@/types/api";
import client, { clearTokens, setTokens } from "./client";

export async function login(credentials: LoginRequest): Promise<TokenResponse> {
  const { data } = await client.post<TokenResponse>("/auth/login", credentials);
  setTokens(data.access_token, data.refresh_token);
  return data;
}

export async function logout(): Promise<void> {
  try {
    await client.post("/auth/logout");
  } catch {
    // Logout is best-effort (stateless JWT)
  } finally {
    clearTokens();
  }
}
