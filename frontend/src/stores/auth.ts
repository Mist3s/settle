/**
 * Auth store (Zustand) — manages authentication state.
 *
 * Tokens live in localStorage (managed by api/client.ts).
 * This store tracks the derived `isAuthenticated` flag for React components.
 */

import { create } from "zustand";
import { login as apiLogin, logout as apiLogout } from "@/api/auth";
import { getAccessToken, clearTokens } from "@/api/client";
import type { LoginRequest } from "@/types/api";

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  /** Check localStorage for existing token on app init. */
  checkAuth: () => void;

  /** Login with credentials. */
  login: (credentials: LoginRequest) => Promise<void>;

  /** Logout and clear state. */
  logout: () => Promise<void>;

  /** Clear error message. */
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  isLoading: false,
  error: null,

  checkAuth: () => {
    const token = getAccessToken();
    set({ isAuthenticated: !!token });
  },

  login: async (credentials: LoginRequest) => {
    set({ isLoading: true, error: null });
    try {
      await apiLogin(credentials);
      set({ isAuthenticated: true, isLoading: false });
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Ошибка входа";
      set({ isLoading: false, error: message });
      throw err;
    }
  },

  logout: async () => {
    try {
      await apiLogout();
    } finally {
      clearTokens();
      set({ isAuthenticated: false, error: null });
    }
  },

  clearError: () => set({ error: null }),
}));
