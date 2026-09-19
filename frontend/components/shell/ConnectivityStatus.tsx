"use client";

import React, { useEffect, useState } from "react";
import { getHealth } from "@/lib/api";
import type { HealthResult } from "@/lib/types";

export function ConnectivityStatus() {
  const [health, setHealth] = useState<HealthResult>({
    ok: false,
    label: "checking...",
  });

  useEffect(() => {
    let mounted = true;

    const check = async () => {
      const res = await getHealth();
      if (mounted) {
        setHealth(res);
      }
    };

    check();
    const interval = setInterval(check, 10_000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <div
      className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium bg-white border border-[#D0D5DD] shadow-2xs"
      title={`Backend API: ${health.label}`}
      role="status"
    >
      <span
        className={`w-2 h-2 rounded-full ${
          health.ok ? "bg-emerald-500 animate-pulse" : "bg-amber-500"
        }`}
        aria-hidden="true"
      />
      <span className="text-[#667085] hidden sm:inline">API:</span>
      <span
        className={`font-semibold ${
          health.ok ? "text-emerald-700" : "text-amber-700"
        }`}
      >
        {health.label}
      </span>
    </div>
  );
}
