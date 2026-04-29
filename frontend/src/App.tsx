/**
 * Root application component.
 *
 * Sets up:
 * - RouterProvider for navigation
 * - Sonner toaster for notifications
 * - Auth initialization on mount
 */

import { useEffect } from "react";
import { RouterProvider } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { useAuthStore } from "@/stores/auth";
import { router } from "@/routes";

export default function App() {
  const checkAuth = useAuthStore((s) => s.checkAuth);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <>
      <RouterProvider router={router} />
      <Toaster position="top-right" richColors closeButton />
    </>
  );
}
