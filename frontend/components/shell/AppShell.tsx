"use client";

import React, { useState } from "react";
import { SideNav } from "./SideNav";
import { TopBar } from "./TopBar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#FBFAFF] flex">
      <a
        href="#main-content"
        className="sr-only fixed left-4 top-4 z-[60] rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white focus:not-sr-only focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300"
      >
        Skip to main content
      </a>
      {/* Desktop fixed sidebar (240px = w-60) */}
      <div className="fixed inset-y-0 left-0 z-30 hidden w-60 border-r border-[#E9E7FF] bg-white lg:block">
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
            className="fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <SideNav onCloseMobileNav={() => setMobileNavOpen(false)} />
          </div>
        </div>
      )}

      {/* Main content column */}
      <div className="min-w-0 flex-1 flex flex-col lg:pl-60">
        <TopBar onToggleMobileNav={() => setMobileNavOpen(true)} />
        <main
          id="main-content"
          className="w-full flex-1 p-4 pt-16 sm:p-6 sm:pt-16 lg:p-8 lg:pt-16"
        >
          {children}
        </main>
      </div>
    </div>
  );
}
