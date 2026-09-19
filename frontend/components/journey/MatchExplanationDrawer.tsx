"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  ShieldCheck,
  AlertTriangle,
  Code,
  FileText,
  HelpCircle,
  Award,
} from "lucide-react";
import { getMatchExplanation } from "@/lib/api";
import type { MatchExplanationResponse } from "@/lib/types";
import { IdentityOutcomeBadge, ChannelBadge } from "@/components/ui/Badge";
import { JsonViewer } from "@/components/ui/JsonViewer";
import { SkeletonBlock } from "@/components/ui/SkeletonBlock";
import { ErrorState } from "@/components/ui/ErrorState";
import { formatDateTime } from "@/lib/formatters";

interface MatchExplanationDrawerProps {
  canonicalEventId: string | null;
  onClose: () => void;
}

export function MatchExplanationDrawer({
  canonicalEventId,
  onClose,
}: MatchExplanationDrawerProps) {
  const [data, setData] = useState<MatchExplanationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"explanation" | "normalized" | "raw">("explanation");

  useEffect(() => {
    if (!canonicalEventId) {
      return;
    }

    let isCurrent = true;
    setData(null);
    setError(null);
    setLoading(true);

    getMatchExplanation(canonicalEventId)
      .then((res) => {
        if (isCurrent) setData(res);
      })
      .catch((err) => {
        if (isCurrent) {
          setError(
            err instanceof Error ? err.message : "Failed to load match explanation"
          );
        }
      })
      .finally(() => {
        if (isCurrent) setLoading(false);
      });

    return () => {
      isCurrent = false;
    };
  }, [canonicalEventId]);

  // Handle Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!canonicalEventId) return null;

  return (
    <div
      className="fixed inset-0 z-50 overflow-hidden bg-slate-900/50 backdrop-blur-xs flex justify-end"
      role="dialog"
      aria-modal="true"
      aria-labelledby="drawer-title"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl bg-white h-full shadow-2xl flex flex-col animate-in slide-in-from-right duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div className="px-6 py-4 border-b border-[#E4E7EC] flex items-center justify-between bg-slate-50/70">
          <div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-[#4F46E5]" />
              <h2 id="drawer-title" className="text-base font-bold text-[#172554]">
                Match Explanation & Evidence
              </h2>
            </div>
            <p className="text-xs font-mono text-[#667085] mt-0.5">
              Event ID: {canonicalEventId}
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close match explanation drawer"
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors focus:outline-none focus:ring-2 focus:ring-[#4F46E5]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab navigation */}
        <div className="px-6 border-b border-[#E4E7EC] flex gap-6 bg-white text-xs font-medium">
          <button
            type="button"
            onClick={() => setActiveTab("explanation")}
            className={`py-3 flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === "explanation"
                ? "border-[#4F46E5] text-[#4F46E5] font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <HelpCircle className="w-4 h-4" />
            <span>Decision Explanation</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("normalized")}
            className={`py-3 flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === "normalized"
                ? "border-[#4F46E5] text-[#4F46E5] font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>Normalized Fields</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("raw")}
            className={`py-3 flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === "raw"
                ? "border-[#4F46E5] text-[#4F46E5] font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <Code className="w-4 h-4" />
            <span>Raw Payload</span>
          </button>
        </div>

        {/* Drawer Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="space-y-4 py-4">
              <SkeletonBlock className="h-8 w-1/2 rounded" />
              <SkeletonBlock className="h-24 w-full rounded" />
              <SkeletonBlock className="h-40 w-full rounded" />
            </div>
          ) : error ? (
            <ErrorState
              title="Could not retrieve match explanation"
              message={error}
              onRetry={() => {
                setLoading(true);
                getMatchExplanation(canonicalEventId)
                  .then(setData)
                  .catch((e) => setError(e.message))
                  .finally(() => setLoading(false));
              }}
            />
          ) : data ? (
            <>
              {activeTab === "explanation" && (
                <div className="space-y-6">
                  {/* Decision overview banner */}
                  <div className="p-4 bg-slate-50 rounded-xl border border-[#E4E7EC] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                      <div className="text-xs text-[#667085] uppercase tracking-wider font-semibold">
                        Identity Decision
                      </div>
                      <div className="mt-1 flex items-center gap-2">
                        <IdentityOutcomeBadge outcome={data.decision} />
                        <ChannelBadge channel={data.event_context.channel} />
                      </div>
                    </div>

                    <div className="sm:text-right">
                      <div className="text-xs text-[#667085] uppercase tracking-wider font-semibold">
                        Identity Score
                      </div>
                      <div className="text-2xl font-bold text-[#172554] tabular-nums mt-0.5">
                        {data.score}
                        <span className="text-xs font-normal text-[#667085] ml-1">
                          / 100
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Conflict warnings (if any) */}
                  {data.conflicts.length > 0 && (
                    <div className="p-4 bg-red-50 border border-red-200 rounded-xl space-y-2">
                      <div className="flex items-center gap-2 text-red-900 font-semibold text-sm">
                        <AlertTriangle className="w-4 h-4 text-red-600" />
                        <span>Identifier Conflicts Detected ({data.conflicts.length})</span>
                      </div>
                      <p className="text-xs text-red-700">
                        A strong identifier conflict blocks automatic linking regardless of matching score.
                      </p>
                      <ul className="list-disc list-inside text-xs text-red-800 space-y-1">
                        {data.conflicts.map((c, idx) => (
                          <li key={idx}>{c.message || JSON.stringify(c)}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Evidence List */}
                  <div>
                    <h3 className="text-sm font-semibold text-[#172554] mb-3 flex items-center gap-2">
                      <Award className="w-4 h-4 text-[#4F46E5]" />
                      <span>Evidence Breakdown</span>
                    </h3>
                    {data.evidence.length === 0 ? (
                      <div className="text-xs text-[#667085] italic p-3 bg-slate-50 rounded-lg border border-[#E4E7EC]">
                        No positive matching evidence recorded for this event.
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {data.evidence.map((item, idx) => (
                          <div
                            key={idx}
                            className="p-3 bg-white rounded-lg border border-[#E4E7EC] flex items-center justify-between text-xs shadow-2xs"
                          >
                            <div className="space-y-0.5">
                              <div className="font-medium text-slate-900">
                                {item.message || item.rule || "Identifier match"}
                              </div>
                              {item.rule && (
                                <div className="text-[11px] font-mono text-slate-500">
                                  Rule: {item.rule}
                                </div>
                              )}
                            </div>
                            {item.points !== undefined && (
                              <span className="px-2 py-1 bg-emerald-50 text-emerald-700 font-semibold font-mono rounded border border-emerald-200">
                                +{item.points} pts
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Decision Thresholds */}
                  {data.thresholds && Object.keys(data.thresholds).length > 0 && (
                    <div className="p-3 bg-slate-50 rounded-lg border border-[#E4E7EC] text-xs space-y-2">
                      <div className="font-semibold text-slate-700">
                        Configured Score Thresholds
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-slate-600">
                        {Object.entries(data.thresholds).map(([key, val]) => (
                          <div key={key} className="flex justify-between">
                            <span className="capitalize">{key.replace(/_/g, " ")}:</span>
                            <span className="font-mono font-medium">{val}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Alternative candidates if evaluated */}
                  {data.alternative_candidates.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-[#172554] mb-2">
                        Other Evaluated Candidates ({data.alternative_candidates.length})
                      </h3>
                      <div className="space-y-2">
                        {data.alternative_candidates.map((alt, idx) => (
                          <div
                            key={idx}
                            className="p-3 bg-slate-50 rounded-lg border border-[#E4E7EC] flex justify-between text-xs font-mono"
                          >
                            <span>Profile: {alt.profile_id}</span>
                            <span className="font-bold">Score: {alt.score}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeTab === "normalized" && (
                <div className="space-y-4">
                  <div className="text-xs text-[#667085]">
                    Canonical fields extracted and normalized according to contract rules.
                  </div>
                  <div className="p-4 bg-slate-50 rounded-xl border border-[#E4E7EC] space-y-2 text-xs">
                    <div className="grid grid-cols-3 gap-2 py-1 border-b border-slate-200">
                      <span className="font-semibold text-slate-600">Occurred At (UTC):</span>
                      <span className="col-span-2 font-mono">
                        {formatDateTime(data.event_context.occurred_at)}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 py-1 border-b border-slate-200">
                      <span className="font-semibold text-slate-600">Channel:</span>
                      <span className="col-span-2 font-mono">
                        {data.event_context.channel}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 py-1 border-b border-slate-200">
                      <span className="font-semibold text-slate-600">Event Type:</span>
                      <span className="col-span-2 font-mono">
                        {data.event_context.event_type}
                      </span>
                    </div>
                    {data.selected_profile_id && (
                      <div className="grid grid-cols-3 gap-2 py-1 border-b border-slate-200">
                        <span className="font-semibold text-slate-600">Linked Profile ID:</span>
                        <span className="col-span-2 font-mono break-all text-[#4F46E5]">
                          {data.selected_profile_id}
                        </span>
                      </div>
                    )}
                  </div>

                  <div>
                    <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                      Full Normalized Payload
                    </h4>
                    <JsonViewer data={data.normalized_fields} />
                  </div>
                </div>
              )}

              {activeTab === "raw" && (
                <div className="space-y-4">
                  <div className="text-xs text-[#667085]">
                    Original raw ingestion envelope preserved verbatim for auditability.
                  </div>
                  <JsonViewer data={data.raw_payload} />
                </div>
              )}
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
