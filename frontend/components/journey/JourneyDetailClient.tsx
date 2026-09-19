"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  AlertTriangle,
  Search,
  Filter,
  ShieldCheck,
  Clock,
  Sparkles,
  Copy,
  Check,
} from "lucide-react";
import { getProfileJourney } from "@/lib/api";
import type {
  ProfileJourneyResponse,
  Channel,
} from "@/lib/types";
import {
  formatShortUuid,
  maskEmail,
  maskPhone,
  formatDateTime,
  formatTimeAgo,
} from "@/lib/formatters";
import {
  EVENT_TYPE_LABELS,
  CHANNEL_META,
} from "@/lib/presenters";
import {
  ChannelBadge,
  IdentityOutcomeBadge,
  SeverityBadge,
} from "@/components/ui/Badge";
import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonBlock } from "@/components/ui/SkeletonBlock";
import { MatchExplanationDrawer } from "./MatchExplanationDrawer";

export function JourneyDetailClient({ profileId }: { profileId: string }) {
  const [data, setData] = useState<ProfileJourneyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState(false);

  // Filter states
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedChannel, setSelectedChannel] = useState<Channel | "all">("all");
  const [selectedOrder, setSelectedOrder] = useState<string | null>(null);

  // Drawer state
  const [inspectEventId, setInspectEventId] = useState<string | null>(null);

  const fetchJourney = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getProfileJourney(profileId);
      setData(res);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load profile journey"
      );
    } finally {
      setLoading(false);
    }
  }, [profileId]);

  useEffect(() => {
    void fetchJourney();
  }, [fetchJourney]);

  const handleCopyId = async (id: string) => {
    try {
      await navigator.clipboard.writeText(id);
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    } catch {
      // Fallback
    }
  };

  // Extract known email & phone from identifiers
  const { email, phone, uniqueChannels } = useMemo(() => {
    if (!data) {
      return { email: null, phone: null, uniqueChannels: [] };
    }

    const emailId = data.profile.identifiers.find((i) => i.type === "email");
    const phoneId = data.profile.identifiers.find((i) => i.type === "phone");

    const channels = Array.from(new Set(data.timeline.map((e) => e.channel)));

    return {
      email: emailId?.display_value ?? null,
      phone: phoneId?.display_value ?? null,
      uniqueChannels: channels,
    };
  }, [data]);

  // Reverse-chronological timeline sorted by occurred_at desc
  const filteredTimeline = useMemo(() => {
    if (!data) return [];

    let events = [...data.timeline].sort(
      (a, b) =>
        new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime()
    );

    if (selectedChannel !== "all") {
      events = events.filter((e) => e.channel === selectedChannel);
    }

    if (selectedOrder) {
      events = events.filter((e) => e.order_id === selectedOrder);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      events = events.filter(
        (e) =>
          e.event_type.toLowerCase().includes(q) ||
          e.channel.toLowerCase().includes(q) ||
          (e.order_id && e.order_id.toLowerCase().includes(q)) ||
          e.evidence_summary.some((msg) => msg.toLowerCase().includes(q))
      );
    }

    return events;
  }, [data, selectedChannel, selectedOrder, searchQuery]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2 text-sm text-[#667085]">
          <SkeletonBlock className="h-4 w-28 rounded" />
        </div>
        <Panel className="p-6">
          <div className="space-y-4">
            <SkeletonBlock className="h-8 w-1/3 rounded" />
            <SkeletonBlock className="h-4 w-1/4 rounded" />
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4">
              <SkeletonBlock className="h-16 rounded" />
              <SkeletonBlock className="h-16 rounded" />
              <SkeletonBlock className="h-16 rounded" />
              <SkeletonBlock className="h-16 rounded" />
            </div>
          </div>
        </Panel>
        <div className="space-y-3">
          <SkeletonBlock className="h-28 w-full rounded-xl" />
          <SkeletonBlock className="h-28 w-full rounded-xl" />
          <SkeletonBlock className="h-28 w-full rounded-xl" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <Link
          href="/customers"
          className="inline-flex items-center gap-1 text-xs font-semibold text-[#4F46E5] hover:underline"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Customer Explorer</span>
        </Link>
        <ErrorState
          title="Customer Profile Not Found"
          message={error || "Profile could not be retrieved from the API."}
          onRetry={fetchJourney}
        />
      </div>
    );
  }

  const { profile, alerts } = data;
  const displayName = profile.display_name?.trim() || "Unknown customer";
  const lastActivity =
    data.timeline.length > 0
      ? data.timeline.reduce((latest, ev) =>
          new Date(ev.occurred_at) > new Date(latest) ? ev.occurred_at : latest,
        data.timeline[0].occurred_at
      )
      : null;

  return (
    <div className="space-y-6">
      {/* Breadcrumb back navigation */}
      <div>
        <Link
          href="/customers"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#667085] hover:text-[#172554] transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Customer Explorer</span>
        </Link>
      </div>

      {/* Profile Header Panel */}
      <Panel className="p-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl sm:text-3xl font-bold text-[#172554] tracking-tight">
                {displayName}
              </h1>
              {alerts.length > 0 && (
                <SeverityBadge severity={alerts[0].severity} />
              )}
            </div>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[#667085] mt-2 font-mono">
              <div className="flex items-center gap-1">
                <span>Profile UUID:</span>
                <span className="font-semibold text-slate-800">{formatShortUuid(profile.id)}</span>
                <button
                  type="button"
                  onClick={() => handleCopyId(profile.id)}
                  title="Copy full UUID"
                  className="p-1 hover:text-slate-900 rounded focus:outline-none focus:ring-1 focus:ring-[#4F46E5]"
                >
                  {copiedId ? (
                    <Check className="w-3 h-3 text-emerald-600" />
                  ) : (
                    <Copy className="w-3 h-3" />
                  )}
                </button>
              </div>

              {email && (
                <div>
                  <span className="text-slate-500 font-sans">Email:</span>{" "}
                  <span className="text-slate-800">{maskEmail(email)}</span>
                </div>
              )}

              {phone && (
                <div>
                  <span className="text-slate-500 font-sans">Phone:</span>{" "}
                  <span className="text-slate-800">{maskPhone(phone)}</span>
                </div>
              )}
            </div>
          </div>

          {/* Quick Stats Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="px-3 py-2 bg-slate-50 border border-[#E4E7EC] rounded-lg">
              <div className="text-[11px] text-[#667085] font-semibold uppercase">Channels</div>
              <div className="text-lg font-bold text-[#172554] tabular-nums mt-0.5">
                {uniqueChannels.length}
              </div>
            </div>

            <div className="px-3 py-2 bg-slate-50 border border-[#E4E7EC] rounded-lg">
              <div className="text-[11px] text-[#667085] font-semibold uppercase">Events</div>
              <div className="text-lg font-bold text-[#172554] tabular-nums mt-0.5">
                {data.timeline.length}
              </div>
            </div>

            <div className="px-3 py-2 bg-slate-50 border border-[#E4E7EC] rounded-lg">
              <div className="text-[11px] text-[#667085] font-semibold uppercase">Open Alerts</div>
              <div
                className={`text-lg font-bold tabular-nums mt-0.5 ${
                  alerts.length > 0 ? "text-[#DC2626]" : "text-emerald-700"
                }`}
              >
                {alerts.length}
              </div>
            </div>

            <div className="px-3 py-2 bg-slate-50 border border-[#E4E7EC] rounded-lg">
              <div className="text-[11px] text-[#667085] font-semibold uppercase">Last Active</div>
              <div className="text-xs font-semibold text-slate-800 mt-1">
                {lastActivity ? formatTimeAgo(lastActivity) : "—"}
              </div>
            </div>
          </div>
        </div>

        {/* Journey synthesis fallback per instructions */}
        <div className="mt-5 pt-4 border-t border-[#E4E7EC] flex items-center gap-2 text-xs text-slate-700 bg-slate-50/70 px-3.5 py-2.5 rounded-lg">
          <Sparkles className="w-4 h-4 text-[#4F46E5] shrink-0" />
          <div>
            <span className="font-semibold text-[#172554]">Journey Status: </span>
            <span>
              {data.timeline.length} events across {uniqueChannels.length} channel
              {uniqueChannels.length === 1 ? "" : "s"}
              {alerts.length > 0
                ? `, with ${alerts.length} open journey alert${alerts.length === 1 ? "" : "s"}.`
                : " with zero active journey alerts."}
            </span>
          </div>
        </div>
      </Panel>

      {/* Active Alerts Section */}
      {alerts.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-[#172554] uppercase tracking-wider flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-[#DC2626]" />
              <span>Active Journey Alerts ({alerts.length})</span>
            </h2>
          </div>

          <div className="grid grid-cols-1 gap-3">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className="p-5 bg-red-50/50 border border-red-200 rounded-xl space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <SeverityBadge severity={alert.severity} />
                    <span className="text-base font-bold text-red-950">
                      {alert.title}
                    </span>
                    {alert.order_id && (
                      <span className="font-mono text-xs px-2 py-0.5 bg-red-100/80 text-red-900 rounded font-semibold border border-red-200">
                        {alert.order_id}
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-red-700 font-mono">
                    {formatTimeAgo(alert.created_at)}
                  </span>
                </div>

                <p className="text-sm text-red-900 leading-relaxed">
                  {alert.description}
                </p>

                <div className="p-3 bg-white/90 border border-red-200/80 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                  <div>
                    <span className="font-bold text-red-900 uppercase text-[11px] tracking-wider block">
                      Recommended Operational Action:
                    </span>
                    <span className="text-slate-800 font-medium mt-0.5">
                      {alert.recommended_action}
                    </span>
                  </div>

                  {alert.order_id && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setSelectedOrder(
                          selectedOrder === alert.order_id ? null : alert.order_id
                        );
                      }}
                      className="shrink-0 bg-red-50 text-red-900 border-red-300 hover:bg-red-100"
                    >
                      {selectedOrder === alert.order_id
                        ? "Clear order filter"
                        : `Filter timeline by ${alert.order_id}`}
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Cross-Channel Timeline Section */}
      <div className="space-y-4">
        {/* Timeline Search & Filter Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-3.5 rounded-xl border border-[#E4E7EC] shadow-2xs">
          <div className="flex-1 max-w-sm relative">
            <Search className="w-4 h-4 text-[#667085] absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="search"
              placeholder="Filter timeline events..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-[#F6F8FB] border border-[#D0D5DD] rounded-md text-[#1E293B] placeholder-[#667085] focus:outline-none focus:ring-2 focus:ring-[#4F46E5]"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-[#667085] font-semibold flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" />
              <span>Channel:</span>
            </span>
            <button
              type="button"
              onClick={() => setSelectedChannel("all")}
              className={`px-2.5 py-1 rounded-full font-medium transition-colors ${
                selectedChannel === "all"
                  ? "bg-[#4F46E5] text-white"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              All ({data.timeline.length})
            </button>
            {(["web", "mobile_app", "call_center", "physical_store"] as Channel[]).map(
              (ch) => {
                const count = data.timeline.filter((e) => e.channel === ch).length;
                if (count === 0) return null;
                const isSelected = selectedChannel === ch;
                return (
                  <button
                    key={ch}
                    type="button"
                    onClick={() =>
                      setSelectedChannel(isSelected ? "all" : ch)
                    }
                    className={`px-2.5 py-1 rounded-full font-medium transition-colors ${
                      isSelected
                        ? "bg-[#4F46E5] text-white"
                        : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                    }`}
                  >
                    {CHANNEL_META[ch].label} ({count})
                  </button>
                );
              }
            )}

            {selectedOrder && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 text-xs font-mono font-medium">
                <span>Order: {selectedOrder}</span>
                <button
                  onClick={() => setSelectedOrder(null)}
                  className="hover:text-indigo-900 font-bold ml-1"
                >
                  ×
                </button>
              </span>
            )}
          </div>
        </div>

        {/* Timeline Events List */}
        {filteredTimeline.length === 0 ? (
          <EmptyState
            title="No matching timeline events"
            description={
              searchQuery || selectedChannel !== "all" || selectedOrder
                ? "No events matched the selected filters."
                : "No customer interaction events have been recorded."
            }
            action={
              (searchQuery || selectedChannel !== "all" || selectedOrder) && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSearchQuery("");
                    setSelectedChannel("all");
                    setSelectedOrder(null);
                  }}
                >
                  Reset filters
                </Button>
              )
            }
          />
        ) : (
          <div className="relative pl-6 sm:pl-8 space-y-4 before:content-[''] before:absolute before:left-3 sm:before:left-4 before:top-3 before:bottom-3 before:w-0.5 before:bg-[#E4E7EC]">
            {filteredTimeline.map((event) => {
              const eventTitle =
                EVENT_TYPE_LABELS[event.event_type] ||
                event.event_type.replace(/_/g, " ");

              return (
                <div
                  key={event.event_id}
                  className="relative group bg-white p-5 rounded-xl border border-[#E4E7EC] shadow-2xs hover:shadow-xs transition-shadow"
                >
                  {/* Timeline indicator node */}
                  <div className="absolute -left-6 sm:-left-8 top-6 -translate-x-1/2 w-3.5 h-3.5 rounded-full border-2 border-white bg-[#4F46E5] shadow-xs" />

                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-2">
                    <div className="flex flex-wrap items-center gap-2.5">
                      <ChannelBadge channel={event.channel} />
                      <h3 className="text-base font-bold text-[#172554]">
                        {eventTitle}
                      </h3>
                      {event.order_id && (
                        <span className="font-mono text-xs px-2 py-0.5 bg-slate-100 text-slate-800 rounded font-semibold border border-[#E4E7EC]">
                          {event.order_id}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2 text-xs text-[#667085]">
                      <Clock className="w-3.5 h-3.5" />
                      <time dateTime={event.occurred_at}>
                        {formatDateTime(event.occurred_at)}
                      </time>
                      <span className="text-slate-400">·</span>
                      <span className="font-medium">
                        {formatTimeAgo(event.occurred_at)}
                      </span>
                    </div>
                  </div>

                  {/* Decision & Score Row */}
                  <div className="flex flex-wrap items-center justify-between gap-3 py-2 border-y border-slate-100 my-3 text-xs">
                    <div className="flex items-center gap-2">
                      <span className="text-[#667085] font-semibold">Outcome:</span>
                      <IdentityOutcomeBadge outcome={event.decision} />
                      <span className="text-slate-400">|</span>
                      <span className="text-[#667085] font-semibold">Identity Score:</span>
                      <span className="font-bold text-[#172554] tabular-nums font-mono">
                        {event.score} / 100
                      </span>
                    </div>

                    {/* "Why linked?" Evidence Trigger Button */}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setInspectEventId(event.event_id)}
                      icon={<ShieldCheck className="w-3.5 h-3.5 text-[#4F46E5]" />}
                      className="text-xs font-semibold text-[#4F46E5] hover:bg-indigo-50 border-indigo-200"
                    >
                      Why linked?
                    </Button>
                  </div>

                  {/* Evidence summary notes */}
                  {event.evidence_summary.length > 0 && (
                    <div className="mt-2 text-xs text-slate-600 space-y-1">
                      {event.evidence_summary.map((summary, idx) => (
                        <div key={idx} className="flex items-start gap-1.5">
                          <span className="text-[#4F46E5] font-bold mt-0.5">•</span>
                          <span>{summary}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Match Explanation Drawer Modal */}
      {inspectEventId && (
        <MatchExplanationDrawer
          canonicalEventId={inspectEventId}
          onClose={() => setInspectEventId(null)}
        />
      )}
    </div>
  );
}
