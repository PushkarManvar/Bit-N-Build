"use client";

import React, { useState } from "react";
import { SideNav } from "./SideNav";
import { TopBar } from "./TopBar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#F6F8FB] flex">
      {/* Desktop fixed sidebar (240px = w-60) */}
      <div className="hidden lg:block fixed inset-y-0 left-0 w-60 z-30 shadow-md">
        <SideNav />
      </div>

      {/* Mobile drawer backdrop and sidebar */}
      {mobileNavOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-xs lg:hidden"
          onClick={() => setMobileNavOpen(false)}
          aria-hidden="true"
        >
          <div
            className="fixed inset-y-0 left-0 w-64 z-50 bg-[#172554] shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <SideNav onCloseMobileNav={() => setMobileNavOpen(false)} />
          </div>
        </div>
      )}

      {/* Main content column */}
      <div className="flex-1 flex flex-col lg:pl-60 min-w-0">
        <TopBar onToggleMobileNav={() => setMobileNavOpen(true)} />
        <main className="flex-1 w-full pt-16 p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
