"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowUpRight,
  Bot,
  CheckCircle2,
  Headphones,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import {
  ApiClientError,
  generateFrictionRadarBrief,
  getFrictionRadar,
} from "@/lib/api";
import type {
  AiOperationsBrief,
  FrictionBand,
  FrictionJourney,
  FrictionRadarResponse,
} from "@/lib/types";
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

const scoreParts = [
  ["unresolved_age_points", "Unresolved age", "bg-rose-500"],
  ["channel_points", "Support channels", "bg-amber-400"],
  ["support_contact_points", "Support contacts", "bg-orange-500"],
  ["repeat_contact_points", "Repeat contact", "bg-violet-500"],
  ["pending_candidate_review_points", "Candidate review", "bg-sky-500"],
] as const;

const signalLabels: Record<AiOperationsBrief["highlighted_signal"], string> = {
  unresolved_age: "unresolved age",
  support_channels: "support-channel spread",
  support_contacts: "repeated support contact",
  repeat_contact: "an open repeat-contact alert",
  candidate_review: "a pending candidate review",
};

function displayName(journey: FrictionJourney): string {
  return journey.display_name ?? "Resolved profile";
}

function snapshot(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown time";
  return new Intl.DateTimeFormat(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function clientError(message: string, code: string): ApiClientError {
  return new ApiClientError(0, { code, message, stage: "analytics" });
}

export function OperationsDossierView() {
  const [radar, setRadar] = useState<FrictionRadarResponse | null>(null);
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const [brief, setBrief] = useState<AiOperationsBrief | null>(null);
  const [loading, setLoading] = useState(true);
  const [briefLoading, setBriefLoading] = useState(false);
  const [error, setError] = useState<ApiClientError | null>(null);
  const [briefError, setBriefError] = useState<ApiClientError | null>(null);

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
          : clientError("The friction ranking could not be loaded.", "FRICTION_RADAR_LOAD_FAILED")
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const requestBrief = useCallback(async () => {
    setBriefLoading(true);
    setBriefError(null);
    try {
      const response = await generateFrictionRadarBrief();
      setBrief(response);
      setSelectedAlertId(response.focus_alert_id);
    } catch (caught) {
      setBriefError(
        caught instanceof ApiClientError
          ? caught
          : clientError("The optional operations brief could not be generated.", "AI_BRIEF_FAILED")
      );
    } finally {
      setBriefLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadRadar();
  }, [loadRadar]);

  const selected = useMemo(
    () => radar?.journeys.find((journey) => journey.alert_id === selectedAlertId) ?? null,
    [radar, selectedAlertId]
  );
  const totalReviews = radar?.journeys.reduce(
    (total, journey) => total + journey.pending_candidate_review_count,
    0
  );
  const repeatedContactCases = radar?.journeys.filter(
    (journey) => journey.has_open_repeat_contact_alert
  ).length;

  if (loading) return <DossierSkeleton />;
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
      <header className="border-b border-slate-200 pb-5">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.15em] text-indigo-600">
              Operations prioritization
            </p>
            <h1 className="mt-1 text-3xl font-bold tracking-tight text-[#172554]">
              Journey Friction Radar
            </h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-[#667085]">
              A deterministic queue of open refund journeys. Every rank is derived from persisted
              age, contact, channel, and review signals—not an AI judgement.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1.5 font-semibold text-indigo-800">
              friction_v1 · 0–{radar.score_max}
            </span>
            <span className="text-[#667085]">Snapshot {snapshot(radar.as_of)}</span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void loadRadar()}
              icon={<RefreshCw className="h-3.5 w-3.5" />}
            >
              Refresh facts
            </Button>
          </div>
        </div>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Operational totals">
        <Stat label="Ranked refunds" value={summary.attributable_open_refunds} hint="Profile and order are known" />
        <Stat label="Critical now" value={summary.critical} hint="Score 45–60" tone="critical" />
        <Stat label="Repeat-contact cases" value={repeatedContactCases ?? 0} hint="Open alert persists" tone="elevated" />
        <Stat label="Outside this rank" value={summary.unattributed_open_refunds} hint="Missing profile or order" />
      </section>

      {radar.journeys.length === 0 ? (
        <EmptyState
          icon={<CheckCircle2 className="h-6 w-6" />}
          title="No attributable open refunds to prioritize"
          description={
            summary.unattributed_open_refunds > 0
              ? `${summary.unattributed_open_refunds} open refund alert${summary.unattributed_open_refunds === 1 ? " is" : "s are"} not ranked because a profile or order is missing.`
              : "New attributable unresolved-refund alerts will be ranked here."
          }
        />
      ) : (
        <>
          {selected && <PriorityDossier journey={selected} scoreMax={radar.score_max} />}

          <section className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(22rem,0.8fr)]">
            <RankedQueue
              journeys={radar.journeys}
              selectedAlertId={selectedAlertId}
              scoreMax={radar.score_max}
              onSelect={setSelectedAlertId}
            />
            <div className="space-y-6">
              <AiBriefPanel
                brief={brief}
                error={briefError}
                loading={briefLoading}
                onGenerate={() => void requestBrief()}
              />
              {selected && <EvidencePanel journey={selected} />}
            </div>
          </section>
        </>
      )}

      <section className="grid gap-6 lg:grid-cols-2">
        <AgeDistribution radar={radar} />
        <SignalContext
          radar={radar}
          totalReviews={totalReviews ?? 0}
          repeatedContactCases={repeatedContactCases ?? 0}
        />
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: number;
  hint: string;
  tone?: "default" | "critical" | "elevated";
}) {
  const accent = {
    default: "border-slate-200 bg-white",
    critical: "border-red-200 bg-red-50/50",
    elevated: "border-amber-200 bg-amber-50/50",
  }[tone];
  return (
    <article className={`rounded-xl border p-4 shadow-sm ${accent}`}>
      <p className="text-xs font-semibold uppercase tracking-wide text-[#667085]">{label}</p>
      <p className="mt-2 text-3xl font-bold tracking-tight text-[#172554]">{value.toLocaleString()}</p>
      <p className="mt-1 text-xs text-[#667085]">{hint}</p>
    </article>
  );
}

function PriorityDossier({ journey, scoreMax }: { journey: FrictionJourney; scoreMax: number }) {
  return (
    <section
      className="overflow-hidden rounded-xl border border-[#E4E7EC] bg-white text-[#172554] shadow-sm"
      aria-label="Priority case dossier"
    >
      <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1fr_auto] lg:items-start">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-indigo-600">
            Priority case · inspect first
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <h2 className="text-2xl font-bold tracking-tight">{displayName(journey)}</h2>
            <span className={`rounded-full border px-2.5 py-1 text-xs font-bold capitalize ${bandStyle[journey.band]}`}>
              {journey.band}
            </span>
          </div>
          <p className="mt-2 font-mono text-sm text-[#667085]">Order {journey.order_id}</p>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-[#475467]">
            This case is ranked because its persisted evidence adds up to the score below. Review
            status is a risk signal only; it never means an event was automatically linked.
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-5 py-3 text-right">
          <p className="text-xs uppercase tracking-wide text-[#667085]">Friction score</p>
          <p className="mt-1 text-4xl font-bold tabular-nums text-[#172554]">
            {journey.friction_score}<span className="text-lg text-[#667085]">/{scoreMax}</span>
          </p>
        </div>
      </div>
      <div className="border-t border-slate-100 bg-slate-50/70 px-6 py-5">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h3 className="text-sm font-semibold">Score decomposition</h3>
          <span className="text-xs text-[#667085]">Points come from deterministic rules</span>
        </div>
        <div className="grid gap-2 sm:grid-cols-5">
          {scoreParts.map(([key, label, color]) => (
            <div key={key} className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
              <div className={`h-1.5 rounded-full ${color}`} />
              <p className="mt-3 text-2xl font-bold tabular-nums">+{journey.components[key]}</p>
              <p className="mt-1 text-xs leading-4 text-[#667085]">{label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function RankedQueue({
  journeys,
  selectedAlertId,
  scoreMax,
  onSelect,
}: {
  journeys: FrictionJourney[];
  selectedAlertId: string | null;
  scoreMax: number;
  onSelect: (alertId: string) => void;
}) {
  return (
    <section className="overflow-hidden rounded-xl border border-[#E4E7EC] bg-white shadow-sm">
      <div className="flex items-end justify-between border-b border-slate-100 px-5 py-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.13em] text-indigo-600">Case queue</p>
          <h2 className="mt-1 text-lg font-semibold text-[#172554]">Ranked open refund journeys</h2>
        </div>
        <span className="text-xs text-[#667085]">Highest score first</span>
      </div>
      <ol className="divide-y divide-slate-100">
        {journeys.map((journey, index) => {
          const selected = journey.alert_id === selectedAlertId;
          return (
            <li key={journey.alert_id}>
              <button
                type="button"
                onClick={() => onSelect(journey.alert_id)}
                aria-pressed={selected}
                className={`w-full px-5 py-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-indigo-500 ${selected ? "bg-indigo-50" : "hover:bg-slate-50"}`}
              >
                <div className="flex gap-3">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-700">
                    {index + 1}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-semibold text-[#172554]">{displayName(journey)}</span>
                      <span className="flex items-center gap-2">
                        <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold capitalize ${bandStyle[journey.band]}`}>
                          {journey.band}
                        </span>
                        <strong className="text-lg tabular-nums text-[#172554]">{journey.friction_score}</strong>
                      </span>
                    </span>
                    <span className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-xs text-[#667085]">
                      <span className="font-mono">{journey.order_id}</span>
                      <span>{journey.unresolved_age_days}d unresolved</span>
                      <span>{journey.distinct_channel_count} channels</span>
                      <span>{journey.support_contact_count} support contacts</span>
                    </span>
                    <span className="mt-3 block h-1.5 overflow-hidden rounded-full bg-slate-100">
                      <span
                        className="block h-full rounded-full bg-indigo-500"
                        style={{ width: `${(journey.friction_score / scoreMax) * 100}%` }}
                      />
                    </span>
                  </span>
                </div>
              </button>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function AiBriefPanel({
  brief,
  error,
  loading,
  onGenerate,
}: {
  brief: AiOperationsBrief | null;
  error: ApiClientError | null;
  loading: boolean;
  onGenerate: () => void;
}) {
  return (
    <section className="rounded-xl border border-violet-200 bg-violet-50/60 p-5 shadow-sm" aria-label="AI operations brief">
      <div className="flex items-start justify-between gap-4">
        <div className="flex gap-3">
          <span className="rounded-lg bg-violet-600 p-2 text-white"><Bot className="h-4 w-4" /></span>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.13em] text-violet-700">Optional AI wording</p>
            <h2 className="mt-1 text-base font-semibold text-[#172554]">Operations brief</h2>
          </div>
        </div>
        <Button size="sm" variant="outline" disabled={loading} onClick={onGenerate} icon={<Sparkles className="h-3.5 w-3.5" />}>
          {loading ? "Writing…" : brief ? "Refresh brief" : "Generate brief"}
        </Button>
      </div>
      {brief ? (
        <div className="mt-4 rounded-lg border border-violet-100 bg-white p-4">
          <p className="font-semibold text-[#172554]">{brief.headline}</p>
          <p className="mt-2 text-sm leading-6 text-[#475467]">{brief.summary}</p>
          <p className="mt-3 text-xs text-[#667085]">
            Highlights {signalLabels[brief.highlighted_signal]} · {brief.provider} / {brief.model}
            {brief.cached ? " · cached wording" : ""}
          </p>
        </div>
      ) : error ? (
        <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-3 text-sm text-amber-900">
          The facts remain available. The optional brief could not be generated: {error.message}
        </p>
      ) : (
        <p className="mt-4 text-sm leading-6 text-[#475467]">
          Generate a short, safe explanation of the selected verified ranking. It cannot change a score, identity decision, or alert.
        </p>
      )}
    </section>
  );
}

function EvidencePanel({ journey }: { journey: FrictionJourney }) {
  const facts = [
    ["Unresolved age", `${journey.unresolved_age_days} days`],
    ["Support-channel spread", `${journey.distinct_channel_count} channels`],
    ["Support contacts", journey.support_contact_count],
    ["Repeat-contact alert", journey.has_open_repeat_contact_alert ? "Open" : "None"],
    ["Candidate review", journey.pending_candidate_review_count || "None"],
  ];
  return (
    <section className="rounded-xl border border-[#E4E7EC] bg-white p-5 shadow-sm" aria-label="Evidence and action">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.13em] text-indigo-600">Evidence and action</p>
          <h2 className="mt-1 text-lg font-semibold text-[#172554]">{displayName(journey)}</h2>
          <p className="mt-1 font-mono text-xs text-[#667085]">{journey.order_id}</p>
        </div>
        <AlertTriangle className="h-5 w-5 text-amber-600" aria-hidden="true" />
      </div>
      <dl className="mt-4 divide-y divide-slate-100 rounded-lg border border-slate-100">
        {facts.map(([label, value]) => (
          <div key={label} className="flex items-center justify-between gap-4 px-3 py-2.5 text-sm">
            <dt className="text-[#667085]">{label}</dt>
            <dd className="font-semibold text-[#172554]">{value}</dd>
          </div>
        ))}
      </dl>
      <Link
        href={`/customers/${encodeURIComponent(journey.profile_id)}`}
        className="mt-4 flex items-center justify-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
      >
        Inspect unified customer timeline <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
      </Link>
      <p className="mt-3 text-xs leading-5 text-[#667085]">
        A candidate review contributes risk only when it names this profile and order. It never claims the event was linked.
      </p>
    </section>
  );
}

function AgeDistribution({ radar }: { radar: FrictionRadarResponse }) {
  const max = Math.max(1, ...radar.unresolved_age_distribution.map((bucket) => bucket.count));
  return (
    <section className="rounded-xl border border-[#E4E7EC] bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold text-[#172554]">How long refunds have remained open</h2>
      <p className="mt-1 text-sm text-[#667085]">Elapsed whole days since each ranked journey’s earliest return request.</p>
      <div className="mt-5 space-y-4">
        {radar.unresolved_age_distribution.map((bucket) => (
          <div key={bucket.bucket}>
            <div className="mb-1.5 flex justify-between text-sm"><span className="text-[#475467]">{bucket.bucket}</span><strong className="text-[#172554]">{bucket.count}</strong></div>
            <div className="h-2.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-rose-500" style={{ width: `${(bucket.count / max) * 100}%` }} /></div>
          </div>
        ))}
      </div>
    </section>
  );
}

function SignalContext({
  radar,
  totalReviews,
  repeatedContactCases,
}: {
  radar: FrictionRadarResponse;
  totalReviews: number;
  repeatedContactCases: number;
}) {
  return (
    <section className="rounded-xl border border-[#E4E7EC] bg-white p-5 shadow-sm">
      <div className="flex gap-3"><span className="rounded-lg bg-teal-50 p-2 text-teal-700"><Headphones className="h-4 w-4" /></span><div><h2 className="text-base font-semibold text-[#172554]">Contact and identity context</h2><p className="mt-1 text-sm text-[#667085]">Signals attached to the ranked queue, not a prediction of customer churn.</p></div></div>
      <div className="mt-5 grid grid-cols-2 gap-3">
        <MiniFact label="Open repeat-contact alerts" value={repeatedContactCases} />
        <MiniFact label="Pending candidate reviews" value={totalReviews} />
      </div>
      <ul className="mt-5 space-y-2">
        {radar.support_contact_channels.length === 0 ? <li className="rounded-lg bg-slate-50 px-3 py-3 text-sm text-[#667085]">No support-contact events are associated with ranked journeys.</li> : radar.support_contact_channels.map((channel) => <li key={channel.channel} className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2.5"><span className="text-sm font-medium text-[#475467]">{CHANNEL_META[channel.channel].label}</span><span className="text-right text-sm"><strong className="text-[#172554]">{channel.count}</strong><span className="ml-2 text-xs text-[#667085]">{channel.share_percent ?? "—"}%</span></span></li>)}
      </ul>
    </section>
  );
}

function MiniFact({ label, value }: { label: string; value: number }) {
  return <div className="rounded-lg bg-slate-50 px-3 py-3"><p className="text-xs text-[#667085]">{label}</p><p className="mt-1 text-xl font-bold text-[#172554]">{value}</p></div>;
}

function DossierSkeleton() {
  return <div className="animate-pulse space-y-6"><div className="h-28 rounded-xl bg-slate-100" /><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }, (_, index) => <div key={index} className="h-28 rounded-xl bg-slate-100" />)}</div><div className="h-64 rounded-2xl bg-slate-100" /><div className="grid gap-6 xl:grid-cols-2"><div className="h-[460px] rounded-xl bg-slate-100" /><div className="h-[460px] rounded-xl bg-slate-100" /></div></div>;
}
