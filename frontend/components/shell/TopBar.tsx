"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Search, Menu } from "lucide-react";
import { ConnectivityStatus } from "./ConnectivityStatus";

interface TopBarProps {
  onToggleMobileNav?: () => void;
}

export function TopBar({ onToggleMobileNav }: TopBarProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const router = useRouter();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchTerm.trim()) {
      router.push(`/customers?search=${encodeURIComponent(searchTerm.trim())}`);
    }
  };

  return (
    <header className="fixed top-0 right-0 left-0 z-20 flex h-16 items-center justify-between border-b border-[#E9E7FF] bg-white/95 px-4 shadow-2xs backdrop-blur lg:left-60 sm:px-6">
      <div className="flex max-w-xl flex-1 items-center gap-3">
        {onToggleMobileNav && (
          <button
            type="button"
            onClick={onToggleMobileNav}
            className="rounded-md p-2 text-[#667085] transition-colors hover:bg-slate-100 hover:text-[#1E293B] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#4F46E5] lg:hidden"
            aria-label="Toggle navigation"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        <form onSubmit={handleSearch} className="relative w-full">
          <label htmlFor="global-search" className="sr-only">
            Search customers or order ID
          </label>
          <div className="relative">
            <Search
              className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-[#667085]"
              aria-hidden="true"
            />
            <input
              id="global-search"
              type="search"
              name="query"
              autoComplete="off"
              placeholder="Search customer name, email, phone, or ORD-204…"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full rounded-md border border-[#D0D5DD] bg-[#FAFAFF] py-1.5 pr-4 pl-9 text-xs text-[#1E293B] placeholder-[#667085] transition-colors focus:bg-white focus:outline-none focus-visible:ring-2 focus-visible:ring-[#4F46E5] sm:text-sm"
            />
          </div>
        </form>
      </div>

      <div className="flex items-center gap-3">
        <ConnectivityStatus />
      </div>
    </header>
  );
}
