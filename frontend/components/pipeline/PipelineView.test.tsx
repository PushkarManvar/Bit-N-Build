/**
 * Pipeline polling behavior tests using fake timers (docs/16 Task 12).
 * Verifies: interval firing, no overlapping polls, burst draining,
 * degraded banner, hidden-tab pause, and authoritative count refresh.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import { ApiClientError } from "@/lib/api";
import { PipelineView } from "@/components/pipeline/PipelineView";

const mocks = vi.hoisted(() => ({
  overview: vi.fn(),
  updates: vi.fn(),
  events: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    getPipelineOverview: mocks.overview,
    getPipelineUpdates: mocks.updates,
    getPipelineEvents: mocks.events,
  };
});

function overviewFixture(over: Record<string, unknown> = {}) {
  return {
    as_of: "2026-09-20T00:00:00Z",
    stages: {
      raw_accepted: 3,
      normalization_succeeded: 3,
      normalization_failed: 0,
      identity_decided: 3,
      profile_linked: 2,
      review_required: 1,
    },
    channels: {
      web: { raw: 1, normalized: 1, failed: 0 },
      mobile_app: { raw: 1, normalized: 1, failed: 0 },
      call_center: { raw: 1, normalized: 1, failed: 0 },
      physical_store: { raw: 0, normalized: 0, failed: 0 },
    },
    events: [],
    next_cursor: null,
    poll_cursor: "cursor-0",
    duplicate_attempts: null,
    duplicate_tracking_supported: false,
    ...over,
  };
}

function updatesFixture(over: Record<string, unknown> = {}) {
  return {
    as_of: "2026-09-20T00:00:01Z",
    stages: overviewFixture().stages,
    channels: overviewFixture().channels,
    events: [],
    next_cursor: "cursor-0",
    upper_bound_cursor: "upper-0",
    has_more: false,
    ...over,
  };
}

function eventRow(id: string) {
  return {
    raw_event_id: id,
    canonical_event_id: null,
    source_event_id: `WEB-${id}`,
    channel: "web",
    event_type: "product_viewed",
    event_summary: { title: "Product viewed", detail: null, kind: "product_view" },
    has_order_reference: false,
    occurred_at: "2026-09-20T00:00:00Z",
    received_at: "2026-09-20T00:00:00Z",
    processed_at: null,
    processing_status: "normalized",
    processing_error_code: null,
    profile_id: null,
    identity_outcome: "new_profile",
    identity_score: 0,
    needs_review: false,
  };
}

describe("PipelineView polling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mocks.overview.mockReset();
    mocks.updates.mockReset();
    mocks.events.mockReset();
    mocks.overview.mockResolvedValue(overviewFixture());
    mocks.updates.mockResolvedValue(updatesFixture());
    mocks.events.mockResolvedValue({ items: [], total: 0, next_cursor: null });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("polls for updates on the interval", async () => {
    render(<PipelineView />);
    await act(async () => {
      await Promise.resolve();
    });
    expect(mocks.updates).not.toHaveBeenCalled();

    await act(async () => {
      vi.advanceTimersByTime(5_000);
      await Promise.resolve();
    });
    expect(mocks.updates).toHaveBeenCalledTimes(1);
    expect(mocks.updates).toHaveBeenCalledWith(expect.objectContaining({ cursor: "cursor-0" }));
  });

  it("does not start an overlapping poll while one is in flight", async () => {
    let resolveUpdates: (value: unknown) => void;
    mocks.updates.mockReturnValue(
      new Promise((resolve) => {
        resolveUpdates = resolve;
      }),
    );
    render(<PipelineView />);
    await act(async () => {
      await Promise.resolve();
    });

    await act(async () => {
      vi.advanceTimersByTime(5_000);
      await Promise.resolve();
    });
    expect(mocks.updates).toHaveBeenCalledTimes(1);

    await act(async () => {
      vi.advanceTimersByTime(10_000);
      await Promise.resolve();
    });
    expect(mocks.updates).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolveUpdates!(updatesFixture());
      await Promise.resolve();
    });
  });

  it("drains a burst across has_more pages without loss or duplicates", async () => {
    mocks.updates
      .mockResolvedValueOnce(
        updatesFixture({
          events: [eventRow("e1"), eventRow("e2")],
          has_more: true,
          next_cursor: "cursor-1",
        }),
      )
      .mockResolvedValueOnce(
        updatesFixture({
          events: [eventRow("e3")],
          has_more: false,
          next_cursor: "cursor-2",
        }),
      );

    render(<PipelineView />);
    await act(async () => {
      await Promise.resolve();
    });
    await act(async () => {
      vi.advanceTimersByTime(5_000);
      await Promise.resolve();
    });

    expect(mocks.updates).toHaveBeenCalledTimes(2);
    expect(mocks.updates.mock.calls[0][0].cursor).toBe("cursor-0");
    expect(mocks.updates.mock.calls[1][0].cursor).toBe("cursor-1");
    const rows = screen.getAllByText(/WEB-e/);
    expect(rows).toHaveLength(3);
  });

  it("shows a degraded banner after repeated poll failures while keeping the snapshot", async () => {
    mocks.updates.mockRejectedValue(
      new ApiClientError(500, {
        code: "PIPELINE_POLL_FAILED",
        message: "updates unavailable",
        stage: "pipeline",
      }),
    );

    render(<PipelineView />);
    await act(async () => {
      await Promise.resolve();
    });

    for (let i = 0; i < 3; i++) {
      await act(async () => {
        vi.advanceTimersByTime(5_000);
        await Promise.resolve();
      });
    }

    expect(screen.getByText(/Live updates are delayed/)).toBeInTheDocument();
    expect(screen.getByText("Raw accepted")).toBeInTheDocument();
  });

  it("pauses polling while the tab is hidden", async () => {
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "hidden",
    });
    render(<PipelineView />);
    await act(async () => {
      await Promise.resolve();
    });

    await act(async () => {
      vi.advanceTimersByTime(15_000);
      await Promise.resolve();
    });
    expect(mocks.updates).not.toHaveBeenCalled();

    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "visible",
    });
  });

  it("refreshes authoritative counts after a successful poll", async () => {
    mocks.updates.mockResolvedValue(
      updatesFixture({
        stages: {
          raw_accepted: 5,
          normalization_succeeded: 5,
          normalization_failed: 0,
          identity_decided: 5,
          profile_linked: 4,
          review_required: 1,
        },
      }),
    );

    render(<PipelineView />);
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getAllByText("3")[0]).toBeInTheDocument();

    await act(async () => {
      vi.advanceTimersByTime(5_000);
      await Promise.resolve();
    });
    expect(screen.getAllByText("5")[0]).toBeInTheDocument();
  });
});