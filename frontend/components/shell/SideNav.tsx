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
      badge:
        pendingCount !== null && pendingCount > 0 ? pendingCount : undefined,
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
    <aside className="flex h-full w-60 select-none flex-col justify-between bg-white text-slate-700">
      <div>
        {/* Brand header */}
        <div className="flex h-16 items-center border-b border-[#E9E7FF] px-5">
          <Link
            href="/customers"
            className="flex items-center gap-2.5 text-base font-bold tracking-tight text-[#172554] transition-colors hover:text-indigo-700"
            onClick={onCloseMobileNav}
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#5146E5] text-white shadow-sm">
              <Compass className="h-5 w-5" aria-hidden="true" />
            </div>
            <span>JourneyLens</span>
          </Link>
        </div>

        {/* Navigation list */}
        <nav className="space-y-1 px-3 py-5" aria-label="Main Navigation">
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
                className={`flex items-center justify-between rounded-lg px-3.5 py-2.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 ${
                  isActive
                    ? "bg-[#F0EFFF] font-semibold text-[#5B52E8]"
                    : "text-slate-600 hover:bg-[#F7F6FF] hover:text-[#312E81]"
                }`}
                aria-current={isActive ? "page" : undefined}
              >
                <div className="flex items-center gap-3">
                  <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                  <span>{item.label}</span>
                </div>
                {item.badge !== undefined && (
                  <span className="rounded-full bg-[#FDE2E1] px-2 py-0.5 text-[11px] font-bold text-[#B42318]">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer / version info */}
      <div className="m-3 rounded-xl border border-[#E9E7FF] bg-[#F7F6FF] p-3 text-xs text-slate-600">
        <div className="flex items-center justify-between gap-2">
          <div className="font-semibold text-[#312E81]">Demo workspace</div>
          <span
            className="h-2.5 w-2.5 rounded-full bg-teal-500"
            aria-label="Connected"
          />
        </div>
        <div className="mt-1 text-[11px] text-slate-500">
          Riya / ORD-204 scenario
        </div>
      </div>
    </aside>
  );
}
