"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Activity,
  AlertCircle,
  BellRing,
  CheckCircle2,
  ChevronRight,
  CircleDot,
  Fingerprint,
  RefreshCw,
  ShieldCheck,
  TriangleAlert,
  Zap,
} from "lucide-react";
import {
  getAlerts,
  getAnalyticsChannels,
  getAnalyticsOverview,
  getDashboardUpdates,
} from "@/lib/api";
import {
  formatMetric,
  formatPercent,
  formatRelativeTime,
} from "@/lib/formatters";
import { getEventTypeLabel } from "@/lib/presenters";
import type {
  AlertOut,
  AlertSeverity,
  AnalyticsOverview,
  ChannelsResponse,
  DashboardEventOut,
} from "@/lib/types";
import { ChannelBadge, IdentityBadge, SeverityBadge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { EmptyState } from "../ui/EmptyState";
import { ErrorBanner } from "../ui/ErrorBanner";
import { MetricCard } from "../ui/MetricCard";
import { SkeletonBlock } from "../ui/Skeleton";

const ALERT_SEVERITIES: Array<AlertSeverity | "all"> = [
  "all",
  "critical",
  "high",
  "medium",
  "low",
];

const ALERT_ORDER: Record<AlertSeverity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

function formatRate(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${value.toFixed(1)}%`;
}

function alertAccent(severity: AlertSeverity): string {
  if (severity === "critical") return "border-l-red-600 bg-red-50/60";
  if (severity === "high") return "border-l-orange-500 bg-orange-50/50";
  if (severity === "medium") return "border-l-amber-500 bg-amber-50/45";
  return "border-l-slate-400 bg-slate-50";
}

export function CommandCentreView() {
  const router = useRouter();
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [channels, setChannels] = useState<ChannelsResponse | null>(null);
  const [alerts, setAlerts] = useState<AlertOut[]>([]);
  const [events, setEvents] = useState<DashboardEventOut[]>([]);
  const [pendingReviews, setPendingReviews] = useState(0);
  const [openAlertsCount, setOpenAlertsCount] = useState(0);
  const [loadingInitial, setLoadingInitial] = useState(true);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);
  const [alertsError, setAlertsError] = useState<string | null>(null);
  const [pollingDegraded, setPollingDegraded] = useState(false);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null);
  const [selectedSeverity, setSelectedSeverity] = useState<
    AlertSeverity | "all"
  >("all");
  const [showAllAlerts, setShowAllAlerts] = useState(false);

  const cursorRef = useRef<string | undefined>(undefined);
  const failCountRef = useRef(0);
  const isPollingRef = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchAllInitial = useCallback(async () => {
    setLoadingInitial(true);
    setAnalyticsError(null);
    setAlertsError(null);
    const requestStartedAt = new Date().toISOString();

    try {
      const [overviewData, channelsData, alertsData, updatesData] =
        await Promise.allSettled([
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

      if (channelsData.status === "fulfilled") setChannels(channelsData.value);

      if (alertsData.status === "fulfilled") {
        setAlerts(alertsData.value.items);
      } else {
        setAlertsError("The alert feed could not be loaded.");
      }

      if (updatesData.status === "fulfilled") {
        setEvents(updatesData.value.events);
        setPendingReviews(updatesData.value.pending_reviews);
        setOpenAlertsCount(updatesData.value.open_alerts);
      }

      cursorRef.current = requestStartedAt;
      setLastRefreshedAt(new Date());
      failCountRef.current = 0;
      setPollingDegraded(false);
    } finally {
      setLoadingInitial(false);
    }
  }, []);

  useEffect(() => {
    void fetchAllInitial();
  }, [fetchAllInitial]);

  useEffect(() => {
    const poll = async () => {
      if (document.visibilityState !== "visible" || isPollingRef.current)
        return;
      isPollingRef.current = true;
      const requestStartedAt = new Date().toISOString();

      try {
        abortControllerRef.current?.abort();
        const controller = new AbortController();
        abortControllerRef.current = controller;
        const updates = await getDashboardUpdates(
          cursorRef.current,
          controller.signal,
        );

        setEvents((previous) => {
          const byId = new Map<string, DashboardEventOut>();
          [...updates.events, ...previous].forEach((event) =>
            byId.set(event.event_id, event),
          );
          return [...byId.values()]
            .sort(
              (a, b) => Date.parse(b.occurred_at) - Date.parse(a.occurred_at),
            )
            .slice(0, 12);
        });

        setAlerts((previous) => {
          const byId = new Map<string, AlertOut>();
          [...updates.new_alerts, ...previous].forEach((alert) =>
            byId.set(alert.id, alert),
          );
          return [...byId.values()].sort(
            (a, b) => Date.parse(b.created_at) - Date.parse(a.created_at),
          );
        });

        setOpenAlertsCount(updates.open_alerts);
        setPendingReviews(updates.pending_reviews);
        cursorRef.current = requestStartedAt;
        failCountRef.current = 0;
        setPollingDegraded(false);
        setLastRefreshedAt(new Date());
      } catch (error) {
        if (error instanceof Error && error.name !== "AbortError") {
          failCountRef.current += 1;
          if (failCountRef.current >= 3) setPollingDegraded(true);
        }
      } finally {
        isPollingRef.current = false;
      }
    };

    const timer = window.setInterval(() => void poll(), 3_000);
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") void poll();
    };
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      abortControllerRef.current?.abort();
    };
  }, []);

  const filteredAlerts = alerts
    .filter(
      (alert) =>
        selectedSeverity === "all" || alert.severity === selectedSeverity,
    )
    .sort((a, b) => ALERT_ORDER[a.severity] - ALERT_ORDER[b.severity]);
  const visibleAlerts = showAllAlerts
    ? filteredAlerts
    : filteredAlerts.slice(0, 3);

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-4 border-b border-slate-200 pb-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-semibold tracking-tight text-[#172554]">
              Command Centre
            </h1>
            <span className="inline-flex items-center gap-2 rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-800">
              <span
                className="h-2 w-2 rounded-full bg-teal-600"
                aria-hidden="true"
              />
              Polling active
            </span>
          </div>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#667085]">
            Monitor identity resolution, customer journeys, and operational
            issues across every channel.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden rounded-lg border border-[#E4E7EC] bg-white px-3 py-2 text-right text-xs text-[#667085] sm:block">
            <span className="block">Last updated</span>
            <strong className="font-semibold text-[#172554]">
              {lastRefreshedAt
                ? formatRelativeTime(lastRefreshedAt.toISOString())
                : "—"}
            </strong>
          </div>
          <Button
            variant="outline"
            size="md"
            icon={
              <RefreshCw
                className={`h-4 w-4 ${loadingInitial ? "animate-spin" : ""}`}
              />
            }
            onClick={() => void fetchAllInitial()}
            disabled={loadingInitial}
          >
            Refresh
          </Button>
        </div>
      </section>

      {pollingDegraded && (
        <ErrorBanner
          title="Live updates paused"
          message="Polling could not reach the backend. The dashboard is showing the last successful data."
          onRetry={() => void fetchAllInitial()}
        />
      )}
      {analyticsError && (
        <ErrorBanner
          title="Analytics unavailable"
          message={analyticsError}
          onRetry={() => void fetchAllInitial()}
        />
      )}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Unified profiles"
          value={formatMetric(analytics?.unified_profiles)}
          sub="Resolved customer records"
          icon={<Fingerprint className="h-5 w-5 text-indigo-600" />}
          loading={loadingInitial}
        />
        <MetricCard
          label="Events processed"
          value={formatMetric(analytics?.normalized_events)}
          sub={
            analytics
              ? `of ${formatMetric(analytics.total_raw_events)} raw events`
              : undefined
          }
          icon={<Zap className="h-5 w-5 text-teal-600" />}
          loading={loadingInitial}
        />
        <MetricCard
          label="Needs review"
          value={pendingReviews}
          sub="Pending human decisions"
          icon={<TriangleAlert className="h-5 w-5 text-amber-600" />}
          loading={loadingInitial}
        />
        <MetricCard
          label="Active journey alerts"
          value={openAlertsCount}
          sub="Open refund or contact issues"
          icon={<BellRing className="h-5 w-5 text-red-600" />}
          loading={loadingInitial}
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.7fr)_minmax(19rem,0.9fr)]">
        <div className="overflow-hidden rounded-xl border border-[#E4E7EC] bg-white shadow-sm">
          <div className="flex flex-col gap-3 border-b border-slate-100 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-red-50 text-red-600">
                <AlertCircle className="h-4 w-4" aria-hidden="true" />
              </span>
              <div>
                <h2 className="text-base font-semibold text-[#172554]">
                  Priority journey issues
                </h2>
                <p className="text-xs text-[#667085]">
                  {filteredAlerts.length} open alerts in this view
                </p>
              </div>
            </div>
            <div
              className="flex rounded-lg border border-indigo-100 bg-indigo-50/70 p-1"
              role="tablist"
              aria-label="Filter alerts by severity"
            >
              {ALERT_SEVERITIES.map((severity) => (
                <button
                  key={severity}
                  type="button"
                  role="tab"
                  aria-selected={selectedSeverity === severity}
                  onClick={() => {
                    setSelectedSeverity(severity);
                    setShowAllAlerts(false);
                  }}
                  className={`rounded-md px-2.5 py-1 text-xs font-medium capitalize transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ${
                    selectedSeverity === severity
                      ? "bg-white text-indigo-700 shadow-sm"
                      : "text-[#667085] hover:text-[#172554]"
                  }`}
                >
                  {severity}
                </button>
              ))}
            </div>
          </div>

          <div className="p-3 sm:p-4">
            {alertsError ? (
              <ErrorBanner
                message={alertsError}
                onRetry={() => void fetchAllInitial()}
              />
            ) : loadingInitial ? (
              <div className="space-y-3">
                <SkeletonBlock height="94px" />
                <SkeletonBlock height="94px" />
              </div>
            ) : visibleAlerts.length === 0 ? (
              <EmptyState
                title="No active journey issues"
                description="No unresolved refunds or repeat-contact issues match this filter."
              />
            ) : (
              <div className="space-y-3">
                {visibleAlerts.map((alert) => (
                  <article
                    key={alert.id}
                    className={`border-l-4 px-4 py-3 ${alertAccent(alert.severity)}`}
                  >
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div className="flex min-w-0 items-center gap-2">
                        <SeverityBadge severity={alert.severity} />
                        <h3 className="truncate text-sm font-semibold text-[#172554]">
                          {alert.title}
                        </h3>
                      </div>
                      {alert.order_id && (
                        <Link
                          href={`/customers?search=${encodeURIComponent(alert.order_id)}`}
                          className="inline-flex shrink-0 items-center gap-1 text-xs font-semibold text-indigo-700 hover:text-indigo-900"
                        >
                          {alert.order_id}
                          <ChevronRight
                            className="h-3.5 w-3.5"
                            aria-hidden="true"
                          />
                        </Link>
                      )}
                    </div>
                    <p className="mt-2 text-sm leading-5 text-[#475467]">
                      {alert.description}
                    </p>
                    <p className="mt-2 text-xs leading-5 text-[#667085]">
                      <span className="font-semibold text-[#475467]">
                        Recommended action:
                      </span>{" "}
                      {alert.recommended_action}
                    </p>
                  </article>
                ))}
                {filteredAlerts.length > 3 && (
                  <button
                    type="button"
                    className="w-full rounded-lg border border-[#D0D5DD] bg-white px-3 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                    onClick={() => setShowAllAlerts((current) => !current)}
                  >
                    {showAllAlerts
                      ? "Show fewer alerts"
                      : `Show ${filteredAlerts.length - 3} more alerts`}
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        <aside className="rounded-xl border border-[#E4E7EC] bg-white p-5 shadow-sm">
          <div className="border-b border-slate-100 pb-4">
            <h2 className="text-base font-semibold text-[#172554]">
              Channel activity
            </h2>
            <p className="mt-1 text-xs leading-5 text-[#667085]">
              Normalized events by originating channel.
            </p>
          </div>

          {loadingInitial ? (
            <div className="mt-4 space-y-3">
              <SkeletonBlock height="48px" />
              <SkeletonBlock height="48px" />
              <SkeletonBlock height="48px" />
              <SkeletonBlock height="48px" />
            </div>
          ) : channels ? (
            <div className="mt-4 space-y-3">
              {[
                ["web", channels.web],
                ["mobile_app", channels.mobile_app],
                ["call_center", channels.call_center],
                ["physical_store", channels.physical_store],
              ].map(([channel, count]) => (
                <div
                  key={channel}
                  className="flex items-center justify-between rounded-lg border border-[#E4E7EC] bg-slate-50/70 px-3 py-3"
                >
                  <ChannelBadge
                    channel={channel as DashboardEventOut["channel"]}
                  />
                  <span className="tabular-nums text-sm font-semibold text-[#172554]">
                    {formatMetric(count as number)} events
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-4">
              <EmptyState
                title="Channel telemetry unavailable"
                description="Try refreshing the dashboard."
              />
            </div>
          )}

          <p className="mt-5 rounded-lg bg-slate-50 px-3 py-3 text-xs leading-5 text-[#667085]">
            All channel feeds are normalized deterministically into canonical
            timeline events.
          </p>
        </aside>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(18rem,0.85fr)_minmax(0,1.35fr)]">
        <aside className="rounded-xl border border-[#E4E7EC] bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h2 className="text-base font-semibold text-[#172554]">
                Identity resolution
              </h2>
              <p className="mt-1 text-xs text-[#667085]">
                Deterministic matching health
              </p>
            </div>
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-50 text-teal-700">
              <ShieldCheck className="h-5 w-5" aria-hidden="true" />
            </span>
          </div>

          <dl className="mt-4 space-y-3">
            <div className="flex items-center justify-between rounded-lg bg-teal-50/70 px-3 py-3">
              <dt className="flex items-center gap-2 text-sm font-medium text-[#475467]">
                <CheckCircle2
                  className="h-4 w-4 text-teal-700"
                  aria-hidden="true"
                />
                Auto-link rate
              </dt>
              <dd className="tabular-nums text-lg font-semibold text-teal-800">
                {formatRate(analytics?.auto_link_rate)}
              </dd>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-amber-50/70 px-3 py-3">
              <dt className="flex items-center gap-2 text-sm font-medium text-[#475467]">
                <TriangleAlert
                  className="h-4 w-4 text-amber-700"
                  aria-hidden="true"
                />
                Review queue
              </dt>
              <dd className="tabular-nums text-lg font-semibold text-amber-800">
                {formatMetric(pendingReviews)}
              </dd>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-indigo-50/70 px-3 py-3">
              <dt className="flex items-center gap-2 text-sm font-medium text-[#475467]">
                <Activity
                  className="h-4 w-4 text-indigo-700"
                  aria-hidden="true"
                />
                Match precision
              </dt>
              <dd className="tabular-nums text-lg font-semibold text-indigo-800">
                {formatPercent(analytics?.match_precision)}
              </dd>
            </div>
          </dl>

          <p className="mt-4 text-xs leading-5 text-[#667085]">
            {analytics?.false_merge_rate === 0
              ? "No false merges recorded in the latest evaluation."
              : "Evaluation metrics are calculated from labelled synthetic data."}
          </p>
        </aside>

        <div className="overflow-hidden rounded-xl border border-[#E4E7EC] bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
            <div>
              <h2 className="text-base font-semibold text-[#172554]">
                Recent activity
              </h2>
              <p className="mt-1 text-xs text-[#667085]">
                Latest canonical events, refreshed every 3 seconds.
              </p>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-teal-50 px-2.5 py-1 text-xs font-semibold text-teal-800">
              <span
                className="h-1.5 w-1.5 rounded-full bg-teal-600"
                aria-hidden="true"
              />
              Live
            </span>
          </div>

          {loadingInitial ? (
            <div className="space-y-3 p-5">
              <SkeletonBlock height="58px" />
              <SkeletonBlock height="58px" />
              <SkeletonBlock height="58px" />
            </div>
          ) : events.length === 0 ? (
            <div className="p-5">
              <EmptyState
                title="No events recorded yet"
                description="Start the deterministic demo to populate the operational feed."
                actionText="Open Demo Controller"
                onAction={() => router.push("/demo")}
              />
            </div>
          ) : (
            <ol className="divide-y divide-slate-100 px-5">
              {events.slice(0, 8).map((event) => (
                <li key={event.event_id} className="flex gap-3 py-4">
                  <span className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 border-indigo-500 bg-white text-indigo-600">
                    <CircleDot className="h-3 w-3" aria-hidden="true" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <p className="text-sm font-semibold text-[#172554]">
                        {getEventTypeLabel(event.event_type)}
                      </p>
                      <time
                        className="shrink-0 text-xs text-[#667085]"
                        dateTime={event.occurred_at}
                      >
                        {formatRelativeTime(event.occurred_at)}
                      </time>
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <ChannelBadge channel={event.channel} />
                      {event.match_decision && (
                        <IdentityBadge outcome={event.match_decision} />
                      )}
                      {event.profile_id && (
                        <Link
                          href={`/customers/${encodeURIComponent(event.profile_id)}`}
                          className="text-xs font-semibold text-indigo-700 hover:text-indigo-900"
                        >
                          View profile
                        </Link>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
      </section>
    </div>
  );
}
