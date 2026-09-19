"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  GitPullRequest,
  PlayCircle,
  Layers,
  Compass,
} from "lucide-react";
import { getReviews } from "@/lib/api";

interface SideNavProps {
  onCloseMobileNav?: () => void;
}

export function SideNav({ onCloseMobileNav }: SideNavProps) {
  const pathname = usePathname();
  const [pendingCount, setPendingCount] = useState<number | null>(null);

  useEffect(() => {
    let mounted = true;
    const fetchPending = async () => {
      try {
        const res = await getReviews();
        if (mounted) {
          setPendingCount(res.total);
        }
      } catch {
        // Backend reviews endpoint might be gated or unavailable
      }
    };

    fetchPending();
    const interval = setInterval(fetchPending, 30_000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const navItems = [
    {
      label: "Command Centre",
      href: "/command-centre",
      icon: LayoutDashboard,
    },
    {
      label: "Customers",
      href: "/customers",
      icon: Users,
    },
    {
      label: "Review Queue",
      href: "/reviews",
      icon: GitPullRequest,
      badge: pendingCount !== null && pendingCount > 0 ? pendingCount : undefined,
    },
    {
      label: "Demo Controller",
      href: "/demo",
      icon: PlayCircle,
    },
    {
      label: "Data Pipeline",
      href: "/pipeline",
      icon: Layers,
    },
  ];

  return (
    <aside className="w-60 h-full bg-[#172554] text-white flex flex-col justify-between select-none">
      <div>
        {/* Brand header */}
        <div className="h-16 flex items-center px-5 border-b border-blue-900/60">
          <Link
            href="/customers"
            className="flex items-center gap-2.5 font-bold text-base tracking-tight text-white hover:text-blue-200 transition-colors"
            onClick={onCloseMobileNav}
          >
            <div className="w-8 h-8 rounded-lg bg-[#4F46E5] flex items-center justify-center text-white shadow-sm">
              <Compass className="w-5 h-5" />
            </div>
            <span>JourneyLens</span>
          </Link>
        </div>

        {/* Navigation list */}
        <nav className="p-3 space-y-1" aria-label="Main Navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              pathname === item.href ||
              (item.href !== "/" && pathname.startsWith(item.href));

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onCloseMobileNav}
                className={`flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs sm:text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-[#4F46E5] text-white font-semibold shadow-xs"
                    : "text-blue-100/80 hover:bg-white/10 hover:text-white"
                }`}
                aria-current={isActive ? "page" : undefined}
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
                  <span>{item.label}</span>
                </div>
                {item.badge !== undefined && (
                  <span className="px-2 py-0.5 text-[11px] font-bold bg-[#D97706] text-white rounded-full">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer / version info */}
      <div className="p-4 border-t border-blue-900/60 text-xs text-blue-200/60">
        <div className="font-medium text-blue-200">JourneyLens Operations</div>
        <div className="text-[11px] text-blue-300/60 mt-0.5">Flagship: Riya / ORD-204</div>
      </div>
    </aside>
  );
}
