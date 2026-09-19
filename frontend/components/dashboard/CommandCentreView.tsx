"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  getAlerts,
  getAnalyticsChannels,
  getAnalyticsOverview,
  getDashboardUpdates,
} from "@/lib/api";
import { formatDateTime, formatMetric, formatPercent, formatRelativeTime, shortenId } from "@/lib/formatters";
import { getEventTypeLabel } from "@/lib/presenters";
import {
  AlertOut,
  AlertSeverity,
  AnalyticsOverview,
  ChannelsResponse,
  DashboardEventOut,
} from "@/lib/types";
import { ChannelBadge, IdentityBadge, SeverityBadge } from "../ui/Badge";
import { EmptyState } from "../ui/EmptyState";
import { ErrorBanner } from "../ui/ErrorBanner";
import { MetricCard } from "../ui/MetricCard";
import { SkeletonBlock } from "../ui/Skeleton";

export function CommandCentreView() {
  const router = useRouter();

  // Data states
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [channels, setChannels] = useState<ChannelsResponse | null>(null);
  const [alerts, setAlerts] = useState<AlertOut[]>([]);
  const [events, setEvents] = useState<DashboardEventOut[]>([]);
  const [pendingReviews, setPendingReviews] = useState<number>(0);
  const [openAlertsCount, setOpenAlertsCount] = useState<number>(0);

  // Loading & Error states
  const [loadingInitial, setLoadingInitial] = useState<boolean>(true);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);
  const [alertsError, setAlertsError] = useState<string | null>(null);
  const [pollingDegraded, setPollingDegraded] = useState<boolean>(false);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null);

  // Filter state for alerts
  const [selectedSeverity, setSelectedSeverity] = useState<AlertSeverity | "all">("all");

  // Polling management refs
  const cursorRef = useRef<string | undefined>(undefined);
  const failCountRef = useRef<number>(0);
  const isPollingRef = useRef<boolean>(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Initial Full Load
  const fetchAllInitial = useCallback(async () => {
    setLoadingInitial(true);
    setAnalyticsError(null);
    setAlertsError(null);

    try {
      const [overviewData, channelsData, alertsData, updatesData] = await Promise.allSettled([
        getAnalyticsOverview(),
        getAnalyticsChannels(),
        getAlerts(),
        getDashboardUpdates(),
      ]);

      if (overviewData.status === "fulfilled") {
        setAnalytics(overviewData.value);
        setOpenAlertsCount(overviewData.value.open_alerts);
      } else {
        setAnalyticsError("Analytics overview could not be loaded.");
      }

      if (channelsData.status === "fulfilled") {
        setChannels(channelsData.value);
      }

      if (alertsData.status === "fulfilled") {
        setAlerts(alertsData.value.items || []);
      } else {
        setAlertsError("Alerts list could not be loaded.");
      }

      if (updatesData.status === "fulfilled") {
        const u = updatesData.value;
        setEvents(u.events || []);
        if (typeof u.pending_reviews === "number") setPendingReviews(u.pending_reviews);
        if (typeof u.open_alerts === "number") setOpenAlertsCount(u.open_alerts);
      }

      cursorRef.current = new Date().toISOString();
      setLastRefreshedAt(new Date());
    } finally {
      setLoadingInitial(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    async function load() {
      if (!ignore) {
        await fetchAllInitial();
      }
    }
    load();
    return () => {
      ignore = true;
    };
  }, [fetchAllInitial]);

  // Polling loop for live dashboard updates
  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;

    const poll = async () => {
      if (document.visibilityState !== "visible") return;
      if (isPollingRef.current) return;

      isPollingRef.current = true;
      const requestStartedAt = new Date().toISOString();

      try {
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
        }
        abortControllerRef.current = new AbortController();

        const updates = await getDashboardUpdates(cursorRef.current, abortControllerRef.current.signal);

        // Merge events by event_id deduplication
        if (updates.events && updates.events.length > 0) {
          setEvents((prev) => {
            const map = new Map<string, DashboardEventOut>();
            // Keep new ones first
            updates.events.forEach((ev) => map.set(ev.event_id, ev));
            prev.forEach((ev) => {
              if (!map.has(ev.event_id)) {
                map.set(ev.event_id, ev);
              }
            });
            const merged = Array.from(map.values());
            // Sort by occurred_at descending
            merged.sort((a, b) => new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime());
            return merged.slice(0, 50);
          });
        }

        // Merge new alerts if present
        if (updates.new_alerts && updates.new_alerts.length > 0) {
          setAlerts((prev) => {
            const alertMap = new Map<string, AlertOut>();
            updates.new_alerts.forEach((a) => alertMap.set(a.id, a));
            prev.forEach((a) => {
              if (!alertMap.has(a.id)) {
                alertMap.set(a.id, a);
              }
            });
            const mergedAlerts = Array.from(alertMap.values());
            mergedAlerts.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
            return mergedAlerts;
          });
        }

        if (typeof updates.open_alerts === "number") {
          setOpenAlertsCount(updates.open_alerts);
        }
        if (typeof updates.pending_reviews === "number") {
          setPendingReviews(updates.pending_reviews);
        }

        cursorRef.current = requestStartedAt;
        failCountRef.current = 0;
        setPollingDegraded(false);
        setLastRefreshedAt(new Date());
      } catch (err: unknown) {
        if (err instanceof Error && err.name !== "AbortError") {
          failCountRef.current += 1;
          if (failCountRef.current >= 3) {
            setPollingDegraded(true);
          }
        }
      } finally {
        isPollingRef.current = false;
      }
    };

    timer = setInterval(poll, 3000);

    const handleVisibility = () => {
      if (document.visibilityState === "visible") {
        poll();
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      if (timer) clearInterval(timer);
      document.removeEventListener("visibilitychange", handleVisibility);
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, []);

  const filteredAlerts = alerts.filter((a) => {
    if (selectedSeverity === "all") return true;
    return a.severity === selectedSeverity;
  });

  return (
    <div>
      {/* Top Header */}
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
          <h1 style={{ fontSize: "24px", fontWeight: 700, color: "var(--color-heading)" }}>
            Command Centre
          </h1>
          <p style={{ color: "var(--color-secondary)", fontSize: "14px", marginTop: "2px" }}>
            Real-time operations, identity resolution health, and priority customer journey issues.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          {lastRefreshedAt && (
            <span style={{ fontSize: "12px", color: "var(--color-secondary)" }}>
              Updated {formatRelativeTime(lastRefreshedAt.toISOString())}
            </span>
          )}
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={fetchAllInitial}
            disabled={loadingInitial}
          >
            ?? Refresh
          </button>
        </div>
      </div>

      {/* Polling Degraded Banner */}
      {pollingDegraded && (
        <ErrorBanner
          title="Live stream degraded"
          message="Continuous polling has experienced connection issues. Displaying cached operational data."
          onRetry={fetchAllInitial}
        />
      )}

      {/* Analytics Partial Error */}
      {analyticsError && (
        <ErrorBanner title="Analytics unavailable" message={analyticsError} onRetry={fetchAllInitial} />
      )}

      {/* -- KPI Metric Cards ------------------------------------------------ */}
      <div className="metrics-grid">
        <MetricCard
          label="Unified Profiles"
          value={formatMetric(analytics?.unified_profiles)}
          sub="Resolved customers"
          loading={loadingInitial}
        />
        <MetricCard
          label="Events Processed"
          value={formatMetric(analytics?.normalized_events)}
          sub={analytics?.total_raw_events ? `of ${formatMetric(analytics.total_raw_events)} raw` : undefined}
          loading={loadingInitial}
        />
        <MetricCard
          label="Needs Review"
          value={pendingReviews}
          sub="Pending human review"
          loading={loadingInitial}
        />
        <MetricCard
          label="Active Alerts"
          value={openAlertsCount}
          sub="Unresolved journey issues"
          loading={loadingInitial}
        />
        <MetricCard
          label="Match Precision"
          value={analytics?.match_precision !== null && analytics?.match_precision !== undefined ? formatPercent(analytics.match_precision) : "�"}
          sub={analytics?.match_precision === null ? "Not evaluated yet" : "Deterministic accuracy"}
          loading={loadingInitial}
        />
        <MetricCard
          label="Auto-Link Rate"
          value={formatPercent(analytics?.auto_link_rate)}
          sub="High-confidence links"
          loading={loadingInitial}
        />
      </div>

      {/* -- Grid with Alerts & Channels ------------------------------------- */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
          gap: "1.5rem",
          marginBottom: "1.5rem",
        }}
      >
        {/* Priority Journey Issues */}
        <div className="panel-card">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Priority Journey Issues</h2>
              <span style={{ fontSize: "12px", color: "var(--color-secondary)" }}>
                {filteredAlerts.length} {selectedSeverity !== "all" ? selectedSeverity : ""} alert
                {filteredAlerts.length !== 1 ? "s" : ""}
              </span>
            </div>

            {/* Severity Tabs */}
            <div style={{ display: "flex", gap: "0.25rem", background: "var(--color-card-subtle)", padding: "2px", borderRadius: "var(--radius-sm)" }}>
              {(["all", "critical", "high", "medium", "low"] as const).map((sev) => (
                <button
                  key={sev}
                  type="button"
                  onClick={() => setSelectedSeverity(sev)}
                  style={{
                    border: "none",
                    background: selectedSeverity === sev ? "#ffffff" : "transparent",
                    color: selectedSeverity === sev ? "var(--color-heading)" : "var(--color-secondary)",
                    fontWeight: selectedSeverity === sev ? 600 : 400,
                    fontSize: "11px",
                    padding: "3px 8px",
                    borderRadius: "4px",
                    cursor: "pointer",
                    boxShadow: selectedSeverity === sev ? "var(--shadow-sm)" : "none",
                    textTransform: "capitalize",
                  }}
                >
                  {sev}
                </button>
              ))}
            </div>
          </div>

          {alertsError && <ErrorBanner message={alertsError} onRetry={fetchAllInitial} />}

          {loadingInitial ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <SkeletonBlock height="60px" />
              <SkeletonBlock height="60px" />
            </div>
          ) : filteredAlerts.length === 0 ? (
            <EmptyState
              title="No active alerts"
              description="No unresolved refunds or repeat-contact anomalies detected in this view."
              icon="?"
            />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", maxHeight: "360px", overflowY: "auto" }}>
              {filteredAlerts.map((alert) => (
                <div
                  key={alert.id}
                  style={{
                    padding: "0.875rem",
                    border: "1px solid var(--color-border-structural)",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: alert.severity === "critical" ? "var(--color-danger-subtle)" : "#ffffff",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.35rem" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <SeverityBadge severity={alert.severity} />
                      <span style={{ fontWeight: 600, color: "var(--color-heading)", fontSize: "13px" }}>
                        {alert.title}
                      </span>
                    </div>
                    {alert.order_id && (
                      <Link
                        href={`/customers?search=${encodeURIComponent(alert.order_id)}`}
                        className="badge"
                        style={{ backgroundColor: "#f1f5f9", color: "var(--color-body)", fontSize: "11px" }}
                        title="Search order in Customer Explorer"
                      >
                        Order: {alert.order_id} ?
                      </Link>
                    )}
                  </div>
                  <p style={{ fontSize: "13px", color: "var(--color-body)", marginBottom: "0.4rem" }}>
                    {alert.description}
                  </p>
                  <div style={{ fontSize: "12px", color: "var(--color-secondary)" }}>
                    <strong>Recommended action:</strong> {alert.recommended_action}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Channel Distribution */}
        <div className="panel-card">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Channel Activity Ingestion</h2>
              <span style={{ fontSize: "12px", color: "var(--color-secondary)" }}>
                Distribution across 4 ingest channels
              </span>
            </div>
          </div>

          {loadingInitial ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <SkeletonBlock height="40px" />
              <SkeletonBlock height="40px" />
              <SkeletonBlock height="40px" />
            </div>
          ) : channels ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.875rem" }}>
              {[
                { channel: "web" as const, count: channels.web },
                { channel: "mobile_app" as const, count: channels.mobile_app },
                { channel: "call_center" as const, count: channels.call_center },
                { channel: "physical_store" as const, count: channels.physical_store },
              ].map(({ channel, count }) => (
                <div
                  key={channel}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "0.75rem 1rem",
                    border: "1px solid var(--color-border-structural)",
                    borderRadius: "var(--radius-md)",
                  }}
                >
                  <ChannelBadge channel={channel} />
                  <span style={{ fontWeight: 700, fontSize: "16px" }} className="tabular-nums">
                    {formatMetric(count)} events
                  </span>
                </div>
              ))}

              <div style={{ marginTop: "0.5rem", padding: "0.75rem", backgroundColor: "var(--color-card-subtle)", borderRadius: "var(--radius-sm)", fontSize: "12px", color: "var(--color-secondary)" }}>
                ?? All channel feeds are normalized deterministically into canonical timeline events.
              </div>
            </div>
          ) : (
            <EmptyState title="No channel telemetry" description="Channel statistics are currently unavailable." />
          )}
        </div>
      </div>

      {/* -- Recent Activity Stream ------------------------------------------ */}
      <div className="panel-card">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Recent Event Stream</h2>
            <span style={{ fontSize: "12px", color: "var(--color-secondary)" }}>
              Polling every 3 seconds � Showing newest canonical activity
            </span>
          </div>
          <span className="badge" style={{ backgroundColor: "var(--color-primary-subtle)", color: "var(--color-primary)" }}>
            ? Live Updates
          </span>
        </div>

        {loadingInitial ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <SkeletonBlock height="36px" />
            <SkeletonBlock height="36px" />
            <SkeletonBlock height="36px" />
          </div>
        ) : events.length === 0 ? (
          <EmptyState
            title="No events recorded yet"
            description="Start the demo scenario or ingest events to observe real-time stream activity."
            actionText="Go to Demo Controller"
            onAction={() => router.push("/demo")}
            icon="?"
          />
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Event ID</th>
                  <th>Channel</th>
                  <th>Event Type</th>
                  <th>Occurred At</th>
                  <th>Profile Link</th>
                  <th>Identity Decision</th>
                </tr>
              </thead>
              <tbody>
                {events.map((ev) => (
                  <tr key={ev.event_id}>
                    <td className="font-mono" style={{ fontSize: "12px" }}>
                      <span title={ev.event_id}>{shortenId(ev.event_id, 10)}</span>
                    </td>
                    <td>
                      <ChannelBadge channel={ev.channel} />
                    </td>
                    <td style={{ fontWeight: 500 }}>{getEventTypeLabel(ev.event_type)}</td>
                    <td style={{ fontSize: "12px", color: "var(--color-secondary)" }}>
                      {formatDateTime(ev.occurred_at)}
                    </td>
                    <td>
                      {ev.profile_id ? (
                        <Link
                          href={`/customers/${encodeURIComponent(ev.profile_id)}`}
                          style={{
                            color: "var(--color-primary)",
                            fontWeight: 500,
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "3px",
                          }}
                        >
                          <span className="font-mono">{shortenId(ev.profile_id)}</span> ?
                        </Link>
                      ) : (
                        <span style={{ color: "var(--color-muted)" }}>�</span>
                      )}
                    </td>
                    <td>
                      {ev.match_decision ? (
                        <IdentityBadge outcome={ev.match_decision} />
                      ) : (
                        <span style={{ color: "var(--color-muted)" }}>�</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
