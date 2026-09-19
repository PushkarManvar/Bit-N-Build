import React, { Suspense } from "react";
import { CustomerExplorerClient } from "@/components/customers/CustomerExplorerClient";
import { TableSkeleton } from "@/components/ui/SkeletonBlock";

export default function CustomersPage() {
  return (
    <Suspense fallback={<TableSkeleton rows={8} />}>
      <CustomerExplorerClient />
    </Suspense>
  );
}
