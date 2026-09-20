/**
 * Public UI/API seam tests for the Journey Intelligence operations dossier.
 * The deterministic radar must remain the useful, visible product when the
 * optional AI wording endpoint is unavailable.
 */
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiClientError } from "@/lib/api";
import { OperationsDossierView } from "@/components/journey-intelligence/OperationsDossierView";

const mocks = vi.hoisted(() => ({
  radar: vi.fn(),
  brief: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    getFrictionRadar: mocks.radar,
    generateFrictionRadarBrief: mocks.brief,
  };
});

function radarFixture() {
  return {
    as_of: "2026-09-20T12:00:00Z",
    score_version: "friction_v1" as const,
    score_max: 60,
    summary: {
      attributable_open_refunds: 2,
      unattributed_open_refunds: 1,
      critical: 1,
      elevated: 1,
      watch: 0,
    },
    journeys: [
      {
        alert_id: "alert-riya",
        profile_id: "profile-riya",
        display_name: "Riya Shah",
        order_id: "ORD-204",
        friction_score: 57,
        band: "critical" as const,
        unresolved_age_days: 5,
        distinct_channel_count: 3,
        support_contact_count: 3,
        has_open_repeat_contact_alert: true,
        pending_candidate_review_count: 1,
        components: {
          unresolved_age_points: 20,
          channel_points: 9,
          support_contact_points: 12,
          repeat_contact_points: 10,
          pending_candidate_review_points: 6,
        },
      },
      {
        alert_id: "alert-vivaan",
        profile_id: "profile-vivaan",
        display_name: "Vivaan Reddy",
        order_id: "ORD-301",
        friction_score: 36,
        band: "elevated" as const,
        unresolved_age_days: 4,
        distinct_channel_count: 1,
        support_contact_count: 2,
        has_open_repeat_contact_alert: false,
        pending_candidate_review_count: 0,
        components: {
          unresolved_age_points: 16,
          channel_points: 3,
          support_contact_points: 8,
          repeat_contact_points: 0,
          pending_candidate_review_points: 0,
        },
      },
    ],
    unresolved_age_distribution: [
      { bucket: "1–3 days", count: 0 },
      { bucket: "4–7 days", count: 2 },
    ],
    support_contact_channels: [{ channel: "call_center" as const, count: 3, share_percent: 100 }],
  };
}

describe("OperationsDossierView", () => {
  beforeEach(() => {
    mocks.radar.mockReset();
    mocks.brief.mockReset();
    mocks.radar.mockResolvedValue(radarFixture());
  });

  it("keeps the deterministic dossier visible when optional AI wording fails", async () => {
    mocks.brief.mockRejectedValue(
      new ApiClientError(503, {
        code: "AI_BRIEF_UNAVAILABLE",
        message: "AI is temporarily unavailable.",
        stage: "ai_brief",
      })
    );

    render(<OperationsDossierView />);

    await screen.findByRole("heading", { name: "Journey Friction Radar" });
    fireEvent.click(screen.getByRole("button", { name: "Generate brief" }));

    await screen.findByText(/The facts remain available/);
    expect(screen.getByLabelText("Priority case dossier")).toHaveTextContent("Riya Shah");
    expect(screen.getByRole("heading", { name: "Ranked open refund journeys" })).toBeInTheDocument();
    expect(screen.getByText("Evidence and action")).toBeInTheDocument();
  });

  it("renders a validated brief separately and focuses its stated case", async () => {
    mocks.brief.mockResolvedValue({
      headline: "Inspect Vivaan’s unresolved refund next",
      summary: "The unresolved age is the strongest verified signal for this journey.",
      focus_alert_id: "alert-vivaan",
      highlighted_signal: "unresolved_age",
      provider: "google",
      model: "gemini-3.6-flash",
      generated_at: "2026-09-20T12:01:00Z",
      cached: false,
    });

    render(<OperationsDossierView />);

    await screen.findByRole("heading", { name: "Journey Friction Radar" });
    fireEvent.click(screen.getByRole("button", { name: "Generate brief" }));

    await screen.findByText("Inspect Vivaan’s unresolved refund next");
    const priorityCase = screen.getByLabelText("Priority case dossier");
    expect(within(priorityCase).getByRole("heading", { name: "Vivaan Reddy" })).toBeInTheDocument();
    expect(screen.getByText(/Highlights unresolved age · google \/ gemini-3\.6-flash/)).toBeInTheDocument();
    await waitFor(() => expect(mocks.brief).toHaveBeenCalledTimes(1));
  });
});
