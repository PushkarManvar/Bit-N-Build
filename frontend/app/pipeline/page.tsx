import React from "react";
import Link from "next/link";
import { Layers, ArrowRight } from "lucide-react";
import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";

export default function PipelinePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[#172554] tracking-tight">
          Data Pipeline
        </h1>
        <p className="text-sm text-[#667085] mt-1">
          Ingestion funnel, channel distribution, and normalized event stream
        </p>
      </div>

      <Panel>
        <div className="flex flex-col items-center justify-center p-8 text-center">
          <div className="w-12 h-12 mb-4 rounded-xl bg-teal-50 flex items-center justify-center text-[#0F766E]">
            <Layers className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-semibold text-[#172554] mb-2">
            Available after backend integration
          </h2>
          <p className="text-sm text-[#667085] max-w-md mb-6 leading-relaxed">
            Full data pipeline telemetry, raw event stream, and normalization inspection will be connected in Stage 7 once supporting backend APIs are verified.
          </p>
          <Link href="/customers">
            <Button
              variant="outline"
              icon={<ArrowRight className="w-4 h-4" />}
              className="flex-row-reverse"
            >
              Explore Customers
            </Button>
          </Link>
        </div>
      </Panel>
    </div>
  );
}
