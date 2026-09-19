import React from "react";
import { Inbox } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
  actionText?: string;
  onAction?: () => void;
}

export function EmptyState({
  title,
  description,
  icon,
  action,
  className = "",
  actionText,
  onAction,
}: EmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 text-center bg-white rounded-xl border border-dashed border-[#D0D5DD] ${className}`}
    >
      <div className="w-12 h-12 mb-3 rounded-full bg-slate-100 flex items-center justify-center text-[#667085]">
        {icon ?? <Inbox className="w-6 h-6" aria-hidden="true" />}
      </div>
      <h3 className="text-base font-semibold text-[#172554] mb-1">{title}</h3>
      <p className="text-sm text-[#667085] max-w-sm mb-4">{description}</p>
      {action ?? (actionText && onAction ? (
        <Button variant="outline" onClick={onAction}>
          {actionText}
        </Button>
      ) : null)}
    </div>
  );
}
