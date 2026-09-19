import React from "react";

export function SkeletonBlock({
  className = "h-4 w-full",
}: {
  className?: string;
}) {
  return (
    <div
      aria-hidden="true"
      className={`animate-pulse bg-slate-200/80 rounded ${className}`}
    />
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="w-full space-y-3 p-4" aria-busy="true" aria-label="Loading content">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center space-x-4">
          <SkeletonBlock className="h-6 w-1/4 rounded-md" />
          <SkeletonBlock className="h-6 w-1/4 rounded-md" />
          <SkeletonBlock className="h-6 w-1/6 rounded-md" />
          <SkeletonBlock className="h-6 w-1/5 rounded-md" />
          <SkeletonBlock className="h-6 w-12 rounded-md" />
        </div>
      ))}
    </div>
  );
}
