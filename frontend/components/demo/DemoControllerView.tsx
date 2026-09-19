"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  getDashboardUpdates,
  getDemoRun,
  getProfiles,
  resetDemo,
  startDemo,
} from "@/lib/api";
import { ChannelBadge } from "../ui/Badge";
import { ErrorBanner } from "../ui/ErrorBanner";
import { MetricCard } from "../ui/MetricCard";

interface StepDefinition {
  id: number;
  channel: "web" | "mobile_app" | "call_center" | "physical_store";
  title: string;
  description: string;
  expectedOutcome: string;
}

const SCENARIO_STEPS: StepDefinition[] = [
  {
    id: 1,
    channel: "web",
    title: "1. Web Product View",
    description: "Riya Shah views product with device DEV-17 and order ORD-204.",
    expectedOutcome: "Creates baseline web session record",
  },
  {
    id: 2,
    channel: "mobile_app",
    title: "2. Mobile Support Contact",
    description: "Riya contacts support via app with email and device DEV-17.",
    expectedOutcome: "Deterministic match via shared device_id bridge (auto_linked)",
  },
  {
    id: 3,
    channel: "call_center",
    title: "3. Call Centre Escalation",
    description: "Riya calls support using phone +91-98765-43210 and email.",
    expectedOutcome: "Deterministic match via verified email (auto_linked)",
  },
  {
    id: 4,
    channel: "physical_store",
    title: "4. Store Return Request",
    description: "In-store return requested for order ORD-204 with phone.",
    expectedOutcome: "Linked via phone; triggers Unresolved Refund & Repeat Contact alerts",
  },
  {
    id: 5,
    channel: "web",
    title: "5. Aarav Web Session",
    description: "Anonymous web product view by Aarav Patel in Mumbai.",
    expectedOutcome: "New profile created; weak name similarity ignored",
  },
  {
    id: 6,
    channel: "mobile_app",
    title: "6. Aarav Mobile Login",
    description: "Aarav logs into mobile app with distinct email and device DEV-701.",
    expectedOutcome: "Dispatched to Review Queue (review_required, safe non-merge)",
  },
];

export function DemoControllerView() {
  const router = useRouter();

  // Run states
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "running" | "completed" | "failed">("idle");
  const [currentStep, setCurrentStep] = useState<number>(0);
  const totalSteps = 6;
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Settings
  const [intervalSeconds, setIntervalSeconds] = useState<number>(1.5);
  const [showResetModal, setShowResetModal] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const [resetSuccessMessage, setResetSuccessMessage] = useState<string | null>(null);

  // Live Metrics
  const [openAlerts, setOpenAlerts] = useState<number>(0);
  const [pendingReviews, setPendingReviews] = useState<number>(0);
  const [resolvedRiyaProfileId, setResolvedRiyaProfileId] = useState<string | null>(null);

  // Polling management
  const pollingRef = useRef<boolean>(false);

  // Sync state on load from dashboard updates
  useEffect(() => {
    let mounted = true;
    async function initCheck() {
      try {
        const updates = await getDashboardUpdates();
        if (!mounted) return;
        if (typeof updates.open_alerts === "number") setOpenAlerts(updates.open_alerts);
        if (typeof updates.pending_reviews === "number") setPendingReviews(updates.pending_reviews);

        if (updates.demo) {
          setRunId(updates.demo.run_id);
          setCurrentStep(updates.demo.current_step);
          if (updates.demo.status === "running") {
            setStatus("running");
          } else if (updates.demo.status === "completed") {
            setStatus("completed");
          } else if (updates.demo.status === "failed") {
            setStatus("failed");
            setErrorMsg(updates.demo.error || "Demo scenario failed");
          }
        }
      } catch {
        // Fallback to idle
      }
    }
    initCheck();
    return () => {
      mounted = false;
    };
  }, []);

  // Poll status lazily while running
  useEffect(() => {
    if (status !== "running" || !runId) return;

    const timer = setInterval(async () => {
      if (pollingRef.current) return;
      pollingRef.current = true;

      try {
        const runData = await getDemoRun(runId);
        setCurrentStep(runData.current_step);

        if (runData.status === "completed") {
          setStatus("completed");
          // Fetch Riya profile ID dynamically via ORD-204 search
          try {
            const profilesRes = await getProfiles({ page: 1, page_size: 5, search: "ORD-204" });
            if (profilesRes.items && profilesRes.items.length > 0) {
              setResolvedRiyaProfileId(profilesRes.items[0].profile_id);
            }
          } catch {
            // Non-blocking
          }
        } else if (runData.status === "failed") {
          setStatus("failed");
          setErrorMsg(runData.error || "Execution failed during scenario step");
        }

        // Also update live counters
        const updates = await getDashboardUpdates();
        if (typeof updates.open_alerts === "number") setOpenAlerts(updates.open_alerts);
        if (typeof updates.pending_reviews === "number") setPendingReviews(updates.pending_reviews);
      } catch (err: unknown) {
        if (err instanceof Error) {
          setErrorMsg(`Polling error: ${err.message}`);
        }
      } finally {
        pollingRef.current = false;
      }
    }, 1000);

    return () => {
      clearInterval(timer);
    };
  }, [status, runId]);

  // Actions
  const handleStartDemo = async () => {
    if (status === "running") return;
    setErrorMsg(null);
    setResetSuccessMessage(null);
    setResolvedRiyaProfileId(null);

    try {
      const response = await startDemo("unresolved_refund_riya", intervalSeconds);

      setRunId(response.run_id);
      setStatus("running");
      setCurrentStep(response.current_step);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMsg(err.message || "Failed to start demo scenario");
      } else {
        setErrorMsg("Failed to start demo scenario");
      }
    }
  };

  const handleConfirmReset = async () => {
    setIsResetting(true);
    setErrorMsg(null);
    try {
      const res = await resetDemo();
      setShowResetModal(false);
      setStatus("idle");
      setRunId(null);
      setCurrentStep(0);
      setResolvedRiyaProfileId(null);
      setResetSuccessMessage(`Sandbox restored successfully. (${Object.entries(res.loaded || {}).map(([k, v]) => `${v} ${k}`).join(", ")})`);

      // Refresh dashboard stats
      const updates = await getDashboardUpdates();
      if (typeof updates.open_alerts === "number") setOpenAlerts(updates.open_alerts);
      if (typeof updates.pending_reviews === "number") setPendingReviews(updates.pending_reviews);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMsg(`Reset failed: ${err.message}`);
      } else {
        setErrorMsg("Reset failed");
      }
    } finally {
      setIsResetting(false);
    }
  };

  const navigateToRiyaJourney = useCallback(async () => {
    if (resolvedRiyaProfileId) {
      router.push(`/customers/${encodeURIComponent(resolvedRiyaProfileId)}`);
    } else {
      try {
        const res = await getProfiles({ page: 1, page_size: 5, search: "ORD-204" });
        if (res.items && res.items.length > 0) {
          router.push(`/customers/${encodeURIComponent(res.items[0].profile_id)}`);
        } else {
          router.push("/customers?search=ORD-204");
        }
      } catch {
        router.push("/customers?search=ORD-204");
      }
    }
  }, [resolvedRiyaProfileId, router]);

  const progressPct = Math.min(100, Math.round((currentStep / totalSteps) * 100));

  return (
    <div>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: "1.5rem",
          flexWrap: "wrap",
          gap: "1rem",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <h1 style={{ fontSize: "24px", fontWeight: 700, color: "var(--color-heading)" }}>
              Demo Controller
            </h1>
            <span
              className="badge"
              style={{ backgroundColor: "#fef3c7", color: "#92400e", border: "1px solid #fde68a" }}
            >
              Internal Presenter Sandbox
            </span>
          </div>
          <p style={{ color: "var(--color-secondary)", fontSize: "14px", marginTop: "2px" }}>
            Deterministic 6-step cross-channel scenario proving Riya Shah (ORD-204) identity resolution and Aarav Patel review safety.
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <button
            type="button"
            className="btn btn-danger btn-sm"
            onClick={() => setShowResetModal(true)}
            disabled={status === "running" || isResetting}
          >
            ?? Reset Sandbox
          </button>
        </div>
      </div>

      {/* Notifications */}
      {errorMsg && <ErrorBanner title="Demo Controller Notification" message={errorMsg} />}

      {resetSuccessMessage && (
        <div
          style={{
            padding: "0.875rem 1.25rem",
            backgroundColor: "var(--color-success-subtle)",
            border: "1px solid var(--color-success-border)",
            borderRadius: "var(--radius-md)",
            color: "var(--color-success)",
            fontWeight: 500,
            marginBottom: "1.5rem",
          }}
        >
          ? {resetSuccessMessage}
        </div>
      )}

      {/* -- Control Bar & Scenario Stats ------------------------------------ */}
      <div className="metrics-grid">
        <MetricCard
          label="Scenario Step"
          value={`${currentStep} / ${totalSteps}`}
          sub={status === "running" ? "Ingesting events..." : status === "completed" ? "All steps finished" : "Ready to start"}
        />
        <MetricCard
          label="Active Alerts"
          value={openAlerts}
          sub="Unresolved refunds detected"
        />
        <MetricCard
          label="Review Queue"
          value={pendingReviews}
          sub="Pending human review"
        />
        <MetricCard
          label="Scenario Status"
          value={status === "running" ? "RUNNING" : status === "completed" ? "COMPLETED" : status === "failed" ? "FAILED" : "IDLE"}
          sub={`Playback interval: ${intervalSeconds}s`}
        />
      </div>

      {/* -- Action Runner Card ---------------------------------------------- */}
      <div className="panel-card" style={{ marginBottom: "1.5rem" }}>
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Scenario Runner: `unresolved_refund_riya`</h2>
            <span style={{ fontSize: "12px", color: "var(--color-secondary)" }}>
              Deterministic cross-channel timeline � No probabilistic LLM hallucination
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            {/* Speed Selector */}
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span style={{ fontSize: "12px", color: "var(--color-secondary)", fontWeight: 500 }}>
                Playback Speed:
              </span>
              <div style={{ display: "flex", gap: "2px", background: "var(--color-card-subtle)", padding: "2px", borderRadius: "var(--radius-sm)" }}>
                {[
                  { label: "1x (1.5s)", val: 1.5 },
                  { label: "2x (0.75s)", val: 0.75 },
                ].map((speed) => (
                  <button
                    key={speed.val}
                    type="button"
                    disabled={status === "running"}
                    onClick={() => setIntervalSeconds(speed.val)}
                    style={{
                      border: "none",
                      background: intervalSeconds === speed.val ? "#ffffff" : "transparent",
                      color: intervalSeconds === speed.val ? "var(--color-heading)" : "var(--color-secondary)",
                      fontWeight: intervalSeconds === speed.val ? 600 : 400,
                      fontSize: "12px",
                      padding: "4px 8px",
                      borderRadius: "4px",
                      cursor: status === "running" ? "not-allowed" : "pointer",
                      boxShadow: intervalSeconds === speed.val ? "var(--shadow-sm)" : "none",
                    }}
                  >
                    {speed.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Start / Run Button */}
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleStartDemo}
              disabled={status === "running"}
            >
              {status === "running" ? "? Running Scenario..." : status === "completed" ? "?? Run Again" : "? Start Scenario"}
            </button>
          </div>
        </div>

        {/* Progress Bar */}
        <div style={{ margin: "1rem 0 0.5rem 0" }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px", fontWeight: 600, color: "var(--color-heading)" }}>
            <span>Progress: {progressPct}%</span>
            <span>Step {currentStep} of {totalSteps}</span>
          </div>
          <div style={{ height: "8px", width: "100%", backgroundColor: "#e2e8f0", borderRadius: "var(--radius-full)", overflow: "hidden" }}>
            <div
              style={{
                height: "100%",
                width: `${progressPct}%`,
                backgroundColor: status === "completed" ? "var(--color-success)" : "var(--color-primary)",
                transition: "width 0.3s ease-in-out",
              }}
            />
          </div>
        </div>

        {/* Completion Actions Banner */}
        {status === "completed" && (
          <div
            style={{
              marginTop: "1.25rem",
              padding: "1rem 1.25rem",
              backgroundColor: "var(--color-success-subtle)",
              border: "1px solid var(--color-success-border)",
              borderRadius: "var(--radius-md)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: "1rem",
            }}
          >
            <div>
              <div style={{ fontWeight: 700, color: "var(--color-success)", fontSize: "14px" }}>
                ?? Scenario Complete: Riya Shah Resolved & Aarav Safely Routed
              </div>
              <p style={{ fontSize: "13px", color: "var(--color-body)", marginTop: "2px" }}>
                All 6 events processed. 2 broken-refund alerts created for ORD-204, and Aarav Patel placed in Review Queue.
              </p>
            </div>

            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={navigateToRiyaJourney}
              >
                Open Riya Shah Journey ?
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => router.push("/reviews")}
              >
                Review Queue ({pendingReviews}) ?
              </button>
            </div>
          </div>
        )}
      </div>

      {/* -- 6-Step Execution Timeline --------------------------------------- */}
      <div className="panel-card">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Deterministic Scenario Flow</h2>
            <span style={{ fontSize: "12px", color: "var(--color-secondary)" }}>
              Step-by-step identity resolution and alert assertion
            </span>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {SCENARIO_STEPS.map((step) => {
            const isFinished = currentStep >= step.id;
            const isCurrent = status === "running" && currentStep === step.id - 1;

            let statusBadge = (
              <span className="badge" style={{ backgroundColor: "#f1f5f9", color: "#64748b" }}>
                Pending
              </span>
            );

            if (isFinished) {
              statusBadge = (
                <span className="badge" style={{ backgroundColor: "var(--color-success-subtle)", color: "var(--color-success)", border: "1px solid var(--color-success-border)" }}>
                  ? Completed
                </span>
              );
            } else if (isCurrent) {
              statusBadge = (
                <span className="badge" style={{ backgroundColor: "var(--color-primary-subtle)", color: "var(--color-primary)" }}>
                  ? Ingesting...
                </span>
              );
            }

            return (
              <div
                key={step.id}
                style={{
                  padding: "1rem 1.25rem",
                  border: "1px solid",
                  borderColor: isFinished ? "var(--color-success-border)" : isCurrent ? "var(--color-primary)" : "var(--color-border-structural)",
                  borderRadius: "var(--radius-lg)",
                  backgroundColor: isCurrent ? "var(--color-primary-subtle)" : isFinished ? "#ffffff" : "var(--color-card-subtle)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  gap: "1rem",
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem", flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                    <ChannelBadge channel={step.channel} />
                    <span style={{ fontWeight: 600, color: "var(--color-heading)", fontSize: "14px" }}>
                      {step.title}
                    </span>
                  </div>
                  <p style={{ fontSize: "13px", color: "var(--color-body)" }}>{step.description}</p>
                  <div style={{ fontSize: "12px", color: "var(--color-secondary)", marginTop: "2px" }}>
                    <strong>Expected Logic:</strong> {step.expectedOutcome}
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center" }}>{statusBadge}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* -- Confirmation Modal for Reset ------------------------------------ */}
      {showResetModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
            padding: "1rem",
          }}
        >
          <div
            className="panel-card"
            style={{
              maxWidth: "480px",
              width: "100%",
              boxShadow: "var(--shadow-lg)",
              padding: "1.5rem",
            }}
            role="dialog"
            aria-modal="true"
            aria-labelledby="reset-modal-title"
          >
            <h2 id="reset-modal-title" style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-heading)", marginBottom: "0.5rem" }}>
              ?? Reset Demo Sandbox?
            </h2>
            <p style={{ fontSize: "13px", color: "var(--color-body)", lineHeight: 1.6, marginBottom: "1.25rem" }}>
              This will clear all ingested demo events, active alerts, identity match decisions, and re-seed clean baseline fixtures from disk.
            </p>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowResetModal(false)}
                disabled={isResetting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={handleConfirmReset}
                disabled={isResetting}
              >
                {isResetting ? "Resetting Sandbox..." : "Confirm Reset"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
