import React from "react";

interface PanelProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
  header?: React.ReactNode;
  footer?: React.ReactNode;
}

export function Panel({
  children,
  className = "",
  header,
  footer,
  ...props
}: PanelProps) {
  return (
    <div
      className={`bg-white rounded-xl border border-[#E4E7EC] shadow-sm overflow-hidden ${className}`}
      {...props}
    >
      {header && (
        <div className="px-5 py-4 border-b border-[#E4E7EC] bg-white flex items-center justify-between">
          {header}
        </div>
      )}
      <div className="p-5">{children}</div>
      {footer && (
        <div className="px-5 py-3 border-t border-[#E4E7EC] bg-slate-50 flex items-center justify-end">
          {footer}
        </div>
      )}
    </div>
  );
}
