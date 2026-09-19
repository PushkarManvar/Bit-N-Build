"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  CheckCircle2,
  CirclePlay,
  ClipboardCheck,
  Gauge,
  LoaderCircle,
  Play,
  RotateCcw,
  ShieldCheck,
  Timer,
} from "lucide-react";
import {
  getDashboardUpdates,
  getDemoRun,
  getProfiles,
  resetDemo,
  startDemo,
} from "@/lib/api";
import { ChannelBadge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { ErrorBanner } from "../ui/ErrorBanner";

interface StepDefinition {
  id: number;
  channel: "web" | "mobile_app" | "call_center" | "physical_store";
  title: string;
  description: string;
  expectedOutcome: string;
}

type DemoStatus = "idle" | "running" | "completed" | "failed";

const SCENARIO_STEPS: StepDefinition[] = [
  {
    id: 1,
    channel: "web",
    title: "Riya starts a return on the website",
    description:
      "An anonymous web event is captured with device DEV-17 and order ORD-204.",
    expectedOutcome: "Creates the baseline anonymous journey record.",
  },
  {
    id: 2,
    channel: "mobile_app",
    title: "Riya contacts support in the mobile app",
    description:
      "The app event supplies Riya’s email alongside the same device and order.",
    expectedOutcome:
      "Links the anonymous event using deterministic device evidence.",
  },
  {
    id: 3,
    channel: "call_center",
    title: "Riya calls about the refund",
    description:
      "A call-centre event contributes her verified phone and order reference.",
    expectedOutcome: "Links to Riya using a strong verified identifier.",
  },
  {
    id: 4,
    channel: "physical_store",
    title: "Riya requests a return in store",
    description:
      "The store return uses the same phone and ORD-204 without a refund completion.",
    expectedOutcome:
      "Creates the unresolved-refund and repeated-contact alerts.",
  },
  {
    id: 5,
    channel: "web",
    title: "Aarav starts an unrelated web session",
    description:
      "A separate visitor record is created for Aarav Patel with only weak name evidence.",
    expectedOutcome:
      "Creates a new profile; name similarity is not used to merge.",
  },
  {
    id: 6,
    channel: "mobile_app",
    title: "Aarav signs in with conflicting identifiers",
    description:
      "A distinct mobile identity reaches the system after the Riya journey is complete.",
    expectedOutcome:
      "Routes the ambiguity to the Review Queue for a human decision.",
  },
];

const STATUS_COPY: Record<DemoStatus, string> = {
  idle: "Ready",
  running: "Running",
  completed: "Complete",
  failed: "Needs attention",
};

function statusClasses(status: DemoStatus): string {
  if (status === "completed") return "border-teal-200 bg-teal-50 text-teal-800";
  if (status === "running")
    return "border-indigo-200 bg-indigo-50 text-indigo-800";
  if (status === "failed") return "border-red-200 bg-red-50 text-red-800";
  return "border-slate-200 bg-slate-50 text-slate-700";
}

export function DemoControllerView() {
  const router = useRouter();
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<DemoStatus>("idle");
  const [currentStep, setCurrentStep] = useState(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [intervalSeconds, setIntervalSeconds] = useState(1.5);
  const [showResetModal, setShowResetModal] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [resetSuccessMessage, setResetSuccessMessage] = useState<string | null>(
    null,
  );
  const [openAlerts, setOpenAlerts] = useState(0);
  const [pendingReviews, setPendingReviews] = useState(0);
  const [resolvedRiyaProfileId, setResolvedRiyaProfileId] = useState<
    string | null
  >(null);
  const pollingRef = useRef(false);

  const totalSteps = SCENARIO_STEPS.length;
  const progressPct = Math.min(
    100,
    Math.round((currentStep / totalSteps) * 100),
  );

  const refreshDashboardCounts = useCallback(async () => {
    const updates = await getDashboardUpdates();
    setOpenAlerts(updates.open_alerts);
    setPendingReviews(updates.pending_reviews);
  }, []);

  useEffect(() => {
    let mounted = true;

    const initialize = async () => {
      try {
        const updates = await getDashboardUpdates();
        if (!mounted) return;

        setOpenAlerts(updates.open_alerts);
        setPendingReviews(updates.pending_reviews);

        if (!updates.demo) return;

        setRunId(updates.demo.run_id);
        setCurrentStep(updates.demo.current_step);
        if (updates.demo.status === "running") setStatus("running");
        if (updates.demo.status === "completed") setStatus("completed");
        if (updates.demo.status === "failed") {
          setStatus("failed");
          setErrorMsg(
            updates.demo.error || "The demo stopped before it could finish.",
          );
        }
      } catch {
        // The page remains usable when the dashboard summary has not loaded yet.
      }
    };

    void initialize();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (status !== "running" || !runId) return;

    const timer = window.setInterval(async () => {
      if (pollingRef.current) return;
      pollingRef.current = true;

      try {
        const runData = await getDemoRun(runId);
        setCurrentStep(runData.current_step);

        if (runData.status === "completed") {
          setStatus("completed");
          try {
            const profiles = await getProfiles({
              page: 1,
              page_size: 5,
              search: "ORD-204",
            });
            if (profiles.items.length > 0) {
              setResolvedRiyaProfileId(profiles.items[0].profile_id);
            }
          } catch {
            // The explorer fallback still makes the completed journey reachable.
          }
        } else if (runData.status === "failed") {
          setStatus("failed");
          setErrorMsg(
            runData.error || "The demo stopped during a scenario step.",
          );
        }

        await refreshDashboardCounts();
      } catch (error) {
        if (error instanceof Error) {
          setErrorMsg(`Could not refresh the live run: ${error.message}`);
        }
      } finally {
        pollingRef.current = false;
      }
    }, 1_000);

    return () => window.clearInterval(timer);
  }, [refreshDashboardCounts, runId, status]);

  const handleStartDemo = async () => {
    if (status === "running") return;
    setErrorMsg(null);
    setResetSuccessMessage(null);
    setResolvedRiyaProfileId(null);

    try {
      const response = await startDemo(
        "unresolved_refund_riya",
        intervalSeconds,
      );
      setRunId(response.run_id);
      setStatus("running");
      setCurrentStep(response.current_step);
    } catch (error) {
      setErrorMsg(
        error instanceof Error
          ? error.message
          : "The demo scenario could not start.",
      );
    }
  };

  const handleConfirmReset = async () => {
    setIsResetting(true);
    setErrorMsg(null);

    try {
      const result = await resetDemo();
      setShowResetModal(false);
      setStatus("idle");
      setRunId(null);
      setCurrentStep(0);
      setResolvedRiyaProfileId(null);
      setResetSuccessMessage(
        `Demo workspace restored: ${Object.entries(result.loaded || {})
          .map(([key, value]) => `${value} ${key}`)
          .join(", ")}.`,
      );
      await refreshDashboardCounts();
    } catch (error) {
      setErrorMsg(
        error instanceof Error
          ? `Reset failed: ${error.message}`
          : "Reset failed.",
      );
    } finally {
      setIsResetting(false);
    }
  };

  const navigateToRiyaJourney = useCallback(async () => {
    if (resolvedRiyaProfileId) {
      router.push(`/customers/${encodeURIComponent(resolvedRiyaProfileId)}`);
      return;
    }

    try {
      const profiles = await getProfiles({
        page: 1,
        page_size: 5,
        search: "ORD-204",
      });
      if (profiles.items.length > 0) {
        router.push(
          `/customers/${encodeURIComponent(profiles.items[0].profile_id)}`,
        );
      } else {
        router.push("/customers?search=ORD-204");
      }
    } catch {
      router.push("/customers?search=ORD-204");
    }
  }, [resolvedRiyaProfileId, router]);

  return (
    <div className="mx-auto max-w-[1440px] space-y-6">
      <section className="flex flex-col gap-4 border-b border-[#E9E7FF] pb-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-balance text-3xl font-semibold tracking-tight text-[#172554]">
              Demo Controller
            </h1>
            <span className="rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-800">
              Internal demo tool
            </span>
          </div>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[#667085]">
            Run the deterministic refund journey that proves Riya’s identity
            link and Aarav’s safe route to human review.
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="md"
          icon={<RotateCcw className="h-4 w-4" />}
          onClick={() => setShowResetModal(true)}
          disabled={status === "running" || isResetting}
        >
          Reset demo
        </Button>
      </section>

      {errorMsg && (
        <ErrorBanner
          title="Demo controller notification"
          message={errorMsg}
          onRetry={() => void handleStartDemo()}
        />
      )}

      {resetSuccessMessage && (
        <div
          className="flex items-start gap-3 rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-800"
          role="status"
          aria-live="polite"
        >
          <CheckCircle2
            className="mt-0.5 h-5 w-5 shrink-0"
            aria-hidden="true"
          />
          <p>{resetSuccessMessage}</p>
        </div>
      )}

      <section className="overflow-hidden rounded-2xl border border-[#E4E7EC] bg-white shadow-sm">
        <div className="flex flex-col gap-6 p-5 lg:flex-row lg:items-center lg:justify-between lg:p-6">
          <div className="max-w-2xl">
            <div className="flex flex-wrap items-center gap-2">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700">
                <CirclePlay className="h-5 w-5" aria-hidden="true" />
              </span>
              <span
                className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${statusClasses(status)}`}
              >
                {STATUS_COPY[status]}
              </span>
            </div>
            <h2 className="mt-4 text-balance text-xl font-semibold text-[#172554]">
              Riya’s unresolved refund & Aarav review safety
            </h2>
            <p className="mt-2 text-sm leading-6 text-[#667085]">
              Six fixed events travel through the same intake, identity, alert,
              and review flow used by the operations console.
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div
              className="inline-flex rounded-lg border border-indigo-100 bg-indigo-50/70 p-1"
              aria-label="Playback speed"
            >
              {[
                { label: "1×", value: 1.5 },
                { label: "2×", value: 0.75 },
              ].map((speed) => (
                <button
                  key={speed.value}
                  type="button"
                  disabled={status === "running"}
                  onClick={() => setIntervalSeconds(speed.value)}
                  className={`rounded-md px-3 py-2 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50 ${
                    intervalSeconds === speed.value
                      ? "bg-white text-indigo-700 shadow-sm"
                      : "text-[#667085] hover:text-[#172554]"
                  }`}
                  aria-pressed={intervalSeconds === speed.value}
                >
                  {speed.label}{" "}
                  <span className="font-normal">({speed.value}s)</span>
                </button>
              ))}
            </div>
            <Button
              type="button"
              variant="primary"
              size="md"
              icon={
                status === "running" ? (
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )
              }
              onClick={() => void handleStartDemo()}
              disabled={status === "running"}
            >
              {status === "running"
                ? "Running scenario…"
                : status === "completed"
                  ? "Run again"
                  : "Run scenario"}
            </Button>
          </div>
        </div>

        <div className="border-t border-[#E9E7FF] bg-[#FAFAFF] px-5 py-4 lg:px-6">
          <div className="mb-2 flex items-center justify-between gap-3 text-xs font-medium text-[#475467]">
            <span>Scenario progress</span>
            <span className="tabular-nums">
              Step {currentStep} of {totalSteps} · {progressPct}%
            </span>
          </div>
          <div
            className="h-2 overflow-hidden rounded-full bg-indigo-100"
            role="progressbar"
            aria-label="Scenario progress"
            aria-valuemin={0}
            aria-valuemax={totalSteps}
            aria-valuenow={currentStep}
          >
            <div
              className={`h-full rounded-full transition-[width] duration-300 motion-reduce:transition-none ${status === "completed" ? "bg-teal-600" : "bg-indigo-600"}`}
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      </section>

      {status === "completed" && (
        <section className="flex flex-col gap-4 rounded-xl border border-teal-200 bg-teal-50 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <CheckCircle2
              className="mt-0.5 h-5 w-5 shrink-0 text-teal-700"
              aria-hidden="true"
            />
            <div>
              <h2 className="font-semibold text-teal-900">Scenario complete</h2>
              <p className="mt-1 text-sm text-teal-800">
                Riya’s refund journey is linked and the Aarav case is ready for
                a human review decision.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={() => void navigateToRiyaJourney()}
            >
              View Riya’s journey
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => router.push("/reviews")}
            >
              Open review queue
            </Button>
          </div>
        </section>
      )}

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.7fr)_minmax(18rem,0.8fr)]">
        <div className="overflow-hidden rounded-2xl border border-[#E4E7EC] bg-white shadow-sm">
          <div className="flex flex-col gap-2 border-b border-[#E9E7FF] px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-base font-semibold text-[#172554]">
                Deterministic execution steps
              </h2>
              <p className="mt-1 text-xs text-[#667085]">
                Each event has one expected, explainable outcome.
              </p>
            </div>
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
              {totalSteps} events
            </span>
          </div>

          <ol className="space-y-3 p-4 sm:p-5">
            {SCENARIO_STEPS.map((step) => {
              const isFinished = currentStep >= step.id;
              const isCurrent =
                status === "running" && currentStep === step.id - 1;
              const stepBadge = isFinished
                ? {
                    label: "Processed",
                    className: "border-teal-200 bg-teal-50 text-teal-800",
                  }
                : isCurrent
                  ? {
                      label: "In progress",
                      className:
                        "border-indigo-200 bg-indigo-50 text-indigo-800",
                    }
                  : {
                      label: "Not started",
                      className: "border-slate-200 bg-slate-50 text-slate-600",
                    };

              return (
                <li
                  key={step.id}
                  className={`rounded-xl border p-4 transition-colors ${
                    isCurrent
                      ? "border-indigo-300 bg-indigo-50/50"
                      : isFinished
                        ? "border-teal-200 bg-white"
                        : "border-[#E4E7EC] bg-[#FCFCFF]"
                  }`}
                >
                  <div className="flex gap-3">
                    <span
                      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${isFinished ? "bg-teal-600 text-white" : isCurrent ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"}`}
                    >
                      {step.id}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                        <div className="flex min-w-0 flex-wrap items-center gap-2">
                          <ChannelBadge channel={step.channel} />
                          <h3 className="text-sm font-semibold text-[#172554]">
                            {step.title}
                          </h3>
                        </div>
                        <span
                          className={`shrink-0 rounded-full border px-2 py-0.5 text-xs font-semibold ${stepBadge.className}`}
                        >
                          {stepBadge.label}
                        </span>
                      </div>
                      <p className="mt-2 text-sm leading-5 text-[#475467]">
                        {step.description}
                      </p>
                      <p className="mt-2 rounded-lg bg-slate-50 px-3 py-2 text-xs leading-5 text-[#667085]">
                        <span className="font-semibold text-[#475467]">
                          Expected outcome:
                        </span>
                        {step.expectedOutcome}
                      </p>
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        </div>

        <aside className="h-fit rounded-2xl border border-[#E4E7EC] bg-white p-5 shadow-sm xl:sticky xl:top-24">
          <div className="flex items-center justify-between border-b border-[#E9E7FF] pb-4">
            <div>
              <h2 className="text-base font-semibold text-[#172554]">
                Live run telemetry
              </h2>
              <p className="mt-1 text-xs text-[#667085]">
                Updates while the scenario is running.
              </p>
            </div>
            <Gauge className="h-5 w-5 text-indigo-600" aria-hidden="true" />
          </div>

          <dl className="mt-4 grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-indigo-100 bg-indigo-50/70 p-3">
              <dt className="text-xs font-medium text-[#667085]">
                Events dispatched
              </dt>
              <dd className="mt-1 tabular-nums text-2xl font-semibold text-indigo-800">
                {currentStep}
                <span className="text-base text-indigo-500">/{totalSteps}</span>
              </dd>
            </div>
            <div className="rounded-xl border border-teal-100 bg-teal-50/70 p-3">
              <dt className="text-xs font-medium text-[#667085]">
                Scenario state
              </dt>
              <dd className="mt-1 text-base font-semibold text-teal-800">
                {STATUS_COPY[status]}
              </dd>
            </div>
            <div className="rounded-xl border border-red-100 bg-red-50/70 p-3">
              <dt className="text-xs font-medium text-[#667085]">
                Active alerts
              </dt>
              <dd className="mt-1 tabular-nums text-2xl font-semibold text-red-700">
                {openAlerts}
              </dd>
            </div>
            <div className="rounded-xl border border-amber-100 bg-amber-50/70 p-3">
              <dt className="text-xs font-medium text-[#667085]">
                Pending reviews
              </dt>
              <dd className="mt-1 tabular-nums text-2xl font-semibold text-amber-800">
                {pendingReviews}
              </dd>
            </div>
          </dl>

          <div className="mt-5 rounded-xl border border-indigo-100 bg-[#F7F6FF] p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-[#312E81]">
              <ShieldCheck className="h-4 w-4" aria-hidden="true" />
              What this proves
            </div>
            <ul className="mt-3 space-y-2 text-xs leading-5 text-[#475467]">
              <li className="flex gap-2">
                <CheckCircle2
                  className="mt-0.5 h-3.5 w-3.5 shrink-0 text-teal-700"
                  aria-hidden="true"
                />
                Strong identifiers link Riya’s events across channels.
              </li>
              <li className="flex gap-2">
                <AlertTriangle
                  className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-700"
                  aria-hidden="true"
                />
                A missing refund completion surfaces an operational alert.
              </li>
              <li className="flex gap-2">
                <ClipboardCheck
                  className="mt-0.5 h-3.5 w-3.5 shrink-0 text-indigo-700"
                  aria-hidden="true"
                />
                Aarav remains a review decision; a name is never enough to
                merge.
              </li>
            </ul>
          </div>

          <div className="mt-5 flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-xs text-[#667085]">
            <Timer
              className="h-4 w-4 shrink-0 text-slate-500"
              aria-hidden="true"
            />
            Polling runs every second only while the demo is active.
          </div>
        </aside>
      </section>

      {showResetModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 p-4 overscroll-contain">
          <section
            className="w-full max-w-md rounded-2xl border border-[#E4E7EC] bg-white p-6 shadow-xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby="reset-modal-title"
            aria-describedby="reset-modal-description"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-50 text-red-700">
              <RotateCcw className="h-5 w-5" aria-hidden="true" />
            </div>
            <h2
              id="reset-modal-title"
              className="mt-4 text-lg font-semibold text-[#172554]"
            >
              Reset demo workspace?
            </h2>
            <p
              id="reset-modal-description"
              className="mt-2 text-sm leading-6 text-[#667085]"
            >
              This clears demo events, active alerts, and match decisions, then
              restores the clean synthetic baseline.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowResetModal(false)}
                disabled={isResetting}
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="danger"
                icon={
                  isResetting ? (
                    <LoaderCircle className="h-4 w-4 animate-spin" />
                  ) : (
                    <RotateCcw className="h-4 w-4" />
                  )
                }
                onClick={() => void handleConfirmReset()}
                disabled={isResetting}
              >
                {isResetting ? "Resetting…" : "Reset demo"}
              </Button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
