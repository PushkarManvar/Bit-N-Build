import React from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "./Button";

interface ErrorStateProps {
  title?: string;
  message: string;
  code?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = "Failed to load data",
  message,
  code,
  onRetry,
  className = "",
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={`p-6 bg-red-50/70 border border-red-200 rounded-xl flex flex-col items-center text-center justify-center ${className}`}
    >
      <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center text-[#DC2626] mb-3">
        <AlertCircle className="w-5 h-5" aria-hidden="true" />
      </div>
      <h4 className="text-sm font-semibold text-red-900 mb-1">{title}</h4>
      <p className="text-xs text-red-700 max-w-md mb-2">{message}</p>
      {code && (
        <span className="inline-block px-2 py-0.5 mb-4 text-[10px] font-mono bg-red-100 text-red-800 rounded border border-red-200">
          Error code: {code}
        </span>
      )}
      {onRetry && (
        <Button
          variant="outline"
          size="sm"
          onClick={onRetry}
          icon={<RefreshCw className="w-3.5 h-3.5" />}
          className="bg-white hover:bg-red-50 text-red-800 border-red-300"
        >
          Try again
        </Button>
      )}
    </div>
  );
}
