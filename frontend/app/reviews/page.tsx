import React from "react";
import Link from "next/link";
import { GitPullRequest, ArrowRight } from "lucide-react";
import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";

export default function ReviewsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[#172554] tracking-tight">
          Review Queue
        </h1>
        <p className="text-sm text-[#667085] mt-1">
          Pending ambiguous identity decisions requiring human resolution
        </p>
      </div>

      <Panel>
        <div className="flex flex-col items-center justify-center p-8 text-center">
          <div className="w-12 h-12 mb-4 rounded-xl bg-amber-50 flex items-center justify-center text-[#D97706]">
            <GitPullRequest className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-semibold text-[#172554] mb-2">
            Available after backend integration
          </h2>
          <p className="text-sm text-[#667085] max-w-md mb-6 leading-relaxed">
            Human review decision resolution actions (approve, reject candidate, create profile) will be fully enabled in Stage 5. No fake review items are displayed.
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
