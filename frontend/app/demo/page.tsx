import React from "react";
import { AppShell } from "@/components/shell/AppShell";
import { DemoControllerView } from "@/components/demo/DemoControllerView";

export default function DemoPage() {
  return (
    <AppShell>
      <DemoControllerView />
    </AppShell>
  );
}