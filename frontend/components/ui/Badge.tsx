import React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Globe,
  Headphones,
  Smartphone,
  Store,
  UserPlus,
} from "lucide-react";
import type {
  AlertSeverity,
  Channel,
  IdentityOutcome,
  ProcessingStatus,
} from "@/lib/types";
import {
  ALERT_SEVERITY_META,
  CHANNEL_META,
  IDENTITY_OUTCOME_META,
  PROCESSING_STATUS_META,
} from "@/lib/presenters";

export function ChannelBadge({
  channel,
  className = "",
}: {
  channel: Channel;
  className?: string;
}) {
  const meta = CHANNEL_META[channel] ?? {
    label: channel,
    iconName: "Globe",
    badgeBg: "bg-slate-100",
    badgeText: "text-slate-800",
    badgeBorder: "border-slate-200",
    hex: "#64748B",
  };

  const renderIcon = () => {
    switch (meta.iconName) {
      case "Globe":
        return <Globe className="w-3.5 h-3.5 mr-1.5" aria-hidden="true" />;
      case "Smartphone":
        return <Smartphone className="w-3.5 h-3.5 mr-1.5" aria-hidden="true" />;
      case "Headphones":
        return <Headphones className="w-3.5 h-3.5 mr-1.5" aria-hidden="true" />;
      case "Store":
        return <Store className="w-3.5 h-3.5 mr-1.5" aria-hidden="true" />;
      default:
        return <Globe className="w-3.5 h-3.5 mr-1.5" aria-hidden="true" />;
    }
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${meta.badgeBg} ${meta.badgeText} ${meta.badgeBorder} ${className}`}
    >
      {renderIcon()}
      <span>{meta.label}</span>
    </span>
  );
}

export function IdentityOutcomeBadge({
  outcome,
  className = "",
}: {
  outcome: IdentityOutcome;
  className?: string;
}) {
  const meta = IDENTITY_OUTCOME_META[outcome] ?? {
    label: outcome,
    badgeBg: "bg-slate-100",
    badgeText: "text-slate-800",
    badgeBorder: "border-slate-200",
    iconName: "CheckCircle2",
  };

  const renderIcon = () => {
    switch (meta.iconName) {
      case "CheckCircle2":
        return <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" aria-hidden="true" />;
      case "AlertTriangle":
        return <AlertTriangle className="w-3.5 h-3.5 mr-1.5" aria-hidden="true" />;
      case "UserPlus":
        return <UserPlus className="w-3.5 h-3.5 mr-1.5" aria-hidden="true" />;
      default:
        return null;
    }
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${meta.badgeBg} ${meta.badgeText} ${meta.badgeBorder} ${className}`}
    >
      {renderIcon()}
      <span>{meta.label}</span>
    </span>
  );
}

export function SeverityBadge({
  severity,
  className = "",
}: {
  severity: AlertSeverity;
  className?: string;
}) {
  const meta = ALERT_SEVERITY_META[severity] ?? {
    label: severity,
    badgeBg: "bg-slate-100",
    badgeText: "text-slate-800",
    badgeBorder: "border-slate-200",
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${meta.badgeBg} ${meta.badgeText} ${meta.badgeBorder} ${className}`}
    >
      {meta.label}
    </span>
  );
}

export function ProcessingStatusBadge({
  status,
  className = "",
}: {
  status: ProcessingStatus;
  className?: string;
}) {
  const meta = PROCESSING_STATUS_META[status] ?? {
    label: status,
    badgeBg: "bg-slate-100",
    badgeText: "text-slate-800",
    badgeBorder: "border-slate-200",
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${meta.badgeBg} ${meta.badgeText} ${meta.badgeBorder} ${className}`}
    >
      {meta.label}
    </span>
  );
}

export const IdentityBadge = IdentityOutcomeBadge;
