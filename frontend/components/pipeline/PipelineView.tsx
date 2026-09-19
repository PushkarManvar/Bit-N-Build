"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  ChevronDown,
  CircleAlert,
  Filter,
  Layers3,
  RefreshCw,
  Search,
} from "lucide-react";
import { ApiClientError, getPipelineEvents, getPipelineOverview } from "@/lib/api";
import type {
  Channel,
  IdentityOutcome,
  PipelineEventOut,
  PipelineOverviewResponse,
  ProcessingStatus,
} from "@/lib/types";
import { CHANNEL_META, getEventTypeLabel } from "@/lib/presenters";
import {
  ChannelBadge,
  IdentityOutcomeBadge,
  ProcessingStatusBadge,
} from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Panel } from "@/components/ui/Panel";

const PAGE_SIZE = 25;

type EventFilters = {
  channel: Channel | "";
  processingStatus: ProcessingStatus | "";
  identityOutcome: IdentityOutcome | "";
  sourceEventId: string;
};

const initialFilters: EventFilters = {
  channel: "",
  processingStatus: "",
  identityOutcome: "",
  sourceEventId: "",
};

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown time";
  return new Intl.DateTimeFormat(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function shortId(value: string | null): string {
  return value ? `${value.slice(0, 8)}…` : "—";
}

function hasFilters(filters: EventFilters): boolean {
  return Boolean(
    filters.channel ||
      filters.processingStatus ||
      filters.identityOutcome ||
      filters.sourceEventId.trim()
  );
}

export function PipelineView() {
  const [overview, setOverview] = useState<PipelineOverviewResponse | null>(null);
  const [events, setEvents] = useState<PipelineEventOut[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [total, setTotal] = useState<number | null>(null);
  const [filters, setFilters] = useState<EventFilters>(initialFilters);
  const [loading, setLoading] = useState(true);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<ApiClientError | null>(null);

  const loadOverview = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getPipelineOverview({ limit: PAGE_SIZE });
      setOverview(response);
      setEvents(response.events);
      setNextCursor(response.next_cursor);
      setTotal(null);
      setFilters(initialFilters);
    } catch (caught) {
      setError(
        caught instanceof ApiClientError
          ? caught
          : new ApiClientError(0, {
              code: "PIPELINE_LOAD_FAILED",
              message: "The pipeline snapshot could not be loaded.",
              stage: "pipeline",
            })
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  const loadFilteredEvents = useCallback(async () => {
    setLoadingEvents(true);
    setError(null);
    try {
      const response = await getPipelineEvents({
        limit: PAGE_SIZE,
        channel: filters.channel || undefined,
        processingStatus: filters.processingStatus || undefined,
        identityOutcome: filters.identityOutcome || undefined,
        sourceEventId: filters.sourceEventId || undefined,
      });
      setEvents(response.items);
      setNextCursor(response.next_cursor);
      setTotal(response.total);
    } catch (caught) {
      setError(
        caught instanceof ApiClientError
          ? caught
          : new ApiClientError(0, {
              code: "PIPELINE_EVENTS_LOAD_FAILED",
              message: "The filtered event stream could not be loaded.",
              stage: "pipeline",
            })
      );
    } finally {
      setLoadingEvents(false);
    }
  }, [filters]);

  const loadMore = useCallback(async () => {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    setError(null);
    try {
      const response = await getPipelineEvents({
        limit: PAGE_SIZE,
        cursor: nextCursor,
        channel: filters.channel || undefined,
        processingStatus: filters.processingStatus || undefined,
        identityOutcome: filters.identityOutcome || undefined,
        sourceEventId: filters.sourceEventId || undefined,
      });
      setEvents((current) => [...current, ...response.items]);
      setNextCursor(response.next_cursor);
      setTotal(response.total);
    } catch (caught) {
      setError(
        caught instanceof ApiClientError
          ? caught
          : new ApiClientError(0, {
              code: "PIPELINE_EVENTS_LOAD_FAILED",
              message: "More pipeline events could not be loaded.",
              stage: "pipeline",
            })
      );
    } finally {
      setLoadingMore(false);
    }
  }, [filters, loadingMore, nextCursor]);

  const eventSummary = useMemo(() => {
    if (total !== null) return `${events.length} of ${total} matching events`;
    return `${events.length} most recent persisted events`;
  }, [events.length, total]);

  if (loading) {
    return <PipelineSkeleton />;
  }

  if (!overview || error) {
    return (
      <ErrorState
        title="Pipeline data is unavailable"
        message={error?.message ?? "The pipeline snapshot could not be loaded."}
        code={error?.code}
        onRetry={() => void loadOverview()}
      />
    );
  }

  const filtered = hasFilters(filters);

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#4F46E5]">
            Ingestion and normalization
          </p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-[#172554]">Data Pipeline</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#667085]">
            Inspect persisted events, normalization outcomes, and explainable identity decisions.
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs text-[#667085]">
          <span className="inline-flex items-center gap-2 rounded-full border border-teal-200 bg-teal-50 px-3 py-1.5 font-medium text-teal-800">
            <span className="h-2 w-2 rounded-full bg-[#0F766E]" aria-hidden="true" />
            Snapshot from {formatTimestamp(overview.as_of)}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void loadOverview()}
            icon={<RefreshCw className="h-3.5 w-3.5" />}
          >
            Refresh
          </Button>
        </div>
      </header>

      <section aria-labelledby="pipeline-stages-heading">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <h2 id="pipeline-stages-heading" className="text-base font-semibold text-[#172554]">
              Persisted processing stages
            </h2>
            <p className="mt-0.5 text-xs text-[#667085]">
              Counts reflect records persisted at the snapshot high-water mark.
            </p>
          </div>
          <span className="hidden text-xs text-[#667085] sm:block">Raw event → canonical event → identity decision</span>
        </div>
        <div className="rounded-xl border border-[#E4E7EC] bg-white p-3 shadow-sm">
          <div className="grid gap-3 lg:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr] lg:items-stretch">
            <StageCard label="Raw accepted" value={overview.stages.raw_accepted} detail="Persisted raw records" />
            <StageArrow />
            <StageCard label="Normalized" value={overview.stages.normalization_succeeded} detail="Canonical records created" />
            <StageArrow />
            <StageCard label="Identity decided" value={overview.stages.identity_decided} detail="Persisted decisions" />
            <StageArrow />
            <StageCard label="Profile linked" value={overview.stages.profile_linked} detail="Canonical rows with a profile" />
          </div>
          <div className="mt-3 grid gap-3 border-t border-[#E4E7EC] pt-3 sm:grid-cols-2">
            <ExceptionFact label="Normalization failed" value={overview.stages.normalization_failed} tone="failure" />
            <ExceptionFact label="Pending review" value={overview.stages.review_required} tone="review" />
          </div>
        </div>
      </section>

      <section aria-labelledby="channel-counts-heading">
        <div className="mb-3">
          <h2 id="channel-counts-heading" className="text-base font-semibold text-[#172554]">
            Channel distribution
          </h2>
          <p className="mt-0.5 text-xs text-[#667085]">Raw, normalized, and failed counts by recorded channel.</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {(Object.keys(overview.channels) as Channel[]).map((channel) => (
            <ChannelCard key={channel} channel={channel} counts={overview.channels[channel]} />
          ))}
        </div>
      </section>

      <Panel
        header={
          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
            <div>
              <h2 className="text-base font-semibold text-[#172554]">Event stream</h2>
              <p className="mt-0.5 text-xs text-[#667085]">{eventSummary}</p>
            </div>
            <span className="text-xs text-[#667085]">Newest received events first</span>
          </div>
        }
      >
        <form
          className="grid gap-3 border-b border-[#E4E7EC] pb-5 md:grid-cols-2 xl:grid-cols-[minmax(0,1.5fr)_repeat(3,minmax(0,1fr))_auto_auto]"
          onSubmit={(event) => {
            event.preventDefault();
            void loadFilteredEvents();
          }}
        >
          <label className="relative block">
            <span className="sr-only">Source event ID prefix</span>
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#667085]" aria-hidden="true" />
            <input
              value={filters.sourceEventId}
              onChange={(event) => setFilters((current) => ({ ...current, sourceEventId: event.target.value }))}
              placeholder="Find source event ID…"
              className="h-10 w-full rounded-md border border-[#D0D5DD] bg-white pl-9 pr-3 text-sm text-[#172554] outline-none placeholder:text-[#98A2B3] focus:border-[#4F46E5] focus:ring-2 focus:ring-indigo-100"
            />
          </label>
          <SelectFilter
            label="Channel"
            value={filters.channel}
            onChange={(value) => setFilters((current) => ({ ...current, channel: value as Channel | "" }))}
            options={[
              ["", "All channels"],
              ["web", "Website"],
              ["mobile_app", "Mobile app"],
              ["call_center", "Call centre"],
              ["physical_store", "Physical store"],
            ]}
          />
          <SelectFilter
            label="Processing status"
            value={filters.processingStatus}
            onChange={(value) => setFilters((current) => ({ ...current, processingStatus: value as ProcessingStatus | "" }))}
            options={[["", "All processing states"], ["normalized", "Normalized"], ["failed", "Failed"], ["received", "Received"]]}
          />
          <SelectFilter
            label="Identity outcome"
            value={filters.identityOutcome}
            onChange={(value) => setFilters((current) => ({ ...current, identityOutcome: value as IdentityOutcome | "" }))}
            options={[["", "All identity outcomes"], ["auto_linked", "Linked automatically"], ["review_required", "Needs review"], ["new_profile", "New profile created"]]}
          />
          <Button type="submit" variant="secondary" size="sm" icon={<Filter className="h-3.5 w-3.5" />} disabled={loadingEvents}>
            {loadingEvents ? "Filtering…" : "Apply"}
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={!filtered || loadingEvents}
            onClick={() => void loadOverview()}
          >
            Reset
          </Button>
        </form>

        {loadingEvents ? (
          <EventTableSkeleton />
        ) : events.length === 0 ? (
          <EmptyState
            className="mt-5"
            icon={<Layers3 className="h-6 w-6" />}
            title={filtered ? "No events match these filters" : "No persisted pipeline events yet"}
            description={
              filtered
                ? "Change or clear the filters to inspect other persisted events."
                : "Ingest an event or run the demo to populate the pipeline stream."
            }
            actionText={filtered ? "Clear filters" : undefined}
            onAction={filtered ? () => void loadOverview() : undefined}
          />
        ) : (
          <>
            <div className="mt-5 overflow-x-auto">
              <table className="w-full min-w-[780px] border-separate border-spacing-0 text-left">
                <caption className="sr-only">Persisted pipeline events</caption>
                <thead>
                  <tr className="text-xs font-semibold uppercase tracking-wide text-[#667085]">
                    <th className="border-b border-[#E4E7EC] px-3 py-3">Received</th>
                    <th className="border-b border-[#E4E7EC] px-3 py-3">Source event</th>
                    <th className="border-b border-[#E4E7EC] px-3 py-3">Channel</th>
                    <th className="border-b border-[#E4E7EC] px-3 py-3">Event type</th>
                    <th className="border-b border-[#E4E7EC] px-3 py-3">Processing</th>
                    <th className="border-b border-[#E4E7EC] px-3 py-3">Identity</th>
                    <th className="border-b border-[#E4E7EC] px-3 py-3">Profile</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((event) => <EventRow key={event.raw_event_id} event={event} />)}
                </tbody>
              </table>
            </div>
            {nextCursor && (
              <div className="mt-5 flex justify-center border-t border-[#E4E7EC] pt-5">
                <Button variant="outline" onClick={() => void loadMore()} disabled={loadingMore} icon={<ChevronDown className="h-4 w-4" />}>
                  {loadingMore ? "Loading events…" : "Load older events"}
                </Button>
              </div>
            )}
          </>
        )}
      </Panel>
    </div>
  );
}

function StageCard({ label, value, detail }: { label: string; value: number; detail: string }) {
  return (
    <div className="rounded-lg bg-[#F8FAFC] px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-[#4F46E5]">{label}</p>
      <p className="mt-2 tabular-nums text-2xl font-bold tracking-tight text-[#172554]">{value.toLocaleString()}</p>
      <p className="mt-1 text-xs text-[#667085]">{detail}</p>
    </div>
  );
}

function StageArrow() {
  return <ArrowRight className="mx-auto hidden h-4 w-4 text-[#98A2B3] lg:block lg:self-center" aria-hidden="true" />;
}

function ExceptionFact({ label, value, tone }: { label: string; value: number; tone: "failure" | "review" }) {
  const color = tone === "failure" ? "text-rose-700" : "text-amber-700";
  return (
    <div className="flex items-center justify-between rounded-lg bg-[#F8FAFC] px-4 py-3">
      <span className="flex items-center gap-2 text-sm font-medium text-[#344054]">
        <CircleAlert className={`h-4 w-4 ${color}`} aria-hidden="true" />
        {label}
      </span>
      <span className={`tabular-nums text-lg font-bold ${color}`}>{value.toLocaleString()}</span>
    </div>
  );
}

function ChannelCard({ channel, counts }: { channel: Channel; counts: { raw: number; normalized: number; failed: number } }) {
  const meta = CHANNEL_META[channel];
  return (
    <Panel className="shadow-none">
      <div className="flex items-center justify-between">
        <ChannelBadge channel={channel} />
        <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: meta.hex }} aria-label={`${meta.label} channel`} />
      </div>
      <dl className="mt-4 grid grid-cols-3 gap-2 text-center">
        <div>
          <dt className="text-[11px] font-medium uppercase tracking-wide text-[#667085]">Raw</dt>
          <dd className="mt-1 tabular-nums text-lg font-semibold text-[#172554]">{counts.raw.toLocaleString()}</dd>
        </div>
        <div>
          <dt className="text-[11px] font-medium uppercase tracking-wide text-[#667085]">Normalized</dt>
          <dd className="mt-1 tabular-nums text-lg font-semibold text-[#172554]">{counts.normalized.toLocaleString()}</dd>
        </div>
        <div>
          <dt className="text-[11px] font-medium uppercase tracking-wide text-[#667085]">Failed</dt>
          <dd className="mt-1 tabular-nums text-lg font-semibold text-[#172554]">{counts.failed.toLocaleString()}</dd>
        </div>
      </dl>
    </Panel>
  );
}

function SelectFilter({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: [string, string][];
}) {
  return (
    <label className="block">
      <span className="sr-only">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 w-full rounded-md border border-[#D0D5DD] bg-white px-3 text-sm text-[#344054] outline-none focus:border-[#4F46E5] focus:ring-2 focus:ring-indigo-100"
      >
        {options.map(([optionValue, optionLabel]) => <option key={optionValue} value={optionValue}>{optionLabel}</option>)}
      </select>
    </label>
  );
}

function EventRow({ event }: { event: PipelineEventOut }) {
  return (
    <tr className="group hover:bg-slate-50">
      <td className="border-b border-[#EAECF0] px-3 py-3.5 text-sm text-[#475467]">{formatTimestamp(event.received_at)}</td>
      <td className="border-b border-[#EAECF0] px-3 py-3.5 font-mono text-xs font-semibold text-[#344054]">{event.source_event_id}</td>
      <td className="border-b border-[#EAECF0] px-3 py-3.5"><ChannelBadge channel={event.channel} /></td>
      <td className="border-b border-[#EAECF0] px-3 py-3.5 text-sm text-[#344054]">{event.event_type ? getEventTypeLabel(event.event_type) : "Not normalized"}</td>
      <td className="border-b border-[#EAECF0] px-3 py-3.5">
        <ProcessingStatusBadge status={event.processing_status} />
        {event.processing_error_code && <p className="mt-1 text-xs font-medium text-rose-700">{event.processing_error_code}</p>}
      </td>
      <td className="border-b border-[#EAECF0] px-3 py-3.5">
        {event.identity_outcome ? <IdentityOutcomeBadge outcome={event.identity_outcome} /> : <span className="text-sm text-[#98A2B3]">—</span>}
      </td>
      <td className="border-b border-[#EAECF0] px-3 py-3.5 font-mono text-xs text-[#475467]">{shortId(event.profile_id)}</td>
    </tr>
  );
}

function PipelineSkeleton() {
  return (
    <div className="space-y-6" aria-label="Loading pipeline data">
      <div className="h-24 animate-pulse rounded-xl bg-slate-200" />
      <div className="grid gap-3 md:grid-cols-4">
        {[0, 1, 2, 3].map((item) => <div key={item} className="h-32 animate-pulse rounded-xl bg-slate-200" />)}
      </div>
      <div className="h-96 animate-pulse rounded-xl bg-slate-200" />
    </div>
  );
}

function EventTableSkeleton() {
  return <div className="mt-5 h-64 animate-pulse rounded-lg bg-slate-100" aria-label="Loading event stream" />;
}
