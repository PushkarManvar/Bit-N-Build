"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  ClipboardCheck,
  Filter,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  UserRoundCheck,
  UsersRound,
  X,
} from "lucide-react";
import { ApiClientError, getReviewQueue, resolveReview } from "@/lib/api";
import {
  formatDateTime,
  formatShortUuid,
  formatTimeAgo,
} from "@/lib/formatters";
import { getEventTypeLabel } from "@/lib/presenters";
import type {
  Channel,
  ReviewDecision,
  ReviewQueueItem,
  ReviewQueueKind,
  ReviewQueuePriority,
  ReviewQueueSummary,
} from "@/lib/types";
import { ChannelBadge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { EmptyState } from "../ui/EmptyState";
import { ErrorState } from "../ui/ErrorState";

const REVIEWER_DEFAULT = "Demo Reviewer";
const PAGE_SIZE = 20;

type KindFilter = "all" | ReviewQueueKind;
type PriorityFilter = "all" | ReviewQueuePriority;

const CHANNEL_OPTIONS: Array<{ value: "all" | Channel; label: string }> = [
  { value: "all", label: "All channels" },
  { value: "web", label: "Website" },
  { value: "mobile_app", label: "Mobile app" },
  { value: "call_center", label: "Call centre" },
  { value: "physical_store", label: "Physical store" },
];

const ACTION_COPY: Record<ReviewDecision, string> = {
  approve_link: "Link approved",
  reject_link: "Candidate rejected",
  create_profile: "Separate profile created",
};

function conflictMessage(item: ReviewQueueItem): string | null {
  const message = item.conflicts[0]?.message;
  return (
    message ||
    (item.conflicts.length > 0
      ? "A strong identifier conflict requires a human decision."
      : null)
  );
}

function bestCandidate(item: ReviewQueueItem) {
  return item.candidates[0] ?? null;
}

const REVIEW_KIND_LABEL: Record<ReviewQueueKind, string> = {
  strong_identifier_conflict: "Strong conflict",
  ambiguous_moderate_match: "Ambiguous moderate match",
  same_name_collision: "Same-name safety",
  incomplete_evidence: "Incomplete evidence",
};

export function ReviewQueueClient() {
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [summary, setSummary] = useState<ReviewQueueSummary | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewerName, setReviewerName] = useState(REVIEWER_DEFAULT);
  const [channel, setChannel] = useState<"all" | Channel>("all");
  const [kind, setKind] = useState<KindFilter>("all");
  const [priority, setPriority] = useState<PriorityFilter>("all");
  const [selectedItem, setSelectedItem] = useState<ReviewQueueItem | null>(null);
  const [resolutionAction, setResolutionAction] =
    useState<ReviewDecision | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchReviews = useCallback(async (cursor?: string) => {
    setLoading(!cursor);
    setError(null);
    try {
      const response = await getReviewQueue({
        limit: PAGE_SIZE,
        cursor,
        channel: channel === "all" ? undefined : channel,
        kind: kind === "all" ? undefined : kind,
        priority: priority === "all" ? undefined : priority,
      });
      setItems((current) => (cursor ? [...current, ...response.items] : response.items));
      setSummary(response.summary);
      setNextCursor(response.next_cursor);
    } catch (err) {
      setError(
        err instanceof ApiClientError
          ? err.message
          : "Review queue could not be loaded.",
      );
    } finally {
      setLoading(false);
    }
  }, [channel, kind, priority]);

  useEffect(() => {
    void fetchReviews();
  }, [fetchReviews]);

  const clearFilters = () => {
    setChannel("all");
    setKind("all");
    setPriority("all");
  };

  const handleResolve = async (action: ReviewDecision, note: string) => {
    if (!selectedItem) return;

    setBusyId(selectedItem.match_decision_id);
    setActionMessage(null);
    try {
      const result = await resolveReview(selectedItem.match_decision_id, {
        action,
        selected_profile_id:
          action === "approve_link"
            ? bestCandidate(selectedItem)?.profile_id || null
            : null,
        reviewer_name: reviewerName.trim() || REVIEWER_DEFAULT,
        note:
          note.trim() ||
          (action === "approve_link"
            ? "Approved link after review."
            : action === "create_profile"
              ? "Created separate profile after review."
              : "Rejected candidate after review."),
      });

      setActionMessage(
        `${ACTION_COPY[result.action]} for case ${formatShortUuid(result.match_decision_id)}.`,
      );
      setSelectedItem(null);
      setResolutionAction(null);
      await fetchReviews();
    } catch (err) {
      setActionMessage(
        err instanceof ApiClientError ? err.message : "Resolution failed.",
      );
      setResolutionAction(null);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="mx-auto max-w-[1440px] space-y-6">
      <section className="flex flex-col gap-4 border-b border-[#E9E7FF] pb-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-balance text-3xl font-semibold tracking-tight text-[#172554]">
              Review Queue
            </h1>
            <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-800">
              {summary?.pending ?? 0} pending
            </span>
          </div>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#667085]">
            Resolve uncertain identity matches before they enter a unified
            customer journey.
          </p>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <label className="flex min-w-56 flex-col gap-1 text-sm font-medium text-[#475467]">
            Reviewer name
            <input
              type="text"
              name="reviewer"
              autoComplete="name"
              value={reviewerName}
              onChange={(event) => setReviewerName(event.target.value)}
              className="rounded-lg border border-[#D0D5DD] bg-white px-3 py-2 text-sm text-[#172554] outline-none transition-colors placeholder:text-[#98A2B3] focus-visible:ring-2 focus-visible:ring-indigo-500"
            />
          </label>
          <Button
            type="button"
            variant="outline"
            size="md"
            icon={
              <RefreshCw
                className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
              />
            }
            onClick={() => void fetchReviews()}
            disabled={loading}
          >
            Refresh
          </Button>
        </div>
      </section>

      {actionMessage && (
        <div
          className="flex items-start gap-3 rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-800"
          role="status"
          aria-live="polite"
        >
          <CheckCircle2
            className="mt-0.5 h-5 w-5 shrink-0"
            aria-hidden="true"
          />
          <p>{actionMessage}</p>
        </div>
      )}

      <section className="flex flex-col gap-3 rounded-xl border border-indigo-100 bg-[#F7F6FF] px-4 py-3 text-sm text-[#312E81] sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <ShieldCheck
            className="mt-0.5 h-5 w-5 shrink-0 text-indigo-700"
            aria-hidden="true"
          />
          <p>
            Review safeguards are active. Strong-identifier conflicts stay out
            of automatic linking.
          </p>
        </div>
        <span className="text-xs font-semibold text-indigo-700">
          {summary?.critical_conflicts ?? 0} conflict
          {(summary?.critical_conflicts ?? 0) === 1 ? "" : "s"} requiring
          inspection
        </span>
      </section>

      {loading ? (
        <QueueSkeleton />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void fetchReviews()} />
      ) : (
        <>
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <QueueMetric
              label="Pending review"
              value={summary?.pending ?? 0}
              detail="Human decisions waiting"
              icon={<UsersRound className="h-5 w-5" aria-hidden="true" />}
              tone="indigo"
            />
            <QueueMetric
              label="Strong conflicts"
              value={summary?.critical_conflicts ?? 0}
              detail="Never linked automatically"
              icon={<CircleAlert className="h-5 w-5" aria-hidden="true" />}
              tone="red"
            />
            <QueueMetric
              label="Incomplete evidence"
              value={summary?.incomplete_evidence ?? 0}
              detail="Moderate evidence needs review"
              icon={<UserRoundCheck className="h-5 w-5" aria-hidden="true" />}
              tone="teal"
            />
            <QueueMetric
              label="Same-name safety"
              value={summary?.same_name_collisions ?? 0}
              detail="Names never create a link"
              icon={<AlertTriangle className="h-5 w-5" aria-hidden="true" />}
              tone="amber"
            />
          </section>

          {items.length === 0 ? (
            <EmptyState
              title="No pending reviews"
              description="Every uncertain identity decision has been resolved. New ambiguous matches will appear here for human review."
            />
          ) : (
            <>
              <section className="rounded-2xl border border-[#E4E7EC] bg-white p-4 shadow-sm">
                <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
                  <Filter
                    className="hidden h-4 w-4 text-[#667085] lg:block"
                    aria-hidden="true"
                  />
                  <label className="flex items-center gap-2 text-sm text-[#475467]">
                    <span className="sr-only">Filter by channel</span>
                    <select
                      name="review-channel"
                      autoComplete="off"
                      value={channel}
                      onChange={(event) => setChannel(event.target.value as "all" | Channel)}
                      className="rounded-lg border border-[#D0D5DD] bg-white px-3 py-2.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                    >
                      {CHANNEL_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="flex items-center gap-2 text-sm text-[#475467]">
                    <span className="sr-only">Filter by review type</span>
                    <select
                      name="review-kind"
                      autoComplete="off"
                      value={kind}
                      onChange={(event) => setKind(event.target.value as KindFilter)}
                      className="rounded-lg border border-[#D0D5DD] bg-white px-3 py-2.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                    >
                      <option value="all">All review types</option>
                      <option value="strong_identifier_conflict">Strong conflicts</option>
                      <option value="incomplete_evidence">Incomplete evidence</option>
                      <option value="same_name_collision">Same-name safety</option>
                      <option value="ambiguous_moderate_match">Ambiguous moderate match</option>
                    </select>
                  </label>
                  <label className="flex items-center gap-2 text-sm text-[#475467]">
                    <span className="sr-only">Filter by priority</span>
                    <select
                      name="review-priority"
                      autoComplete="off"
                      value={priority}
                      onChange={(event) => setPriority(event.target.value as PriorityFilter)}
                      className="rounded-lg border border-[#D0D5DD] bg-white px-3 py-2.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                    >
                      <option value="all">All priorities</option>
                      <option value="critical">Critical</option>
                      <option value="high">High</option>
                      <option value="standard">Standard</option>
                    </select>
                  </label>
                </div>

                {(channel !== "all" || kind !== "all" || priority !== "all") && (
                  <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-[#E9E7FF] pt-3 text-xs text-[#667085]">
                    <span>Filters active</span>
                    <button
                      type="button"
                      className="font-semibold text-indigo-700 hover:text-indigo-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                      onClick={clearFilters}
                    >
                      Clear all
                    </button>
                  </div>
                )}
              </section>

              {items.length === 0 ? (
                <EmptyState
                  title="No cases match these filters"
                  description="Clear or adjust the filters to inspect a different set of pending reviews."
                  actionText="Clear all filters"
                  onAction={clearFilters}
                />
              ) : (
                <section className="overflow-hidden rounded-2xl border border-[#E4E7EC] bg-white shadow-sm">
                  <div className="flex flex-col gap-2 border-b border-[#E9E7FF] px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <h2 className="text-lg font-semibold text-[#172554]">
                        Pending identity decisions
                      </h2>
                      <p className="mt-1 text-xs text-[#667085]">
                        Showing {items.length} of {summary?.pending ?? 0} matching cases.
                      </p>
                    </div>
                    <span className="flex items-center gap-2 text-xs font-medium text-red-700">
                      <span
                        className="h-2 w-2 rounded-full bg-red-600"
                        aria-hidden="true"
                      />
                      Conflicts are highlighted
                    </span>
                  </div>

                  <div className="hidden grid-cols-[minmax(11rem,1fr)_minmax(11rem,0.9fr)_minmax(14rem,1.2fr)_minmax(12rem,1fr)_auto] gap-4 bg-[#F7F6FF] px-5 py-3 text-xs font-semibold uppercase tracking-wide text-[#667085] xl:grid">
                    <span>Incoming record</span>
                    <span>Suggested profile</span>
                    <span>Evidence</span>
                    <span>Safety signal</span>
                    <span className="text-right">Action</span>
                  </div>

                  <ul className="divide-y divide-[#E9E7FF]">
                    {items.map((item) => (
                      <ReviewRow
                        key={item.match_decision_id}
                        item={item}
                        onOpen={() => setSelectedItem(item)}
                      />
                    ))}
                  </ul>

                  {nextCursor && (
                    <div className="border-t border-[#E9E7FF] px-5 py-4 text-center">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => void fetchReviews(nextCursor)}
                      >
                        Load next{" "}
                        {Math.min(PAGE_SIZE, (summary?.pending ?? 0) - items.length)}{" "}
                        cases
                      </Button>
                    </div>
                  )}
                </section>
              )}
            </>
          )}
        </>
      )}

      {selectedItem && (
        <ReviewDrawer
          item={selectedItem}
          reviewerName={reviewerName}
          busy={busyId === selectedItem.match_decision_id}
          pendingAction={resolutionAction}
          onClose={() => {
            if (!busyId) setSelectedItem(null);
          }}
          onRequestResolution={(action, note) => {
            if (action === "approve_link") {
              setResolutionAction(action);
            } else {
              void handleResolve(action, note);
            }
          }}
          onApprove={(note) => void handleResolve("approve_link", note)}
          onCancelApproval={() => setResolutionAction(null)}
        />
      )}
    </div>
  );
}

function QueueMetric({
  label,
  value,
  detail,
  icon,
  tone,
}: {
  label: string;
  value: number;
  detail: string;
  icon: React.ReactNode;
  tone: "indigo" | "red" | "teal" | "amber";
}) {
  const toneClasses = {
    indigo: "bg-indigo-50 text-indigo-700",
    red: "bg-red-50 text-red-700",
    teal: "bg-teal-50 text-teal-700",
    amber: "bg-amber-50 text-amber-700",
  }[tone];

  return (
    <div className="rounded-xl border border-[#E4E7EC] bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-[#475467]">{label}</p>
        <span
          className={`flex h-9 w-9 items-center justify-center rounded-lg ${toneClasses}`}
        >
          {icon}
        </span>
      </div>
      <p className="mt-4 tabular-nums text-3xl font-semibold tracking-tight text-[#172554]">
        {value}
      </p>
      <p className="mt-1 text-xs text-[#667085]">{detail}</p>
    </div>
  );
}

function QueueSkeleton() {
  return (
    <div className="space-y-6" aria-label="Loading review queue">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((index) => (
          <div
            key={index}
            className="h-36 animate-pulse rounded-xl border border-[#E4E7EC] bg-white"
          />
        ))}
      </div>
      <div className="space-y-3 rounded-2xl border border-[#E4E7EC] bg-white p-5">
        {[0, 1, 2].map((index) => (
          <div
            key={index}
            className="h-24 animate-pulse rounded-xl bg-slate-100"
          />
        ))}
      </div>
    </div>
  );
}

function ReviewRow({ item, onOpen }: { item: ReviewQueueItem; onOpen: () => void }) {
  const conflict = conflictMessage(item);
  const candidate = bestCandidate(item);

  return (
    <li className="px-5 py-4 transition-colors hover:bg-[#FCFCFF]">
      <div className="grid gap-4 xl:grid-cols-[minmax(11rem,1fr)_minmax(11rem,0.9fr)_minmax(14rem,1.2fr)_minmax(12rem,1fr)_auto] xl:items-start">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            {item.event.channel && (
              <ChannelBadge channel={item.event.channel} />
            )}
            <span className="rounded-full border border-indigo-200 bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-700">
              {REVIEW_KIND_LABEL[item.review_kind]}
            </span>
            <span className="font-mono text-xs text-[#667085]">
              {formatShortUuid(item.match_decision_id)}
            </span>
          </div>
          <p className="mt-2 text-sm font-semibold text-[#172554]">
            {item.event.customer_name || "Unknown customer"}
          </p>
          <p className="mt-1 text-xs text-[#667085]">
            {item.event.event_type
              ? getEventTypeLabel(item.event.event_type)
              : "Unspecified event"}
            {item.event.occurred_at &&
              ` · ${formatTimeAgo(item.event.occurred_at)}`}
          </p>
        </div>

        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-[#667085] xl:hidden">
            Suggested profile
          </p>
          {candidate ? (
            <>
              <p className="mt-1 truncate text-sm font-semibold text-[#172554] xl:mt-0">
                {candidate.display_name || "Profile unavailable"}
              </p>
              <p className="mt-1 text-xs text-[#667085]">
                {formatShortUuid(candidate.profile_id)} · score {candidate.score}
              </p>
            </>
          ) : (
            <p className="mt-1 text-sm text-[#667085] xl:mt-0">
              No candidate suggested
            </p>
          )}
        </div>

        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-[#667085] xl:hidden">
            Evidence
          </p>
          {item.evidence.length > 0 ? (
            <ul className="mt-1 space-y-1 text-sm leading-5 text-[#475467] xl:mt-0">
              {item.evidence.slice(0, 2).map((evidence, index) => (
                <li
                  key={`${item.match_decision_id}-${index}`}
                  className="flex gap-2"
                >
                  <CheckCircle2
                    className="mt-0.5 h-3.5 w-3.5 shrink-0 text-teal-700"
                    aria-hidden="true"
                  />
                  <span>
                    {evidence.message} · {evidence.weight} points
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-1 text-sm text-[#667085] xl:mt-0">
              No positive evidence recorded
            </p>
          )}
        </div>

        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-[#667085] xl:hidden">
            Safety signal
          </p>
          {conflict ? (
            <div className="mt-1 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 xl:mt-0">
              <div className="flex items-center gap-1.5 font-semibold">
                <CircleAlert className="h-4 w-4 shrink-0" aria-hidden="true" />
                {REVIEW_KIND_LABEL[item.review_kind]}
              </div>
              <p className="mt-1 text-xs leading-5">{conflict}</p>
            </div>
          ) : (
            <div className="mt-1 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800 xl:mt-0">
              <p className="font-semibold">{REVIEW_KIND_LABEL[item.review_kind]}</p>
              <p className="mt-1 text-xs leading-5">
                {item.missing_strong_identifiers.length
                  ? `Missing: ${item.missing_strong_identifiers.join(", ")}`
                  : "Human validation required."}
              </p>
            </div>
          )}
        </div>

        <div className="flex xl:justify-end">
          <Button
            type="button"
            variant="outline"
            size="sm"
            icon={<ChevronRight className="h-4 w-4" />}
            onClick={onOpen}
          >
            Review case
          </Button>
        </div>
      </div>
    </li>
  );
}

function ReviewDrawer({
  item,
  reviewerName,
  busy,
  pendingAction,
  onClose,
  onRequestResolution,
  onApprove,
  onCancelApproval,
}: {
  item: ReviewQueueItem;
  reviewerName: string;
  busy: boolean;
  pendingAction: ReviewDecision | null;
  onClose: () => void;
  onRequestResolution: (action: ReviewDecision, note: string) => void;
  onApprove: (note: string) => void;
  onCancelApproval: () => void;
}) {
  const [note, setNote] = useState("");
  const conflict = conflictMessage(item);
  const candidate = bestCandidate(item);

  return (
    <>
      <button
        type="button"
        aria-label="Close review case"
        className="fixed inset-0 z-40 cursor-default bg-slate-950/30 backdrop-blur-[1px]"
        onClick={onClose}
        disabled={busy}
      />
      <aside
        className="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col overscroll-contain border-l border-[#E4E7EC] bg-[#FBFAFF] shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="review-case-title"
      >
        <header className="flex items-start justify-between gap-4 border-b border-[#E9E7FF] bg-white px-5 py-4 sm:px-6">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700">
                <ClipboardCheck className="h-5 w-5" aria-hidden="true" />
              </span>
              <div>
                <h2
                  id="review-case-title"
                  className="text-lg font-semibold text-[#172554]"
                >
                  Review case {formatShortUuid(item.match_decision_id)}
                </h2>
                <p className="mt-0.5 text-xs text-[#667085]">
                  Decide with the evidence below; no action is automatic.
                </p>
              </div>
            </div>
          </div>
          <button
            type="button"
            aria-label="Close review case"
            className="rounded-lg p-2 text-[#667085] transition-colors hover:bg-slate-100 hover:text-[#172554] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
            onClick={onClose}
            disabled={busy}
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </header>

        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-5 sm:p-6">
          {conflict && (
            <section className="rounded-xl border border-red-200 bg-red-50 p-4">
              <div className="flex items-start gap-3">
                <CircleAlert
                  className="mt-0.5 h-5 w-5 shrink-0 text-red-700"
                  aria-hidden="true"
                />
                <div>
                  <h3 className="font-semibold text-red-900">
                    Strong identifier conflict
                  </h3>
                  <p className="mt-1 break-words text-sm leading-6 text-red-800">
                    {conflict}
                  </p>
                  <p className="mt-2 text-xs font-semibold text-red-800">
                    Approve link is unavailable. Reject the candidate or create
                    a separate profile instead.
                  </p>
                </div>
              </div>
            </section>
          )}

          <section className="grid gap-4 md:grid-cols-[1fr_auto_1fr] md:items-stretch">
            <CaseRecord
              label="Incoming record"
              title={item.event.customer_name || "Unknown customer"}
              channel={item.event.channel}
              details={[
                item.event.event_type
                  ? getEventTypeLabel(item.event.event_type)
                  : "Unspecified event",
                formatDateTime(item.event.occurred_at),
              ]}
            />
            <div className="hidden items-center justify-center md:flex">
              <span className="rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700">
                Compare
              </span>
            </div>
            <CaseRecord
              label="Suggested profile"
              title={
                candidate?.display_name || "No profile suggested"
              }
              details={
                candidate
                  ? [
                      `Profile ${formatShortUuid(candidate.profile_id)}`,
                      `Score ${candidate.score}`,
                    ]
                  : ["No credible existing profile was returned"]
              }
            />
          </section>

          {item.candidates.length > 1 && (
            <section className="rounded-xl border border-[#E4E7EC] bg-white p-4">
              <h3 className="text-sm font-semibold text-[#172554]">
                Candidate alternatives
              </h3>
              <ul className="mt-3 divide-y divide-[#E9E7FF] rounded-lg border border-[#E4E7EC]">
                {item.candidates.map((alternative) => (
                  <li
                    key={alternative.profile_id}
                    className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm"
                  >
                    <span className="font-medium text-[#172554]">
                      {alternative.display_name || "Profile unavailable"}
                    </span>
                    <span className="text-xs text-[#667085]">
                      Score {alternative.score} · {alternative.matched_fields.join(", ")}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="rounded-xl border border-[#E4E7EC] bg-white p-4">
            <h3 className="text-sm font-semibold text-[#172554]">
              Evidence considered
            </h3>
            {item.evidence.length > 0 ? (
              <ul className="mt-3 space-y-2 text-sm leading-6 text-[#475467]">
                {item.evidence.map((evidence, index) => (
                  <li
                    key={`${item.match_decision_id}-evidence-${index}`}
                    className="flex gap-2 break-words"
                  >
                    <CheckCircle2
                      className="mt-1 h-4 w-4 shrink-0 text-teal-700"
                      aria-hidden="true"
                    />
                    <span>
                      {evidence.message} · {evidence.weight} points
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-[#667085]">
                No positive evidence was returned for this case.
              </p>
            )}
          </section>

          <section className="rounded-xl border border-amber-200 bg-amber-50/70 p-4">
            <h3 className="text-sm font-semibold text-amber-900">
              Missing strong identifiers
            </h3>
            <p className="mt-2 text-sm leading-6 text-amber-900">
              {item.missing_strong_identifiers.length
                ? item.missing_strong_identifiers.join(", ")
                : "No missing strong identifiers were reported."}
            </p>
          </section>

          {item.reason && (
            <section className="rounded-xl bg-[#F7F6FF] p-4">
              <h3 className="text-sm font-semibold text-[#312E81]">
                Decision context
              </h3>
              <p className="mt-2 text-sm leading-6 text-[#475467]">
                {item.reason}
              </p>
            </section>
          )}

          <label className="flex flex-col gap-2 text-sm font-medium text-[#475467]">
            Reviewer note{" "}
            <span className="font-normal text-[#98A2B3]">
              Optional, stored with the decision
            </span>
            <textarea
              name="review-note"
              autoComplete="off"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              maxLength={500}
              rows={3}
              placeholder="Add the evidence or reasoning behind this decision…"
              className="resize-y rounded-lg border border-[#D0D5DD] bg-white px-3 py-2 text-sm text-[#172554] outline-none transition-colors placeholder:text-[#98A2B3] focus-visible:ring-2 focus-visible:ring-indigo-500"
            />
            <span className="text-right text-xs font-normal text-[#98A2B3]">
              {note.length}/500
            </span>
          </label>
        </div>

        <footer className="border-t border-[#E9E7FF] bg-white px-5 py-4 sm:px-6">
          <p className="mb-3 text-xs text-[#667085]">
            Decision recorded as{" "}
            <span className="font-semibold text-[#475467]">
              {reviewerName.trim() || REVIEWER_DEFAULT}
            </span>
            .
          </p>
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:justify-end">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onRequestResolution("reject_link", note)}
              disabled={busy}
            >
              Reject candidate
            </Button>
            <Button
              type="button"
              variant="primary"
              size="sm"
              icon={
                busy ? (
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                ) : (
                  <UsersRound className="h-4 w-4" />
                )
              }
              onClick={() => onRequestResolution("create_profile", note)}
              disabled={busy}
            >
              Create separate profile
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="border-red-300 text-red-700 hover:bg-red-50"
              onClick={() => onRequestResolution("approve_link", note)}
              disabled={busy || !candidate || Boolean(conflict)}
              title={
                conflict
                  ? "Strong conflicts cannot be approved"
                  : candidate
                    ? "Requires confirmation"
                    : "No candidate is available to link"
              }
            >
              Approve link
            </Button>
          </div>
        </footer>
      </aside>

      {pendingAction === "approve_link" && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          <button
            type="button"
            aria-label="Cancel link approval"
            className="absolute inset-0 cursor-default bg-slate-950/30"
            onClick={onCancelApproval}
            disabled={busy}
          />
          <section
            className="relative w-full max-w-md rounded-2xl border border-[#E4E7EC] bg-white p-6 shadow-xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby="approve-link-title"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-50 text-red-700">
              <AlertTriangle className="h-5 w-5" aria-hidden="true" />
            </div>
            <h3
              id="approve-link-title"
              className="mt-4 text-lg font-semibold text-[#172554]"
            >
              Approve this identity link?
            </h3>
            <p className="mt-2 text-sm leading-6 text-[#667085]">
              This attaches the incoming record to{" "}
              {candidate?.display_name || "the suggested profile"} and
              reruns journey rules. Confirm only when the evidence supports the
              link.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={onCancelApproval}
                disabled={busy}
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="danger"
                onClick={() => onApprove(note)}
                disabled={busy}
                icon={
                  busy ? (
                    <LoaderCircle className="h-4 w-4 animate-spin" />
                  ) : undefined
                }
              >
                Approve & link
              </Button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}

function CaseRecord({
  label,
  title,
  channel,
  details,
}: {
  label: string;
  title: string;
  channel?: Channel | null;
  details: string[];
}) {
  return (
    <section className="rounded-xl border border-[#E4E7EC] bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-[#667085]">
          {label}
        </p>
        {channel && <ChannelBadge channel={channel} />}
      </div>
      <p className="mt-3 text-base font-semibold text-[#172554]">{title}</p>
      <ul className="mt-2 space-y-1 text-sm leading-5 text-[#667085]">
        {details.map((detail) => (
          <li key={detail}>{detail}</li>
        ))}
      </ul>
    </section>
  );
}
