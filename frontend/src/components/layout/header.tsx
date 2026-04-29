/**
 * Top header bar — shows page title and logout button.
 */

import { LogOut } from "lucide-react";
import { useAuthStore } from "@/stores/auth";
import { Button } from "@/components/ui/button";

interface HeaderProps {
  title?: string;
}

export function Header({ title = "Settle" }: HeaderProps) {
  const logout = useAuthStore((s) => s.logout);

  return (
    <header className="sticky top-0 z-40 flex items-center justify-between h-14 px-4 lg:px-6 border-b border-border bg-background/95 backdrop-blur-sm">
      {/* Mobile: show brand, Desktop: show page title */}
      <div className="flex items-center gap-2">
        <div className="lg:hidden size-7 rounded-md bg-primary flex items-center justify-center">
          <span className="text-primary-foreground font-bold text-xs">S</span>
        </div>
        <h1 className="text-base font-semibold text-foreground">{title}</h1>
      </div>

      <Button variant="ghost" size="icon-sm" onClick={() => void logout()}>
        <LogOut className="size-4" />
        <span className="sr-only">Выйти</span>
      </Button>
    </header>
  );
}
