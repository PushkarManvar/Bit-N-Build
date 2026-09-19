import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "./Button";

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
      className="mb-4 flex flex-col gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
      role="alert"
    >
      <div className="flex gap-3">
        <AlertTriangle
          className="mt-0.5 h-5 w-5 shrink-0 text-red-700"
          aria-hidden="true"
        />
        <div>
          <div className="font-semibold text-red-800">
            {title} {stage ? `(${stage})` : ""}
          </div>
          <div className="mt-0.5 text-sm text-red-700">{message}</div>
        </div>
      </div>
      {onRetry && (
        <Button
          type="button"
          variant="danger"
          size="sm"
          icon={<RefreshCw className="h-3.5 w-3.5" />}
          onClick={onRetry}
        >
          Retry
        </Button>
      )}
    </div>
  );
}
