import React from "react";
import Link from "next/link";
import { LayoutDashboard, ArrowRight } from "lucide-react";
import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";

export default function CommandCentrePage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[#172554] tracking-tight">
            Command Centre
          </h1>
          <p className="text-sm text-[#667085] mt-1">
            Operational dashboard and system telemetry
          </p>
        </div>
      </div>

      <Panel>
        <div className="flex flex-col items-center justify-center p-8 text-center">
          <div className="w-12 h-12 mb-4 rounded-xl bg-indigo-50 flex items-center justify-center text-[#4F46E5]">
            <LayoutDashboard className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-semibold text-[#172554] mb-2">
            Available after backend integration
          </h2>
          <p className="text-sm text-[#667085] max-w-md mb-6 leading-relaxed">
            Full command centre analytics, live alert feeds, and recent event polling will be wired in subsequent backend integration stages. No mock metrics or fabricated records are rendered here.
          </p>
          <Link href="/customers">
            <Button
              icon={<ArrowRight className="w-4 h-4" />}
              className="flex-row-reverse"
            >
              Go to Customer Explorer
            </Button>
          </Link>
        </div>
      </Panel>
    </div>
  );
}
