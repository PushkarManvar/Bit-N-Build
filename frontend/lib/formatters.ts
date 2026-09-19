/**
 * Deterministic formatters and data masking according to
 * docs/12_STITCH_FRONTEND_IMPLEMENTATION_GUIDE.md section 7.5.
 */

/**
 * Shorten a UUID to its first 8 characters.
 */
export function formatShortUuid(id: string | null | undefined): string {
  if (!id) return "—";
  return id.length > 8 ? id.slice(0, 8) : id;
}

/**
 * Mask email: preserve first character and domain, mask the rest.
 * Example: "riya.sharma@example.com" -> "r***@example.com"
 */
export function maskEmail(email: string | null | undefined): string {
  if (!email) return "—";
  const atIndex = email.indexOf("@");
  if (atIndex <= 0) return email;
  const firstChar = email.charAt(0);
  const domain = email.slice(atIndex);
  return `${firstChar}***${domain}`;
}

/**
 * Mask phone: preserve country code (if present) and last 4 digits.
 * Example: "+919876543210" -> "+91 •••••• 3210"
 */
export function maskPhone(phone: string | null | undefined): string {
  if (!phone) return "—";
  const cleaned = phone.trim();
  const hasPlus = cleaned.startsWith("+");
  
  if (cleaned.length <= 4) return cleaned;
  
  const last4 = cleaned.slice(-4);
  
  if (hasPlus) {
    // E.g. +91 9876543210 -> extract country code (+91)
    const match = cleaned.match(/^(\+\d{1,3})/);
    const countryCode = match ? match[1] : "+";
    return `${countryCode} •••••• ${last4}`;
  }
  
  return `•••••• ${last4}`;
}

/**
 * Format ISO UTC timestamp to a readable local or deterministic string.
 */
export function formatDateTime(isoString: string | null | undefined): string {
  if (!isoString) return "—";
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      timeZoneName: "short",
    }).format(date);
  } catch {
    return isoString;
  }
}

/**
 * Relative time ago formatter.
 */
export function formatTimeAgo(isoString: string | null | undefined): string {
  if (!isoString) return "—";
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffSeconds < 60) return "just now";
    if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
    if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)}h ago`;
    if (diffSeconds < 604800) return `${Math.floor(diffSeconds / 86400)}d ago`;
    return formatDateTime(isoString);
  } catch {
    return isoString;
  }
}

/**
 * Dashboard helpers (Preet, Tasks 2/4).
 */
export function shortenId(id: string | null | undefined, length = 8): string {
  if (!id) return "-";
  return id.length > length ? id.slice(0, length) : id;
}

export function formatRelativeTime(dateStr: string | null | undefined): string {
  if (!dateStr) return "-";
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000);
    if (diffSec < 5) return "just now";
    if (diffSec < 60) return `${diffSec}s ago`;
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    const diffDays = Math.floor(diffHr / 24);
    return `${diffDays}d ago`;
  } catch {
    return dateStr;
  }
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatMetric(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  return value.toLocaleString();
}
