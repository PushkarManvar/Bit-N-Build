/**
 * JourneyLens frozen API types and enums (docs/05_API_CONTRACT.md).
 * Synchronized with backend/app/core/enums.py and backend schemas.
 */

// Core Enums
export type Channel = "web" | "mobile_app" | "call_center" | "physical_store";

export type ProcessingStatus = "received" | "normalized" | "failed";

export type EventType =
  | "product_viewed"
  | "app_login"
  | "order_placed"
  | "return_requested"
  | "support_contacted"
  | "store_visited"
  | "refund_completed";

export type IdentityOutcome = "auto_linked" | "review_required" | "new_profile";

export type ReviewDecision = "approve_link" | "reject_link" | "create_profile";

export type ReviewStatus = "pending" | "approved" | "rejected" | "profile_created";

export type AlertType = "unresolved_refund" | "repeat_contact";

export type AlertSeverity = "low" | "medium" | "high" | "critical";

export type AlertStatus = "open" | "resolved";

export type DemoRunStatus = "running" | "completed" | "failed";

// Profile & Journey Types
export interface ProfileIdentifierOut {
  type: string;
  display_value: string;
  first_seen_at: string;
}

export interface ProfileSummary {
  profile_id: string;
  display_name: string | null;
  email: string | null;
  phone: string | null;
  channels_used: Channel[];
  event_count: number;
  open_alert_count: number;
  review_required: boolean;
  last_seen_at: string;
}

export interface ProfileListResponse {
  items: ProfileSummary[];
  page: number;
  page_size: number;
  total: number;
}

export interface AlertOut {
  id: string;
  type: AlertType;
  severity: AlertSeverity;
  title: string;
  description: string;
  recommended_action: string;
  status: AlertStatus;
  order_id: string | null;
  created_at: string;
}

export interface AlertListResponse {
  items: AlertOut[];
  total: number;
}

export interface TimelineEventOut {
  event_id: string;
  channel: Channel;
  event_type: EventType;
  occurred_at: string;
  order_id: string | null;
  decision: IdentityOutcome;
  score: number;
  evidence_summary: string[];
}

export interface ProfileDetail {
  id: string;
  display_name: string | null;
  identifiers: ProfileIdentifierOut[];
}

export interface ProfileJourneyResponse {
  profile: ProfileDetail;
  timeline: TimelineEventOut[];
  alerts: AlertOut[];
  journey_summary: Record<string, unknown> | null;
}

// Match Explanation Types
export interface EventContext {
  channel: Channel;
  event_type: EventType;
  occurred_at: string;
}

export interface EvidenceItem {
  rule?: string;
  points?: number;
  message?: string;
  [key: string]: unknown;
}

export interface ConflictItem {
  type?: string;
  message?: string;
  [key: string]: unknown;
}

export interface CandidateAlternative {
  profile_id: string;
  score: number;
  [key: string]: unknown;
}

export interface MatchExplanationResponse {
  event_id: string;
  event_context: EventContext;
  decision: IdentityOutcome;
  selected_profile_id: string | null;
  score: number;
  thresholds: Record<string, number>;
  evidence: EvidenceItem[];
  conflicts: ConflictItem[];
  alternative_candidates: CandidateAlternative[];
  raw_payload: Record<string, unknown>;
  normalized_fields: Record<string, unknown>;
}

// Analytics Types
export interface AnalyticsOverview {
  total_raw_events: number;
  normalized_events: number;
  failed_events: number;
  duplicate_events: number | null;
  unified_profiles: number;
  auto_link_rate: number | null;
  review_required_rate: number | null;
  open_alerts: number;
  match_precision: number | null;
  match_recall: number | null;
  match_f1: number | null;
  false_merge_rate: number | null;
  average_processing_latency_ms: number | null;
}

export interface ChannelsResponse {
  web: number;
  mobile_app: number;
  call_center: number;
  physical_store: number;
}

// Review Types
export interface ReviewEventOut {
  channel: Channel | null;
  event_type: EventType | null;
  customer_name: string | null;
  occurred_at: string | null;
}

export interface BestCandidateOut {
  profile_id: string;
  display_name: string | null;
  score: number;
}

export interface ReviewItem {
  match_decision_id: string;
  event: ReviewEventOut;
  best_candidate: BestCandidateOut | null;
  evidence: string[];
  conflicts: ConflictItem[];
  missing_strong_identifiers: string[];
  reason: string;
}

export interface ReviewListResponse {
  items: ReviewItem[];
  total: number;
}

export interface ResolveReviewRequest {
  action: ReviewDecision;
  selected_profile_id?: string | null;
  reviewer_name: string;
  note?: string | null;
}

export interface ResolveReviewResponse {
  match_decision_id: string;
  review_status: ReviewStatus | string;
  action: ReviewDecision;
  profile_id: string | null;
  resolved_at: string;
}

// Demo & Dashboard Polling Types
export interface DemoStartRequest {
  scenario: string;
  interval_seconds?: number;
}

export interface DemoStartResponse {
  run_id: string;
  status: string;
  total_steps: number;
  current_step: number;
}

export interface DemoRunResponse {
  run_id: string;
  status: string;
  current_step: number;
  total_steps: number;
  last_event_id: string | null;
  error: string | null;
}

export interface DemoResetResponse {
  status: string;
  loaded: Record<string, number>;
}

export interface DashboardEventOut {
  event_id: string;
  channel: Channel;
  event_type: EventType;
  occurred_at: string;
  profile_id: string | null;
  match_decision: IdentityOutcome | null;
}

export interface DashboardUpdatesResponse {
  events: DashboardEventOut[];
  new_alerts: AlertOut[];
  open_alerts: number;
  pending_reviews: number;
  demo: DemoRunResponse | null;
}

// Error Envelope Shape
export interface ApiErrorDetail {
  code: string;
  message: string;
  stage: string;
  raw_event_id?: string | null;
  details?: Record<string, unknown>;
}

export interface ApiErrorResponse {
  error: ApiErrorDetail;
}

export interface HealthResult {
  ok: boolean;
  label: string;
}
