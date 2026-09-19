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
    <header className="h-16 fixed top-0 right-0 left-0 lg:left-60 bg-white border-b border-[#E4E7EC] z-20 flex items-center justify-between px-4 sm:px-6 shadow-2xs">
      <div className="flex items-center gap-3 flex-1 max-w-lg">
        {onToggleMobileNav && (
          <button
            type="button"
            onClick={onToggleMobileNav}
            className="lg:hidden p-2 text-[#667085] hover:text-[#1E293B] hover:bg-slate-100 rounded-md focus:outline-none focus:ring-2 focus:ring-[#4F46E5]"
            aria-label="Toggle navigation"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        <form onSubmit={handleSearch} className="w-full relative">
          <label htmlFor="global-search" className="sr-only">
            Search customers or order ID
          </label>
          <div className="relative">
            <Search className="w-4 h-4 text-[#667085] absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              id="global-search"
              type="search"
              placeholder="Search customer name, email, phone, or ORD-204..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-1.5 text-xs sm:text-sm bg-[#F6F8FB] border border-[#D0D5DD] rounded-md text-[#1E293B] placeholder-[#667085] focus:outline-none focus:ring-2 focus:ring-[#4F46E5] focus:bg-white transition-all"
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
