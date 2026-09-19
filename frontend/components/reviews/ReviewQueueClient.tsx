"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  getReviews,
  resolveReview,
  ApiClientError,
} from "@/lib/api";
import type { ReviewItem } from "@/lib/types";
import { formatDateTime } from "@/lib/formatters";
import { getEventTypeLabel } from "@/lib/presenters";
import { ChannelBadge } from "../ui/Badge";
import { Panel } from "../ui/Panel";
import { Button } from "../ui/Button";
import { EmptyState } from "../ui/EmptyState";
import { ErrorState } from "../ui/ErrorState";
import { SkeletonBlock } from "../ui/SkeletonBlock";

const REVIEWER_DEFAULT = "Demo Reviewer";

export function ReviewQueueClient() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewerName, setReviewerName] = useState(REVIEWER_DEFAULT);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchReviews = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getReviews();
      setItems(response.items);
    } catch (err) {
      setError(
        err instanceof ApiClientError
          ? err.message
          : "Review queue could not be loaded."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchReviews();
  }, [fetchReviews]);

  const handleResolve = async (
    decisionId: string,
    action: "approve_link" | "reject_link" | "create_profile"
  ) => {
    setBusyId(decisionId);
    setActionMessage(null);
    try {
      const item = items.find((i) => i.match_decision_id === decisionId);
      const result = await resolveReview(decisionId, {
        action,
        selected_profile_id:
          action === "approve_link" && item?.best_candidate
            ? item.best_candidate.profile_id
            : null,
        reviewer_name: reviewerName.trim() || REVIEWER_DEFAULT,
        note: action === "approve_link" ? "Approved by reviewer." : "Kept separate by reviewer.",
      });
      setItems((prev) => prev.filter((i) => i.match_decision_id !== decisionId));
      setActionMessage(
        `${result.action} resolved for ${result.match_decision_id.slice(0, 8)}.`
      );
    } catch (err) {
      setActionMessage(
        err instanceof ApiClientError ? err.message : "Resolution failed."
      );
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-6">
      <Panel>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-[#172554] tracking-tight">
              Review Queue
            </h1>
            <p className="text-sm text-[#667085] mt-1">
              Pending ambiguous identity decisions requiring human resolution
            </p>
          </div>
          <label className="flex flex-col text-sm text-[#667085] gap-1">
            <span>Reviewer name</span>
            <input
              type="text"
              value={reviewerName}
              onChange={(event) => setReviewerName(event.target.value)}
              className="border border-[#D0D5DD] rounded-lg px-3 py-2 text-[#172554] bg-white w-56"
              aria-label="Reviewer name"
            />
          </label>
        </div>

        {actionMessage && (
          <p className="mt-4 text-sm text-[#2563EB] font-medium" role="status">
            {actionMessage}
          </p>
        )}
      </Panel>

      {loading && (
        <div className="space-y-3" aria-label="Loading reviews">
          <SkeletonBlock className="h-[120px]" />
          <SkeletonBlock className="h-[120px]" />
        </div>
      )}

      {!loading && error && <ErrorState message={error} onRetry={fetchReviews} />}

      {!loading && !error && items.length === 0 && (
        <EmptyState
          title="No pending reviews"
          description="Every identity decision has been resolved. New ambiguous matches will appear here for human review."
        />
      )}

      {!loading && !error && items.length > 0 && (
        <ul className="space-y-4">
          {items.map((item) => (
            <li key={item.match_decision_id}>
              <ReviewCard
                item={item}
                busy={busyId === item.match_decision_id}
                onResolve={(action) => handleResolve(item.match_decision_id, action)}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ReviewCard({
  item,
  busy,
  onResolve,
}: {
  item: ReviewItem;
  busy: boolean;
  onResolve: (action: "approve_link" | "reject_link" | "create_profile") => void;
}) {
  return (
    <Panel>
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            {item.event.channel && <ChannelBadge channel={item.event.channel} />}
            <span className="text-sm font-semibold text-[#172554]">
              {getEventTypeLabel(item.event.event_type)}
            </span>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
              Needs review
            </span>
          </div>
          <span className="text-xs text-[#667085] tabular-nums">
            {formatDateTime(item.event.occurred_at)}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-[#667085] mb-1">
              Customer
            </p>
            <p className="font-medium text-[#172554]">
              {item.event.customer_name || "Unknown"}
            </p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-[#667085] mb-1">
              Best candidate
            </p>
            {item.best_candidate ? (
              <>
                <p className="font-medium text-[#172554]">
                  {item.best_candidate.display_name || "Profile"}
                </p>
                <p className="text-xs text-[#667085]">
                  {item.best_candidate.profile_id.slice(0, 8)} · score{" "}
                  {item.best_candidate.score}
                </p>
              </>
            ) : (
              <p className="text-[#667085]">No candidate</p>
            )}
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-[#667085] mb-1">
              Missing strong identifiers
            </p>
            <p className="text-[#667085]">
              {item.missing_strong_identifiers.length
                ? item.missing_strong_identifiers.join(", ")
                : "None"}
            </p>
          </div>
        </div>

        {item.evidence.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-[#667085] mb-1">
              Evidence
            </p>
            <ul className="list-disc pl-5 text-sm text-[#344054]">
              {item.evidence.map((evidence, index) => (
                <li key={index}>{evidence}</li>
              ))}
            </ul>
          </div>
        )}

        {item.conflicts.length > 0 && (
          <div className="rounded-lg bg-rose-50 border border-rose-200 p-3">
            <p className="text-xs font-semibold text-rose-700 mb-1">
              Conflicting evidence
            </p>
            <p className="text-sm text-rose-700">{item.conflicts[0].message}</p>
          </div>
        )}

        {item.reason && (
          <p className="text-sm text-[#667085] italic">{item.reason}</p>
        )}

        <div className="flex flex-wrap gap-2 border-t border-[#E4E7EC] pt-4">
          <Button
            variant="primary"
            disabled={busy || !item.best_candidate}
            onClick={() => onResolve("approve_link")}
          >
            Approve link
          </Button>
          <Button
            variant="outline"
            disabled={busy}
            onClick={() => onResolve("reject_link")}
          >
            Reject link
          </Button>
          <Button
            variant="outline"
            disabled={busy}
            onClick={() => onResolve("create_profile")}
          >
            Create separate profile
          </Button>
        </div>
      </div>
    </Panel>
  );
}