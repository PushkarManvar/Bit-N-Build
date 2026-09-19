import React from "react";

interface ErrorBannerProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  stage?: string;
}

export function ErrorBanner({
  title = "Failed to load data",
  message,
  onRetry,
  stage,
}: ErrorBannerProps) {
  return (
    <div
      style={{
        padding: "1rem 1.25rem",
        backgroundColor: "var(--color-danger-subtle)",
        border: "1px solid var(--color-danger-border)",
        borderRadius: "var(--radius-md)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "1rem",
        marginBottom: "1rem",
      }}
      role="alert"
    >
      <div>
        <div style={{ fontWeight: 600, color: "var(--color-danger)", marginBottom: "0.2rem" }}>
          ⚠️ {title} {stage ? `(${stage})` : ""}
        </div>
        <div style={{ fontSize: "13px", color: "#991b1b" }}>{message}</div>
      </div>
      {onRetry && (
        <button
          type="button"
          className="btn btn-danger btn-sm"
          onClick={onRetry}
          style={{ whiteSpace: "nowrap" }}
        >
          Retry
        </button>
      )}
    </div>
  );
}
