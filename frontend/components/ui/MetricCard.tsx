import React from "react";

interface MetricCardProps {
  label: string;
  value: string | number | null | undefined;
  subtext?: string;
  icon?: React.ReactNode;
  className?: string;
}

export function MetricCard({
  label,
  value,
  subtext,
  icon,
  className = "",
}: MetricCardProps) {
  const displayValue = value === null || value === undefined ? "—" : value;

  return (
    <div
      className={`bg-white rounded-xl border border-[#E4E7EC] p-5 shadow-sm flex flex-col justify-between ${className}`}
    >
      <div className="flex items-center justify-between text-[#667085] mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider">{label}</span>
        {icon && <div className="text-[#667085]">{icon}</div>}
      </div>
      <div className="text-2xl font-bold text-[#172554] tabular-nums tracking-tight">
        {displayValue}
      </div>
      {subtext && (
        <div className="text-xs text-[#667085] mt-1.5 font-medium">{subtext}</div>
      )}
    </div>
  );
}
