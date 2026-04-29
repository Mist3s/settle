/**
 * App layout wrapper — sidebar (desktop) + header + mobile nav.
 */

import { Outlet } from "react-router-dom";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { MobileNav } from "./mobile-nav";

export function AppLayout() {
  return (
    <div className="flex min-h-dvh">
      <Sidebar />

      <div className="flex flex-1 flex-col min-w-0">
        <Header />

        <main className="flex-1 p-4 lg:p-6 pb-20 lg:pb-6">
          <Outlet />
        </main>

        <MobileNav />
      </div>
    </div>
  );
}
