/**
 * Mobile bottom navigation bar.
 * Visible on screens < 1024px.
 * 5 primary tabs + "More" popover for secondary items.
 */

import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  CreditCard,
  Wallet,
  CalendarDays,
  History,
  BarChart3,
  FlaskConical,
  Settings,
  MoreHorizontal,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

const PRIMARY_ITEMS = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Главная" },
  { to: "/loans", icon: CreditCard, label: "Кредиты" },
  { to: "/calendar", icon: CalendarDays, label: "Календарь" },
  { to: "/incomes", icon: Wallet, label: "Доходы" },
  { to: "/history", icon: History, label: "История" },
] as const;

const SECONDARY_ITEMS = [
  { to: "/analytics", icon: BarChart3, label: "Аналитика" },
  { to: "/simulator", icon: FlaskConical, label: "Симулятор" },
  { to: "/settings", icon: Settings, label: "Настройки" },
] as const;

export function MobileNav() {
  const [showMore, setShowMore] = useState(false);
  const location = useLocation();

  // Highlight "More" when a secondary route is active
  const isSecondaryActive = SECONDARY_ITEMS.some(
    (item) => location.pathname.startsWith(item.to),
  );

  return (
    <>
      {/* Overlay backdrop when "More" is open */}
      {showMore && (
        <div
          className="lg:hidden fixed inset-0 z-40 bg-black/30 backdrop-blur-[2px]"
          onClick={() => setShowMore(false)}
        />
      )}

      {/* "More" popup */}
      {showMore && (
        <div className="lg:hidden fixed bottom-16 right-2 z-50 w-44 rounded-xl border border-border bg-background shadow-xl animate-in fade-in slide-in-from-bottom-4 duration-200">
          <div className="flex items-center justify-between px-3 pt-2.5 pb-1">
            <span className="text-xs font-medium text-muted-foreground">
              Ещё
            </span>
            <button
              type="button"
              onClick={() => setShowMore(false)}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="size-3.5" />
            </button>
          </div>
          <div className="px-1 pb-2">
            {SECONDARY_ITEMS.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setShowMore(false)}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    isActive
                      ? "text-primary bg-primary/5"
                      : "text-foreground hover:bg-accent",
                  )
                }
              >
                <Icon className="size-4" />
                <span>{label}</span>
              </NavLink>
            ))}
          </div>
        </div>
      )}

      {/* Bottom tab bar */}
      <nav className="lg:hidden fixed bottom-0 inset-x-0 z-50 border-t border-border bg-background/95 backdrop-blur-sm">
        <ul className="flex items-center justify-around py-1 px-1">
          {PRIMARY_ITEMS.map(({ to, icon: Icon, label }) => (
            <li key={to}>
              <NavLink
                to={to}
                className={({ isActive }) =>
                  cn(
                    "flex flex-col items-center gap-0.5 px-2 py-1.5 text-[10px] font-medium transition-colors rounded-lg min-w-[3rem]",
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

          {/* More button */}
          <li>
            <button
              type="button"
              onClick={() => setShowMore(!showMore)}
              className={cn(
                "flex flex-col items-center gap-0.5 px-2 py-1.5 text-[10px] font-medium transition-colors rounded-lg min-w-[3rem]",
                isSecondaryActive || showMore
                  ? "text-primary"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <MoreHorizontal className="size-5" />
              <span>Ещё</span>
            </button>
          </li>
        </ul>
      </nav>
    </>
  );
}
