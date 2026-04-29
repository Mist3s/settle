/**
 * Mobile bottom navigation bar.
 * Visible on screens < 1024px.
 */

import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  CreditCard,
  Wallet,
  CalendarDays,
  History,
  FlaskConical,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Дашборд" },
  { to: "/loans", icon: CreditCard, label: "Кредиты" },
  { to: "/incomes", icon: Wallet, label: "Доходы" },
  { to: "/calendar", icon: CalendarDays, label: "Календарь" },
  { to: "/history", icon: History, label: "История" },
  { to: "/simulator", icon: FlaskConical, label: "Симулятор" },
  { to: "/settings", icon: Settings, label: "Настройки" },
] as const;

export function MobileNav() {
  return (
    <nav className="lg:hidden fixed bottom-0 inset-x-0 z-50 border-t border-border bg-background/95 backdrop-blur-sm safe-area-inset-bottom">
      <ul className="flex items-center justify-around py-1.5">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <li key={to}>
            <NavLink
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex flex-col items-center gap-0.5 px-2 py-1 text-[10px] font-medium transition-colors rounded-md",
                  isActive
                    ? "text-primary"
                    : "text-muted-foreground hover:text-foreground",
                )
              }
            >
              <Icon className="size-5" />
              <span>{label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
