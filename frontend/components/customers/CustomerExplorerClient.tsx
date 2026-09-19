"use client";

import React, { useState, useEffect, useCallback, useTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Search,
  Users,
  ArrowRight,
  Activity,
  AlertCircle,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
} from "lucide-react";
import { getProfiles, getProfileJourney } from "@/lib/api";
import type {
  ProfileListResponse,
  ProfileJourneyResponse,
} from "@/lib/types";
import {
  formatShortUuid,
  maskEmail,
  maskPhone,
  formatTimeAgo,
} from "@/lib/formatters";
import { ChannelBadge, SeverityBadge } from "@/components/ui/Badge";
import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { TableSkeleton, SkeletonBlock } from "@/components/ui/SkeletonBlock";

export function CustomerExplorerClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [, startTransition] = useTransition();

  const initialSearch = searchParams.get("search") || "";
  const initialPage = parseInt(searchParams.get("page") || "1", 10);

  const [searchQuery, setSearchQuery] = useState(initialSearch);
  const [debouncedSearch, setDebouncedSearch] = useState(initialSearch);
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [pageSize] = useState(15);

  const [data, setData] = useState<ProfileListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selected profile for side preview
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<ProfileJourneyResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery.trim());
      setCurrentPage(1);
    }, 350);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Sync with URL params
  useEffect(() => {
    const params = new URLSearchParams();
    if (debouncedSearch) params.set("search", debouncedSearch);
    if (currentPage > 1) params.set("page", String(currentPage));

    const newUrl = `/customers${params.toString() ? `?${params.toString()}` : ""}`;
    startTransition(() => {
      router.replace(newUrl, { scroll: false });
    });
  }, [debouncedSearch, currentPage, router]);

  // Fetch profiles list
  const fetchProfiles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getProfiles({
        page: currentPage,
        page_size: pageSize,
        search: debouncedSearch || undefined,
      });
      setData(res);

      // Auto-select first item if none selected
      if (res.items.length > 0 && !selectedProfileId) {
        setSelectedProfileId(res.items[0].profile_id);
      } else if (res.items.length === 0) {
        setSelectedProfileId(null);
        setPreviewData(null);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load profiles from API"
      );
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, debouncedSearch, selectedProfileId]);

  useEffect(() => {
    fetchProfiles();
  }, [fetchProfiles]);

  // Fetch preview when selectedProfileId changes
  useEffect(() => {
    if (!selectedProfileId) {
      return;
    }

    let isCurrent = true;
    setPreviewLoading(true);
    setPreviewData(null);
    getProfileJourney(selectedProfileId)
      .then((res) => {
        if (isCurrent) setPreviewData(res);
      })
      .catch(() => {
        if (isCurrent) setPreviewData(null);
      })
      .finally(() => {
        if (isCurrent) setPreviewLoading(false);
      });

    return () => {
      isCurrent = false;
    };
  }, [selectedProfileId]);

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 1;

  return (
    <div className="space-y-6">
      {/* Header with search */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[#172554] tracking-tight">
            Customer Explorer
          </h1>
          <p className="text-sm text-[#667085] mt-0.5">
            Search unified customer profiles, verified cross-channel identifiers, and journeys
          </p>
        </div>

        <div className="w-full sm:w-80">
          <div className="relative">
            <Search className="w-4 h-4 text-[#667085] absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="search"
              placeholder="Search by name, email, phone, or ORD-204..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-sm bg-white border border-[#D0D5DD] rounded-lg text-[#1E293B] placeholder-[#667085] focus:outline-none focus:ring-2 focus:ring-[#4F46E5] shadow-2xs"
            />
          </div>
        </div>
      </div>

      {error ? (
        <ErrorState
          title="Could not connect to profiles API"
          message={error}
          onRetry={fetchProfiles}
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
          {/* Main Profiles Table (2 cols) */}
          <div className="lg:col-span-2 space-y-4">
            <Panel className="p-0 overflow-hidden">
              <div className="px-5 py-3.5 border-b border-[#E4E7EC] bg-slate-50/70 flex items-center justify-between text-xs font-semibold text-[#667085] uppercase tracking-wider">
                <span>
                  {loading
                    ? "Searching profiles..."
                    : `Resolved Profiles (${data?.total ?? 0})`}
                </span>
                {debouncedSearch && (
                  <span className="font-normal normal-case text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
                    Filter: &quot;{debouncedSearch}&quot;
                  </span>
                )}
              </div>

              {loading ? (
                <TableSkeleton rows={6} />
              ) : !data || data.items.length === 0 ? (
                <EmptyState
                  title="No customer profiles found"
                  description={
                    debouncedSearch
                      ? `No profiles matched "${debouncedSearch}". Check for spelling or search by order reference (e.g. ORD-204).`
                      : "No customer records have been ingested into the system yet."
                  }
                  icon={<Users className="w-6 h-6" />}
                  action={
                    debouncedSearch ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSearchQuery("")}
                      >
                        Clear search
                      </Button>
                    ) : undefined
                  }
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-[#E4E7EC] bg-white text-xs font-medium text-[#667085]">
                        <th className="py-3 px-4">Customer</th>
                        <th className="py-3 px-4">Verified Identifiers</th>
                        <th className="py-3 px-4">Channels</th>
                        <th className="py-3 px-4">Events</th>
                        <th className="py-3 px-4">Last Seen</th>
                        <th className="py-3 px-4 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#E4E7EC] text-sm">
                      {data.items.map((profile) => {
                        const isSelected = selectedProfileId === profile.profile_id;
                        const displayName =
                          profile.display_name?.trim() || "Unknown customer";

                        return (
                          <tr
                            key={profile.profile_id}
                            onClick={() => setSelectedProfileId(profile.profile_id)}
                            className={`cursor-pointer transition-colors ${
                              isSelected
                                ? "bg-indigo-50/60 font-medium"
                                : "hover:bg-slate-50"
                            }`}
                          >
                            <td className="py-3 px-4">
                              <div className="font-semibold text-[#172554]">
                                {displayName}
                              </div>
                              <div className="text-xs font-mono text-[#667085]">
                                ID: {formatShortUuid(profile.profile_id)}
                              </div>
                            </td>

                            <td className="py-3 px-4 text-xs space-y-1">
                              {profile.email && (
                                <div className="text-slate-700">
                                  {maskEmail(profile.email)}
                                </div>
                              )}
                              {profile.phone && (
                                <div className="text-slate-700">
                                  {maskPhone(profile.phone)}
                                </div>
                              )}
                              {!profile.email && !profile.phone && (
                                <span className="text-slate-400 italic">No contact</span>
                              )}
                            </td>

                            <td className="py-3 px-4">
                              <div className="flex flex-wrap gap-1">
                                {profile.channels_used.map((ch) => (
                                  <ChannelBadge key={ch} channel={ch} />
                                ))}
                              </div>
                            </td>

                            <td className="py-3 px-4 tabular-nums text-slate-700 font-semibold">
                              {profile.event_count}
                            </td>

                            <td className="py-3 px-4 text-xs text-[#667085] whitespace-nowrap">
                              {formatTimeAgo(profile.last_seen_at)}
                            </td>

                            <td className="py-3 px-4 text-right">
                              <a
                                href={`/customers/${profile.profile_id}`}
                                onClick={(e) => e.stopPropagation()}
                                className="inline-flex items-center gap-1 text-xs font-semibold text-[#4F46E5] hover:text-indigo-800 hover:underline"
                              >
                                <span>Journey</span>
                                <ArrowRight className="w-3.5 h-3.5" />
                              </a>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Pagination controls */}
              {data && data.total > pageSize && (
                <div className="px-5 py-3 border-t border-[#E4E7EC] bg-white flex items-center justify-between text-xs text-[#667085]">
                  <div>
                    Showing{" "}
                    <span className="font-medium text-slate-900">
                      {(currentPage - 1) * pageSize + 1}
                    </span>{" "}
                    to{" "}
                    <span className="font-medium text-slate-900">
                      {Math.min(currentPage * pageSize, data.total)}
                    </span>{" "}
                    of{" "}
                    <span className="font-medium text-slate-900">
                      {data.total}
                    </span>{" "}
                    profiles
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={currentPage <= 1}
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      icon={<ChevronLeft className="w-3.5 h-3.5" />}
                    >
                      Previous
                    </Button>
                    <span className="px-2 font-medium">
                      Page {currentPage} of {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={currentPage >= totalPages}
                      onClick={() =>
                        setCurrentPage((p) => Math.min(totalPages, p + 1))
                      }
                      icon={<ChevronRight className="w-3.5 h-3.5" />}
                      className="flex-row-reverse"
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </Panel>
          </div>

          {/* Side Preview Panel (1 col) */}
          <div className="space-y-4 sticky top-20">
            <Panel
              header={
                <div className="flex items-center justify-between w-full">
                  <span className="text-xs font-semibold text-[#667085] uppercase tracking-wider">
                    Profile Preview
                  </span>
                  {selectedProfileId && (
                    <a
                      href={`/customers/${selectedProfileId}`}
                      className="text-xs text-[#4F46E5] hover:underline inline-flex items-center gap-1 font-semibold"
                    >
                      <span>Open full journey</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                </div>
              }
            >
              {!selectedProfileId ? (
                <div className="text-center py-8 text-[#667085] text-sm">
                  Select a customer from the table to preview verified identifiers and alerts.
                </div>
              ) : previewLoading ? (
                <div className="space-y-4 py-2">
                  <SkeletonBlock className="h-6 w-3/4 rounded" />
                  <SkeletonBlock className="h-4 w-1/2 rounded" />
                  <SkeletonBlock className="h-20 w-full rounded" />
                  <SkeletonBlock className="h-24 w-full rounded" />
                </div>
              ) : previewData ? (
                <div className="space-y-5">
                  <div>
                    <div className="text-lg font-bold text-[#172554]">
                      {previewData.profile.display_name?.trim() || "Unknown customer"}
                    </div>
                    <div className="text-xs font-mono text-[#667085] mt-0.5">
                      UUID: {previewData.profile.id}
                    </div>
                  </div>

                  {/* Alerts (if any) */}
                  {previewData.alerts.length > 0 && (
                    <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-amber-900 flex items-center gap-1">
                          <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                          <span>Active Journey Alerts ({previewData.alerts.length})</span>
                        </span>
                        <SeverityBadge severity={previewData.alerts[0].severity} />
                      </div>
                      <div className="text-xs font-semibold text-amber-950">
                        {previewData.alerts[0].title}
                      </div>
                      <div className="text-[11px] text-amber-800 line-clamp-2">
                        {previewData.alerts[0].description}
                      </div>
                    </div>
                  )}

                  {/* Verified identifiers */}
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-wider text-[#667085] mb-2 flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-[#0F766E]" />
                      <span>Verified Identifiers</span>
                    </div>
                    <div className="space-y-1.5 text-xs bg-slate-50 p-3 rounded-lg border border-[#E4E7EC]">
                      {previewData.profile.identifiers.length === 0 ? (
                        <span className="text-slate-400 italic">No identifiers stored</span>
                      ) : (
                        previewData.profile.identifiers.map((id, idx) => (
                          <div
                            key={idx}
                            className="flex items-center justify-between text-slate-800"
                          >
                            <span className="font-mono text-slate-500 uppercase text-[11px]">
                              {id.type}
                            </span>
                            <span className="font-mono font-medium">
                              {id.type === "email"
                                ? maskEmail(id.display_value)
                                : id.type === "phone"
                                ? maskPhone(id.display_value)
                                : id.display_value}
                            </span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Recent events count */}
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-wider text-[#667085] mb-2 flex items-center gap-1.5">
                      <Activity className="w-3.5 h-3.5 text-[#4F46E5]" />
                      <span>Recent Events ({previewData.timeline.length})</span>
                    </div>
                    <div className="space-y-2">
                      {previewData.timeline.slice(-3).reverse().map((ev) => (
                        <div
                          key={ev.event_id}
                          className="p-2.5 rounded-lg border border-[#E4E7EC] bg-white flex items-center justify-between text-xs"
                        >
                          <div>
                            <div className="font-medium text-slate-900">
                              {ev.event_type.replace(/_/g, " ")}
                            </div>
                            <div className="text-[11px] text-slate-500">
                              {formatTimeAgo(ev.occurred_at)}
                            </div>
                          </div>
                          <ChannelBadge channel={ev.channel} />
                        </div>
                      ))}
                    </div>
                  </div>

                  <a
                    href={`/customers/${previewData.profile.id}`}
                    className="block"
                  >
                    <Button
                      variant="primary"
                      className="w-full"
                      icon={<ArrowRight className="w-4 h-4" />}
                    >
                      View full customer timeline
                    </Button>
                  </a>
                </div>
              ) : (
                <div className="text-center py-6 text-xs text-[#667085]">
                  Unable to load preview details.
                </div>
              )}
            </Panel>
          </div>
        </div>
      )}
    </div>
  );
}
