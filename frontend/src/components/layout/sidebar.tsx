/**
 * Desktop sidebar navigation.
 * Visible on screens >= 1024px (lg breakpoint).
 */

import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  CreditCard,
  CalendarDays,
  FlaskConical,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Дашборд" },
  { to: "/loans", icon: CreditCard, label: "Кредиты" },
  { to: "/calendar", icon: CalendarDays, label: "Календарь" },
  { to: "/simulator", icon: FlaskConical, label: "Симулятор" },
  { to: "/settings", icon: Settings, label: "Настройки" },
] as const;

export function Sidebar() {
  return (
    <aside className="hidden lg:flex flex-col w-60 border-r border-border bg-sidebar min-h-dvh">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="size-8 rounded-lg bg-primary flex items-center justify-center">
          <span className="text-primary-foreground font-bold text-sm">S</span>
        </div>
        <span className="text-lg font-semibold text-sidebar-foreground tracking-tight">
          Settle
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-2">
        <ul className="space-y-1">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <li key={to}>
              <NavLink
                to={to}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-sidebar-accent text-sidebar-primary"
                      : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground",
                  )
                }
              >
                <Icon className="size-4 shrink-0" />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-sidebar-border">
        <p className="text-xs text-muted-foreground">
          Settle v0.1
        </p>
      </div>
    </aside>
  );
}
