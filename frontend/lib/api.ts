/**
 * Centralized API Client for JourneyLens.
 * Conforms to docs/05_API_CONTRACT.md and docs/12_STITCH_FRONTEND_IMPLEMENTATION_GUIDE.md.
 */

import type {
  AlertListResponse,
  AnalyticsOverview,
  ApiErrorDetail,
  Channel,
  ChannelsResponse,
  DashboardUpdatesResponse,
  DemoResetResponse,
  DemoRunResponse,
  DemoStartRequest,
  DemoStartResponse,
  HealthResult,
  MatchExplanationResponse,
  PipelineEventDetailResponse,
  PipelineEventListResponse,
  PipelineOverviewResponse,
  PipelineUpdatesResponse,
  IdentityOutcome,
  ProcessingStatus,
  ProfileJourneyResponse,
  ProfileListResponse,
  ResolveReviewRequest,
  ResolveReviewResponse,
  ReviewListResponse,
} from "./types";

export class ApiClientError extends Error {
  public readonly code: string;
  public readonly status: number;
  public readonly stage: string;
  public readonly rawEventId?: string | null;
  public readonly details?: Record<string, unknown>;

  constructor(status: number, errorDetail: ApiErrorDetail) {
    super(errorDetail.message || `API request failed with status ${status}`);
    this.name = "ApiClientError";
    this.status = status;
    this.code = errorDetail.code || `HTTP_${status}`;
    this.stage = errorDetail.stage || "client";
    this.rawEventId = errorDetail.raw_event_id;
    this.details = errorDetail.details;
  }
}

export function getBaseUrl(): string {
  if (typeof window === "undefined") {
    // Server-side context (Node.js/Next.js server component)
    return (
      process.env.BACKEND_INTERNAL_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      "http://localhost:8000"
    );
  }
  // Client-side browser context
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    if (response.status === 204) {
      return {} as T;
    }
    return (await response.json()) as T;
  }

  let errorDetail: ApiErrorDetail;
  try {
    const errorBody = await response.json();
    if (errorBody && typeof errorBody === "object" && "error" in errorBody) {
      errorDetail = errorBody.error;
    } else if (errorBody && typeof errorBody === "object" && "detail" in errorBody) {
      // Handle standard FastAPI HTTPException or validation error (gap BE-FE-07)
      const detailStr =
        typeof errorBody.detail === "string"
          ? errorBody.detail
          : JSON.stringify(errorBody.detail);
      errorDetail = {
        code: response.status === 404 ? "NOT_FOUND" : `HTTP_${response.status}`,
        message: detailStr,
        stage: "api",
      };
    } else {
      errorDetail = {
        code: `HTTP_${response.status}`,
        message: response.statusText || `Request failed with status ${response.status}`,
        stage: "api",
      };
    }
  } catch {
    errorDetail = {
      code: `HTTP_${response.status}`,
      message: response.statusText || `Request failed with status ${response.status}`,
      stage: "transport",
    };
  }

  throw new ApiClientError(response.status, errorDetail);
}

export async function getHealth(): Promise<HealthResult> {
  const baseUrl = getBaseUrl();
  try {
    const response = await fetch(`${baseUrl}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3_000),
    });
    if (!response.ok) {
      return { ok: false, label: `unavailable (${response.status})` };
    }
    return { ok: true, label: "connected" };
  } catch {
    return { ok: false, label: "waiting for API" };
  }
}

export async function getProfiles(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  signal?: AbortSignal;
}): Promise<ProfileListResponse> {
  const baseUrl = getBaseUrl();
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.search && params.search.trim()) {
    searchParams.set("search", params.search.trim());
  }

  const query = searchParams.toString();
  const url = `${baseUrl}/api/profiles${query ? `?${query}` : ""}`;

  const response = await fetch(url, {
    cache: "no-store",
    signal: params?.signal ?? AbortSignal.timeout(5_000),
  });

  return handleResponse<ProfileListResponse>(response);
}

export async function getProfileJourney(
  profileId: string,
  signal?: AbortSignal
): Promise<ProfileJourneyResponse> {
  const baseUrl = getBaseUrl();
  const response = await fetch(`${baseUrl}/api/profiles/${encodeURIComponent(profileId)}`, {
    cache: "no-store",
    signal: signal ?? AbortSignal.timeout(5_000),
  });

  return handleResponse<ProfileJourneyResponse>(response);
}

export async function getMatchExplanation(
  canonicalEventId: string,
  signal?: AbortSignal
): Promise<MatchExplanationResponse> {
  const baseUrl = getBaseUrl();
  const response = await fetch(
    `${baseUrl}/api/events/${encodeURIComponent(canonicalEventId)}/match-explanation`,
    {
      cache: "no-store",
      signal: signal ?? AbortSignal.timeout(5_000),
    }
  );

  return handleResponse<MatchExplanationResponse>(response);
}

export async function getAlerts(signal?: AbortSignal): Promise<AlertListResponse> {
  const baseUrl = getBaseUrl();
  const response = await fetch(`${baseUrl}/api/alerts`, {
    cache: "no-store",
    signal: signal ?? AbortSignal.timeout(5_000),
  });

  return handleResponse<AlertListResponse>(response);
}

export async function getAnalyticsOverview(signal?: AbortSignal): Promise<AnalyticsOverview> {
  const baseUrl = getBaseUrl();
  const response = await fetch(`${baseUrl}/api/analytics/overview`, {
    cache: "no-store",
    signal: signal ?? AbortSignal.timeout(5_000),
  });

  return handleResponse<AnalyticsOverview>(response);
}

export async function getAnalyticsChannels(signal?: AbortSignal): Promise<ChannelsResponse> {
  const baseUrl = getBaseUrl();
  const response = await fetch(`${baseUrl}/api/analytics/channels`, {
    cache: "no-store",
    signal: signal ?? AbortSignal.timeout(5_000),
  });

  return handleResponse<ChannelsResponse>(response);
}

export async function getReviews(signal?: AbortSignal): Promise<ReviewListResponse> {
  const baseUrl = getBaseUrl();
  const response = await fetch(`${baseUrl}/api/reviews`, {
    cache: "no-store",
    signal: signal ?? AbortSignal.timeout(5_000),
  });

  return handleResponse<ReviewListResponse>(response);
}

export async function resolveReview(
  matchDecisionId: string,
  payload: ResolveReviewRequest,
  signal?: AbortSignal
): Promise<ResolveReviewResponse> {
  const baseUrl = getBaseUrl();
  const response = await fetch(
    `${baseUrl}/api/reviews/${encodeURIComponent(matchDecisionId)}/resolve`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: signal ?? AbortSignal.timeout(5_000),
    }
  );

  return handleResponse<ResolveReviewResponse>(response);
}

export async function getDashboardUpdates(
  since?: string,
  signal?: AbortSignal
): Promise<DashboardUpdatesResponse> {
  const baseUrl = getBaseUrl();
  const searchParams = new URLSearchParams();
  if (since) searchParams.set("since", since);

  const query = searchParams.toString();
  const url = `${baseUrl}/api/dashboard/updates${query ? `?${query}` : ""}`;

  const response = await fetch(url, {
    cache: "no-store",
    signal: signal ?? AbortSignal.timeout(5_000),
  });

  return handleResponse<DashboardUpdatesResponse>(response);
}

export async function getPipelineOverview(params?: {
  limit?: number;
  signal?: AbortSignal;
}): Promise<PipelineOverviewResponse> {
  const baseUrl = getBaseUrl();
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set("limit", String(params.limit));

  const query = searchParams.toString();
  const response = await fetch(`${baseUrl}/api/pipeline/overview${query ? `?${query}` : ""}`, {
    cache: "no-store",
    signal: params?.signal ?? AbortSignal.timeout(5_000),
  });

  return handleResponse<PipelineOverviewResponse>(response);
}

export async function getPipelineEvents(params?: {
  limit?: number;
  cursor?: string;
  channel?: Channel;
  processingStatus?: ProcessingStatus;
  identityOutcome?: IdentityOutcome;
  sourceEventId?: string;
  signal?: AbortSignal;
}): Promise<PipelineEventListResponse> {
  const baseUrl = getBaseUrl();
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.cursor) searchParams.set("cursor", params.cursor);
  if (params?.channel) searchParams.set("channel", params.channel);
  if (params?.processingStatus) {
    searchParams.set("processing_status", params.processingStatus);
  }
  if (params?.identityOutcome) {
    searchParams.set("identity_outcome", params.identityOutcome);
  }
  if (params?.sourceEventId?.trim()) {
    searchParams.set("source_event_id", params.sourceEventId.trim());
  }

  const query = searchParams.toString();
  const response = await fetch(`${baseUrl}/api/pipeline/events${query ? `?${query}` : ""}`, {
    cache: "no-store",
    signal: params?.signal ?? AbortSignal.timeout(5_000),
  });

  return handleResponse<PipelineEventListResponse>(response);
}

export async function getPipelineEventDetail(
  rawEventId: string,
  signal?: AbortSignal
): Promise<PipelineEventDetailResponse> {
  const baseUrl = getBaseUrl();
  const response = await fetch(
    `${baseUrl}/api/pipeline/events/${encodeURIComponent(rawEventId)}`,
    {
      cache: "no-store",
      signal: signal ?? AbortSignal.timeout(5_000),
    }
  );

  return handleResponse<PipelineEventDetailResponse>(response);
}

export async function getPipelineUpdates(params: {
  cursor: string;
  upperBoundCursor?: string;
  limit?: number;
  signal?: AbortSignal;
}): Promise<PipelineUpdatesResponse> {
  const baseUrl = getBaseUrl();
  const searchParams = new URLSearchParams({ cursor: params.cursor });
  if (params.upperBoundCursor) {
    searchParams.set("upper_bound_cursor", params.upperBoundCursor);
  }
  if (params.limit) searchParams.set("limit", String(params.limit));

  const response = await fetch(`${baseUrl}/api/pipeline/updates?${searchParams.toString()}`, {
    cache: "no-store",
    signal: params.signal ?? AbortSignal.timeout(5_000),
  });

  return handleResponse<PipelineUpdatesResponse>(response);
}

export async function startDemo(
  scenario = "unresolved_refund_riya",
  intervalSeconds = 1.5,
  signal?: AbortSignal
): Promise<DemoStartResponse> {
  const baseUrl = getBaseUrl();
  const payload: DemoStartRequest = {
    scenario,
    interval_seconds: intervalSeconds,
  };

  const response = await fetch(`${baseUrl}/api/demo/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: signal ?? AbortSignal.timeout(5_000),
  });

  return handleResponse<DemoStartResponse>(response);
}

export async function getDemoStatus(
  runId: string,
  signal?: AbortSignal
): Promise<DemoRunResponse> {
  const baseUrl = getBaseUrl();
  const response = await fetch(`${baseUrl}/api/demo/${encodeURIComponent(runId)}`, {
    cache: "no-store",
    signal: signal ?? AbortSignal.timeout(5_000),
  });

  return handleResponse<DemoRunResponse>(response);
}

export const getDemoRun = getDemoStatus;

export async function resetDemo(signal?: AbortSignal): Promise<DemoResetResponse> {
  const baseUrl = getBaseUrl();
  const response = await fetch(`${baseUrl}/api/demo/reset`, {
    method: "POST",
    signal: signal ?? AbortSignal.timeout(10_000),
  });

  return handleResponse<DemoResetResponse>(response);
}
