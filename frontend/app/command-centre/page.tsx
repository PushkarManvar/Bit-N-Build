import React from "react";
import { AppShell } from "@/components/shell/AppShell";
import { CommandCentreView } from "@/components/dashboard/CommandCentreView";

export default function CommandCentrePage() {
  return (
    <AppShell>
      <CommandCentreView />
    </AppShell>
  );
}