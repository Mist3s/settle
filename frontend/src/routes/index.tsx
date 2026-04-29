/**
 * Application router configuration.
 */

import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppLayout } from "@/components/layout/app-layout";
import { ProtectedRoute } from "./protected-route";
import { LoginPage } from "@/pages/login";
import { DashboardPage } from "@/pages/dashboard";
import { LoansPage } from "@/pages/loans";
import { CalendarPage } from "@/pages/calendar";
import { SimulatorPage } from "@/pages/simulator";
import { SettingsPage } from "@/pages/settings";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          {
            index: true,
            element: <Navigate to="/dashboard" replace />,
          },
          {
            path: "dashboard",
            element: <DashboardPage />,
          },
          {
            path: "loans",
            element: <LoansPage />,
          },
          {
            path: "calendar",
            element: <CalendarPage />,
          },
          {
            path: "simulator",
            element: <SimulatorPage />,
          },
          {
            path: "settings",
            element: <SettingsPage />,
          },
        ],
      },
    ],
  },
]);
