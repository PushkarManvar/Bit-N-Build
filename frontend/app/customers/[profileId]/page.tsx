import React from "react";
import { JourneyDetailClient } from "@/components/journey/JourneyDetailClient";

interface PageProps {
  params: Promise<{ profileId: string }>;
}

export default async function CustomerJourneyPage({ params }: PageProps) {
  const { profileId } = await params;
  return <JourneyDetailClient profileId={profileId} />;
}
