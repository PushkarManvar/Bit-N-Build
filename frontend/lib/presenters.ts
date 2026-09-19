/**
 * Presenter mappings for JourneyLens channels, events, decisions, and alerts.
 * Adheres strictly to docs/12_STITCH_FRONTEND_IMPLEMENTATION_GUIDE.md section 5.
 */

import type {
  AlertSeverity,
  AlertType,
  Channel,
  EventType,
  IdentityOutcome,
  ReviewDecision,
  ProcessingStatus,
} from "./types";

export interface ChannelMeta {
  label: string;
  iconName: "Globe" | "Smartphone" | "Headphones" | "Store";
  colorClass: string;
  badgeBg: string;
  badgeText: string;
  badgeBorder: string;
  hex: string;
}

export const CHANNEL_META: Record<Channel, ChannelMeta> = {
  web: {
    label: "Website",
    iconName: "Globe",
    colorClass: "text-[#4F46E5]",
    badgeBg: "bg-indigo-50",
    badgeText: "text-indigo-700",
    badgeBorder: "border-indigo-200",
    hex: "#4F46E5",
  },
  mobile_app: {
    label: "Mobile App",
    iconName: "Smartphone",
    colorClass: "text-[#7C3AED]",
    badgeBg: "bg-purple-50",
    badgeText: "text-purple-700",
    badgeBorder: "border-purple-200",
    hex: "#7C3AED",
  },
  call_center: {
    label: "Call Centre",
    iconName: "Headphones",
    colorClass: "text-[#EA580C]",
    badgeBg: "bg-orange-50",
    badgeText: "text-orange-700",
    badgeBorder: "border-orange-200",
    hex: "#EA580C",
  },
  physical_store: {
    label: "Physical Store",
    iconName: "Store",
    colorClass: "text-[#0F766E]",
    badgeBg: "bg-teal-50",
    badgeText: "text-teal-700",
    badgeBorder: "border-teal-200",
    hex: "#0F766E",
  },
};

export interface IdentityOutcomeMeta {
  label: string;
  badgeBg: string;
  badgeText: string;
  badgeBorder: string;
  iconName: "CheckCircle2" | "AlertTriangle" | "UserPlus";
}

export const IDENTITY_OUTCOME_META: Record<IdentityOutcome, IdentityOutcomeMeta> = {
  auto_linked: {
    label: "Linked automatically",
    badgeBg: "bg-emerald-50",
    badgeText: "text-emerald-700",
    badgeBorder: "border-emerald-200",
    iconName: "CheckCircle2",
  },
  review_required: {
    label: "Needs review",
    badgeBg: "bg-amber-50",
    badgeText: "text-amber-700",
    badgeBorder: "border-amber-200",
    iconName: "AlertTriangle",
  },
  new_profile: {
    label: "New profile created",
    badgeBg: "bg-indigo-50",
    badgeText: "text-indigo-700",
    badgeBorder: "border-indigo-200",
    iconName: "UserPlus",
  },
};

export interface AlertSeverityMeta {
  label: string;
  badgeBg: string;
  badgeText: string;
  badgeBorder: string;
}

export const ALERT_SEVERITY_META: Record<AlertSeverity, AlertSeverityMeta> = {
  critical: {
    label: "Critical",
    badgeBg: "bg-red-50",
    badgeText: "text-red-700",
    badgeBorder: "border-red-200",
  },
  high: {
    label: "High",
    badgeBg: "bg-orange-50",
    badgeText: "text-orange-700",
    badgeBorder: "border-orange-200",
  },
  medium: {
    label: "Medium",
    badgeBg: "bg-amber-50",
    badgeText: "text-amber-700",
    badgeBorder: "border-amber-200",
  },
  low: {
    label: "Low",
    badgeBg: "bg-slate-50",
    badgeText: "text-slate-700",
    badgeBorder: "border-slate-200",
  },
};

export const EVENT_TYPE_LABELS: Record<EventType, string> = {
  product_viewed: "Product viewed",
  app_login: "App login",
  order_placed: "Order placed",
  return_requested: "Return requested",
  support_contacted: "Support contacted",
  store_visited: "Store visited",
  refund_completed: "Refund completed",
};

export const ALERT_TYPE_LABELS: Record<AlertType, string> = {
  unresolved_refund: "Unresolved refund",
  repeat_contact: "Repeat contact",
};

export const PROCESSING_STATUS_META: Record<
  ProcessingStatus,
  { label: string; badgeBg: string; badgeText: string; badgeBorder: string }
> = {
  received: {
    label: "Received",
    badgeBg: "bg-blue-50",
    badgeText: "text-blue-700",
    badgeBorder: "border-blue-200",
  },
  normalized: {
    label: "Normalized",
    badgeBg: "bg-emerald-50",
    badgeText: "text-emerald-700",
    badgeBorder: "border-emerald-200",
  },
  failed: {
    label: "Failed",
    badgeBg: "bg-rose-50",
    badgeText: "text-rose-700",
    badgeBorder: "border-rose-200",
  },
};

/**
 * Function-style presenters used by dashboard/demo views (Preet, Tasks 2/4).
 */
export interface PresenterInfo {
  label: string;
  iconName?: string;
  badgeClass: string;
}

export function getChannelPresenter(channel: Channel | string | null | undefined): PresenterInfo {
  switch (channel) {
    case "web": return { label: "Website", iconName: "Globe", badgeClass: "badge-channel-web" };
    case "mobile_app": return { label: "Mobile App", iconName: "Smartphone", badgeClass: "badge-channel-mobile_app" };
    case "call_center": return { label: "Call Centre", iconName: "Headphones", badgeClass: "badge-channel-call_center" };
    case "physical_store": return { label: "Physical Store", iconName: "Store", badgeClass: "badge-channel-physical_store" };
    default: return { label: channel || "Unknown", iconName: "HelpCircle", badgeClass: "badge" };
  }
}

export function getEventTypeLabel(eventType: EventType | string | null | undefined): string {
  switch (eventType) {
    case "product_viewed": return "Product viewed";
    case "app_login": return "App login";
    case "order_placed": return "Order placed";
    case "return_requested": return "Return requested";
    case "support_contacted": return "Support contacted";
    case "store_visited": return "Store visited";
    case "refund_completed": return "Refund completed";
    default: return eventType ? eventType.replace(/_/g, " ") : "Event";
  }
}

export function getIdentityOutcomePresenter(outcome: IdentityOutcome | string | null | undefined): PresenterInfo {
  switch (outcome) {
    case "auto_linked": return { label: "Linked automatically", badgeClass: "badge-outcome-auto_linked" };
    case "review_required": return { label: "Needs review", badgeClass: "badge-outcome-review_required" };
    case "new_profile": return { label: "New profile created", badgeClass: "badge-outcome-new_profile" };
    default: return { label: outcome || "-", badgeClass: "badge" };
  }
}

export function getSeverityPresenter(severity: AlertSeverity | string | null | undefined): PresenterInfo {
  switch (severity) {
    case "critical": return { label: "Critical", badgeClass: "badge-severity-critical" };
    case "high": return { label: "High", badgeClass: "badge-severity-high" };
    case "medium": return { label: "Medium", badgeClass: "badge-severity-medium" };
    case "low": return { label: "Low", badgeClass: "badge-severity-low" };
    default: return { label: severity || "Unknown", badgeClass: "badge" };
  }
}

export function getReviewActionLabel(action: ReviewDecision | string): string {
  switch (action) {
    case "approve_link": return "Approve selected match";
    case "reject_link": return "Reject this candidate";
    case "create_profile": return "Create separate profile";
    default: return action;
  }
}
