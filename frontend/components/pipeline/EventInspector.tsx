"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, FileJson, GitBranch, X } from "lucide-react";
import { ApiClientError, getPipelineEventDetail } from "@/lib/api";
import type { PipelineEventDetailResponse } from "@/lib/types";
import { ChannelBadge, IdentityOutcomeBadge, ProcessingStatusBadge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { JsonViewer } from "@/components/ui/JsonViewer";
import { formatDateTime } from "@/lib/formatters";

type InspectorTab = "decision" | "canonical" | "raw";

const tabs: { id: InspectorTab; label: string }[] = [
  { id: "decision", label: "Identity decision" },
  { id: "canonical", label: "Canonical event" },
  { id: "raw", label: "Raw event" },
];

export function EventInspector({ rawEventId, onClose }: { rawEventId: string | null; onClose: () => void }) {
  const [detail, setDetail] = useState<PipelineEventDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiClientError | null>(null);
  const [activeTab, setActiveTab] = useState<InspectorTab>("decision");
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  const loadDetail = useCallback(async (eventId: string, signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const response = await getPipelineEventDetail(eventId, signal);
      setDetail(response);
    } catch (caught) {
      if (signal?.aborted) return;
      setError(
        caught instanceof ApiClientError
          ? caught
          : new ApiClientError(0, {
              code: "PIPELINE_INSPECTOR_LOAD_FAILED",
              message: "The event inspector could not be loaded.",
              stage: "pipeline",
            })
      );
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!rawEventId) return;
    const controller = new AbortController();
    setDetail(null);
    setActiveTab("decision");
    void loadDetail(rawEventId, controller.signal);
    closeButtonRef.current?.focus();
    return () => controller.abort();
  }, [loadDetail, rawEventId]);

  useEffect(() => {
    if (!rawEventId) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose, rawEventId]);

  if (!rawEventId) return null;

  const selectRelativeTab = (direction: 1 | -1) => {
    const currentIndex = tabs.findIndex((tab) => tab.id === activeTab);
    setActiveTab(tabs[(currentIndex + direction + tabs.length) % tabs.length].id);
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/35 backdrop-blur-[1px]" onClick={onClose}>
      <aside
        className="flex h-full w-full max-w-2xl flex-col border-l border-[#E4E7EC] bg-[#FBFAFF] shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="pipeline-inspector-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex items-start justify-between gap-4 border-b border-[#E4E7EC] bg-white px-5 py-4 sm:px-6">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#4F46E5]">Event inspector</p>
            <h2 id="pipeline-inspector-title" className="mt-1 truncate text-lg font-bold text-[#172554]">
              {detail?.event.source_event_id ?? "Loading event…"}
            </h2>
            <p className="mt-1 break-all font-mono text-xs text-[#667085]">Raw event ID: {rawEventId}</p>
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label="Close event inspector"
            className="rounded-md p-2 text-[#667085] hover:bg-slate-100 hover:text-[#172554] focus:outline-none focus:ring-2 focus:ring-[#4F46E5]"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </header>

        {loading ? <InspectorSkeleton /> : error ? (
          <div className="p-6">
            <ErrorState
              title="Event inspector is unavailable"
              message={error.message}
              code={error.code}
              onRetry={() => void loadDetail(rawEventId)}
            />
          </div>
        ) : detail ? (
          <>
            <div className="border-b border-[#E4E7EC] bg-white px-5 py-3 sm:px-6">
              <div className="flex flex-wrap items-center gap-2">
                <ChannelBadge channel={detail.event.channel} />
                <ProcessingStatusBadge status={detail.event.processing_status} />
                {detail.event.identity_outcome && <IdentityOutcomeBadge outcome={detail.event.identity_outcome} />}
              </div>
            </div>
            <div className="border-b border-[#E4E7EC] bg-white px-5 sm:px-6" role="tablist" aria-label="Event inspector sections">
              <div className="flex gap-5 overflow-x-auto">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    role="tab"
                    id={`pipeline-tab-${tab.id}`}
                    aria-controls={`pipeline-panel-${tab.id}`}
                    aria-selected={activeTab === tab.id}
                    tabIndex={activeTab === tab.id ? 0 : -1}
                    onClick={() => setActiveTab(tab.id)}
                    onKeyDown={(event) => {
                      if (event.key === "ArrowRight") {
                        event.preventDefault();
                        selectRelativeTab(1);
                      }
                      if (event.key === "ArrowLeft") {
                        event.preventDefault();
                        selectRelativeTab(-1);
                      }
                    }}
                    className={`whitespace-nowrap border-b-2 py-3 text-sm font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-[#4F46E5] ${
                      activeTab === tab.id
                        ? "border-[#4F46E5] text-[#4F46E5]"
                        : "border-transparent text-[#667085] hover:text-[#344054]"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-5 sm:p-6">
              {activeTab === "decision" && <DecisionTab detail={detail} />}
              {activeTab === "canonical" && <CanonicalTab detail={detail} />}
              {activeTab === "raw" && <RawTab detail={detail} />}
            </div>
          </>
        ) : null}
      </aside>
    </div>
  );
}

function DecisionTab({ detail }: { detail: PipelineEventDetailResponse }) {
  const decision = detail.identity_decision;
  if (!decision) {
    return (
      <section id="pipeline-panel-decision" role="tabpanel" aria-labelledby="pipeline-tab-decision">
        <EmptyState
          icon={<GitBranch className="h-6 w-6" />}
          title="No identity decision was persisted"
          description="This raw event did not produce a canonical event and therefore has no identity decision."
        />
      </section>
    );
  }

  return (
    <section id="pipeline-panel-decision" role="tabpanel" aria-labelledby="pipeline-tab-decision" className="space-y-5">
      <div className="rounded-xl border border-[#E4E7EC] bg-white p-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-[#667085]">Persisted identity decision</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <IdentityOutcomeBadge outcome={decision.outcome} />
              {decision.review_status && <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800">Review: {decision.review_status}</span>}
            </div>
          </div>
          <div className="rounded-lg bg-slate-50 px-4 py-2 text-right">
            <p className="text-xs font-medium text-[#667085]">Score</p>
            <p className="tabular-nums text-2xl font-bold text-[#172554]">{decision.score}<span className="ml-1 text-xs font-normal text-[#667085]">/ 100</span></p>
          </div>
        </div>
        <Fact label="Canonical event ID" value={decision.canonical_event_id} mono />
        <Fact label="Selected profile ID" value={decision.selected_profile_id ?? "No profile selected"} mono />
        <Fact label="Reason" value={decision.reason ?? "No persisted decision reason."} />
      </div>
      <JsonSection title="Thresholds" data={decision.thresholds} />
      <JsonSection title="Evidence" data={decision.evidence} emptyMessage="No positive matching evidence was persisted." />
      <JsonSection title="Conflicts" data={decision.conflicts} emptyMessage="No conflicts were persisted." tone="warning" />
      <JsonSection title="Candidates" data={decision.candidates} emptyMessage="No candidate profiles were persisted." />
    </section>
  );
}

function CanonicalTab({ detail }: { detail: PipelineEventDetailResponse }) {
  const canonical = detail.canonical_event;
  if (!canonical) {
    return (
      <section id="pipeline-panel-canonical" role="tabpanel" aria-labelledby="pipeline-tab-canonical">
        <EmptyState
          icon={<FileJson className="h-6 w-6" />}
          title="No canonical event was created"
          description="Normalization did not complete for this raw event, so canonical fields are unavailable."
        />
      </section>
    );
  }
  return (
    <section id="pipeline-panel-canonical" role="tabpanel" aria-labelledby="pipeline-tab-canonical" className="space-y-5">
      <div className="rounded-xl border border-[#E4E7EC] bg-white p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-[#667085]">Canonical event record</p>
        <Fact label="Canonical event ID" value={canonical.id} mono />
        <Fact label="Source raw event ID" value={canonical.raw_event_id} mono />
        <Fact label="Event type" value={canonical.event_type.replace(/_/g, " ")} />
        <Fact label="Occurred at" value={formatDateTime(canonical.occurred_at)} />
        <Fact label="Canonical record created" value={formatDateTime(canonical.created_at)} />
      </div>
      <JsonSection title="Normalized canonical fields" data={{ identifiers: canonical.identifiers, entity_references: canonical.entity_references, attributes: canonical.attributes }} />
    </section>
  );
}

function RawTab({ detail }: { detail: PipelineEventDetailResponse }) {
  const raw = detail.raw_event;
  return (
    <section id="pipeline-panel-raw" role="tabpanel" aria-labelledby="pipeline-tab-raw" className="space-y-5">
      <div className="rounded-xl border border-[#E4E7EC] bg-white p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-[#667085]">Immutable raw event record</p>
        <Fact label="Raw event ID" value={raw.id} mono />
        <Fact label="Source event ID" value={raw.source_event_id} mono />
        <Fact label="Schema version" value={raw.schema_version} />
        <Fact label="Received at" value={formatDateTime(raw.received_at)} />
        <Fact label="Occurred at" value={formatDateTime(raw.occurred_at)} />
        {raw.processing_error && <Fact label="Processing error" value={raw.processing_error} tone="warning" />}
      </div>
      <JsonSection title="Raw payload" data={raw.payload} />
    </section>
  );
}

function Fact({ label, value, mono = false, tone }: { label: string; value: string; mono?: boolean; tone?: "warning" }) {
  return (
    <div className="mt-3 border-t border-[#EAECF0] pt-3">
      <p className="text-xs font-medium text-[#667085]">{label}</p>
      <p className={`mt-1 break-all text-sm ${mono ? "font-mono text-xs text-[#344054]" : tone === "warning" ? "text-rose-700" : "text-[#344054]"}`}>{value}</p>
    </div>
  );
}

function JsonSection({ title, data, emptyMessage, tone }: { title: string; data: unknown; emptyMessage?: string; tone?: "warning" }) {
  const isEmpty = Array.isArray(data) ? data.length === 0 : Object.keys(data as object).length === 0;
  return (
    <div className="rounded-xl border border-[#E4E7EC] bg-white p-4">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-[#172554]">
        {tone === "warning" && <AlertTriangle className="h-4 w-4 text-amber-600" aria-hidden="true" />}
        {title}
      </h3>
      {isEmpty && emptyMessage ? <p className="mt-3 text-sm text-[#667085]">{emptyMessage}</p> : <JsonViewer data={data} className="mt-3" />}
    </div>
  );
}

function InspectorSkeleton() {
  return <div className="m-6 h-80 animate-pulse rounded-xl bg-slate-100" aria-label="Loading event inspector" />;
}
