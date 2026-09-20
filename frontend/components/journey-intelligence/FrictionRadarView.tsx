"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ChevronRight,
  Clock3,
  Headphones,
  RefreshCw,
  ShieldCheck,
  UsersRound,
} from "lucide-react";
import { ApiClientError, getFrictionRadar } from "@/lib/api";
import type { FrictionBand, FrictionJourney, FrictionRadarResponse } from "@/lib/types";
import { CHANNEL_META } from "@/lib/presenters";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";

const JOURNEY_LIMIT = 20;

const bandStyle: Record<FrictionBand, string> = {
  critical: "border-red-200 bg-red-50 text-red-800",
  elevated: "border-amber-200 bg-amber-50 text-amber-800",
  watch: "border-blue-200 bg-blue-50 text-blue-800",
  none: "border-slate-200 bg-slate-50 text-slate-700",
};

const componentLabels = [
  ["unresolved_age_points", "Unresolved age"],
  ["channel_points", "Support channels"],
  ["support_contact_points", "Support contacts"],
  ["repeat_contact_points", "Open repeat-contact alert"],
  ["pending_candidate_review_points", "Pending candidate review"],
] as const;

function formatSnapshot(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown time";
  return new Intl.DateTimeFormat(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function displayName(journey: FrictionJourney): string {
  return journey.display_name ?? "Resolved profile";
}

export function FrictionRadarView() {
  const [radar, setRadar] = useState<FrictionRadarResponse | null>(null);
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiClientError | null>(null);

  const loadRadar = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getFrictionRadar({ limit: JOURNEY_LIMIT });
      setRadar(response);
      setSelectedAlertId((current) =>
        response.journeys.some((journey) => journey.alert_id === current)
          ? current
          : (response.journeys[0]?.alert_id ?? null)
      );
    } catch (caught) {
      setError(
        caught instanceof ApiClientError
          ? caught
          : new ApiClientError(0, {
              code: "FRICTION_RADAR_LOAD_FAILED",
              message: "The friction ranking could not be loaded.",
              stage: "analytics",
            })
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadRadar();
  }, [loadRadar]);

  const selectedJourney = useMemo(
    () => radar?.journeys.find((journey) => journey.alert_id === selectedAlertId) ?? null,
    [radar, selectedAlertId]
  );
  const maxAgeBucket = Math.max(
    1,
    ...(radar?.unresolved_age_distribution.map((bucket) => bucket.count) ?? [0])
  );

  if (loading) return <FrictionRadarSkeleton />;
  if (!radar || error) {
    return (
      <ErrorState
        title="Journey intelligence is unavailable"
        message={error?.message ?? "The friction ranking could not be loaded."}
        code={error?.code}
        onRetry={() => void loadRadar()}
      />
    );
  }

  const { summary } = radar;
  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-600">
            Operations prioritization
          </p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-[#172554]">
            Journey Friction Radar
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[#667085]">
            Rank open, attributable unresolved refunds by persisted journey evidence so the team can inspect the most disrupted customer journey first.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-800">
            Score: 0–{radar.score_max}
          </span>
          <span className="text-xs text-[#667085]">Snapshot {formatSnapshot(radar.as_of)}</span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void loadRadar()}
            icon={<RefreshCw className="h-3.5 w-3.5" />}
          >
            Refresh
          </Button>
        </div>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Friction radar summary">
        <MetricCard label="Ranked open refunds" value={summary.attributable_open_refunds} detail="Profile and order are known" icon={<UsersRound className="h-5 w-5" />} tone="indigo" />
        <MetricCard label="Critical journeys" value={summary.critical} detail="Score 45–60" icon={<AlertTriangle className="h-5 w-5" />} tone="red" />
        <MetricCard label="Elevated journeys" value={summary.elevated} detail="Score 30–44" icon={<Clock3 className="h-5 w-5" />} tone="amber" />
        <MetricCard label="Unattributed alerts" value={summary.unattributed_open_refunds} detail="Shown but not rankable" icon={<ShieldCheck className="h-5 w-5" />} tone="slate" />
      </section>

      {radar.journeys.length === 0 ? (
        <EmptyState
          icon={<ShieldCheck className="h-6 w-6" />}
          title="No attributable open refunds to rank"
          description={
            summary.unattributed_open_refunds > 0
              ? `${summary.unattributed_open_refunds} open refund alert${summary.unattributed_open_refunds === 1 ? " is" : "s are"} missing a profile or order, so ${summary.unattributed_open_refunds === 1 ? "it" : "they"} cannot be ranked here.`
              : "Open unresolved-refund alerts will appear here once both a profile and order are persisted."
          }
        />
      ) : (
        <section className="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(21rem,0.9fr)]">
          <div className="overflow-hidden rounded-xl border border-[#E4E7EC] bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
              <div>
                <h2 className="text-base font-semibold text-[#172554]">Ranked refund journeys</h2>
                <p className="mt-1 text-xs text-[#667085]">Highest persisted friction first.</p>
              </div>
              <span className="text-xs text-[#667085]">{radar.journeys.length} shown</span>
            </div>
            <ol className="divide-y divide-slate-100">
              {radar.journeys.map((journey, index) => {
                const selected = journey.alert_id === selectedAlertId;
                return (
                  <li key={journey.alert_id}>
                    <button
                      type="button"
                      onClick={() => setSelectedAlertId(journey.alert_id)}
                      className={`flex w-full gap-3 px-4 py-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-indigo-500 ${selected ? "bg-indigo-50/70" : "hover:bg-slate-50"}`}
                      aria-pressed={selected}
                    >
                      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-700">{index + 1}</span>
                      <span className="min-w-0 flex-1">
                        <span className="flex flex-wrap items-center gap-2">
                          <span className="truncate text-sm font-semibold text-[#172554]">{displayName(journey)}</span>
                          <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold capitalize ${bandStyle[journey.band]}`}>{journey.band}</span>
                        </span>
                        <span className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-[#667085]">
                          <span className="font-mono font-semibold text-slate-700">{journey.order_id}</span>
                          <span>{journey.unresolved_age_days} unresolved day{journey.unresolved_age_days === 1 ? "" : "s"}</span>
                          <span>{journey.support_contact_count} support contact{journey.support_contact_count === 1 ? "" : "s"}</span>
                        </span>
                      </span>
                      <span className="flex shrink-0 items-center gap-1 text-right">
                        <strong className="tabular-nums text-2xl tracking-tight text-[#172554]">{journey.friction_score}</strong>
                        <ChevronRight className="h-4 w-4 text-[#667085]" aria-hidden="true" />
                      </span>
                    </button>
                  </li>
                );
              })}
            </ol>
          </div>

          {selectedJourney && <EvidenceLedger journey={selectedJourney} scoreMax={radar.score_max} />}
        </section>
      )}

      <section className="grid gap-6 lg:grid-cols-2">
        <DistributionPanel buckets={radar.unresolved_age_distribution} maxCount={maxAgeBucket} />
        <ContactChannelsPanel channels={radar.support_contact_channels} />
      </section>
    </div>
  );
}

function MetricCard({ label, value, detail, icon, tone }: { label: string; value: number; detail: string; icon: React.ReactNode; tone: "indigo" | "red" | "amber" | "slate" }) {
  const tones = {
    indigo: "border-indigo-100 bg-indigo-50/60 text-indigo-700",
    red: "border-red-100 bg-red-50/60 text-red-700",
    amber: "border-amber-100 bg-amber-50/60 text-amber-700",
    slate: "border-slate-200 bg-slate-50 text-slate-700",
  };
  return <article className={`rounded-xl border p-4 ${tones[tone]}`}><div className="flex items-start justify-between"><p className="text-sm font-semibold">{label}</p><span aria-hidden="true">{icon}</span></div><p className="mt-3 tabular-nums text-3xl font-bold tracking-tight text-[#172554]">{value.toLocaleString()}</p><p className="mt-1 text-xs text-[#667085]">{detail}</p></article>;
}

function EvidenceLedger({ journey, scoreMax }: { journey: FrictionJourney; scoreMax: number }) {
  return (
    <aside className="rounded-xl border border-[#E4E7EC] bg-white p-5 shadow-sm" aria-label="Selected journey evidence">
      <div className="flex items-start justify-between gap-3 border-b border-slate-100 pb-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-indigo-600">Evidence ledger</p>
          <h2 className="mt-1 text-lg font-semibold text-[#172554]">{displayName(journey)}</h2>
          <p className="mt-1 font-mono text-xs text-[#667085]">{journey.order_id}</p>
        </div>
        <span className={`rounded-lg border px-2.5 py-1 text-sm font-bold ${bandStyle[journey.band]}`}>{journey.friction_score}/{scoreMax}</span>
      </div>
      <dl className="mt-4 space-y-2">
        {componentLabels.map(([key, label]) => <div key={key} className="flex items-center justify-between gap-4 rounded-lg bg-slate-50 px-3 py-2.5"><dt className="text-sm text-[#475467]">{label}</dt><dd className="tabular-nums text-sm font-bold text-[#172554]">+{journey.components[key]}</dd></div>)}
      </dl>
      <div className="mt-4 grid grid-cols-2 gap-3 border-t border-slate-100 pt-4 text-xs">
        <Fact label="Support channels" value={journey.distinct_channel_count} />
        <Fact label="Support contacts" value={journey.support_contact_count} />
        <Fact label="Repeat-contact alert" value={journey.has_open_repeat_contact_alert ? "Open" : "None"} />
        <Fact label="Candidate reviews" value={journey.pending_candidate_review_count} />
      </div>
      <Link href={`/customers/${encodeURIComponent(journey.profile_id)}`} className="mt-5 flex items-center justify-center gap-1.5 rounded-md border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-semibold text-indigo-800 transition-colors hover:bg-indigo-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500">View unified customer timeline <ChevronRight className="h-4 w-4" aria-hidden="true" /></Link>
      <p className="mt-3 text-xs leading-5 text-[#667085]">Candidate reviews add score only when the pending decision names this profile and the same order. They are not treated as linked events.</p>
    </aside>
  );
}

function Fact({ label, value }: { label: string; value: number | string }) { return <div><dt className="text-[#667085]">{label}</dt><dd className="mt-1 font-semibold text-[#172554]">{value}</dd></div>; }

function DistributionPanel({ buckets, maxCount }: { buckets: FrictionRadarResponse["unresolved_age_distribution"]; maxCount: number }) { return <section className="rounded-xl border border-[#E4E7EC] bg-white p-5 shadow-sm"><h2 className="text-base font-semibold text-[#172554]">Unresolved age distribution</h2><p className="mt-1 text-xs text-[#667085]">Ranked open refunds by elapsed whole days since the earliest return request.</p><div className="mt-5 space-y-4">{buckets.map((bucket) => <div key={bucket.bucket}><div className="mb-1.5 flex justify-between text-sm"><span className="text-[#475467]">{bucket.bucket}</span><strong className="tabular-nums text-[#172554]">{bucket.count}</strong></div><div className="h-2.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-indigo-500" style={{ width: `${(bucket.count / maxCount) * 100}%` }} aria-label={`${bucket.bucket}: ${bucket.count} journey${bucket.count === 1 ? "" : "s"}`} /></div></div>)}</div></section>; }

function ContactChannelsPanel({ channels }: { channels: FrictionRadarResponse["support_contact_channels"] }) { return <section className="rounded-xl border border-[#E4E7EC] bg-white p-5 shadow-sm"><div className="flex items-start gap-3"><span className="mt-0.5 rounded-lg bg-teal-50 p-2 text-teal-700"><Headphones className="h-4 w-4" aria-hidden="true" /></span><div><h2 className="text-base font-semibold text-[#172554]">Support-contact channels</h2><p className="mt-1 text-xs text-[#667085]">Raw support-contact events across all ranked journeys.</p></div></div>{channels.length === 0 ? <p className="mt-5 rounded-lg bg-slate-50 px-3 py-4 text-sm text-[#667085]">No persisted support contacts are associated with the ranked journeys.</p> : <ul className="mt-5 space-y-3">{channels.map((channel) => <li key={channel.channel} className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50 px-3 py-3"><span className="text-sm font-medium text-[#475467]">{CHANNEL_META[channel.channel].label}</span><span className="text-right"><strong className="block tabular-nums text-sm text-[#172554]">{channel.count}</strong><span className="text-xs text-[#667085]">{channel.share_percent ?? "—"}% of contacts</span></span></li>)}</ul>}</section>; }

function FrictionRadarSkeleton() { return <div className="animate-pulse space-y-6"><div className="h-28 rounded-xl bg-slate-100" /><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }, (_, index) => <div key={index} className="h-36 rounded-xl bg-slate-100" />)}</div><div className="grid gap-6 xl:grid-cols-2"><div className="h-[360px] rounded-xl bg-slate-100" /><div className="h-[360px] rounded-xl bg-slate-100" /></div></div>; }
