/**
 * Application router configuration.
 */

import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppLayout } from "@/components/layout/app-layout";
import { ProtectedRoute } from "./protected-route";
import { LoginPage } from "@/pages/login";
import { DashboardPage } from "@/pages/dashboard";
import { LoansPage } from "@/pages/loans";
import { LoanDetailPage } from "@/pages/loan-detail";
import { IncomesPage } from "@/pages/incomes";
import { CalendarPage } from "@/pages/calendar";
import { HistoryPage } from "@/pages/history";
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
            path: "loans/:id",
            element: <LoanDetailPage />,
          },
          {
            path: "incomes",
            element: <IncomesPage />,
          },
          {
            path: "calendar",
            element: <CalendarPage />,
          },
          {
            path: "history",
            element: <HistoryPage />,
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
