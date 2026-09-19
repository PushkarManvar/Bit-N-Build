"use client";

import React, { useState } from "react";
import { Check, Copy } from "lucide-react";

interface JsonViewerProps {
  data: unknown;
  className?: string;
  maxHeight?: string;
}

export function JsonViewer({
  data,
  className = "",
  maxHeight = "max-h-96",
}: JsonViewerProps) {
  const [copied, setCopied] = useState(false);
  const formatted = JSON.stringify(data, null, 2);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(formatted);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  return (
    <div
      className={`relative rounded-lg border border-[#E4E7EC] bg-slate-900 text-slate-100 overflow-hidden ${className}`}
    >
      <div className="flex items-center justify-between px-3 py-2 bg-slate-800/80 border-b border-slate-700 text-xs text-slate-300">
        <span className="font-mono">JSON payload</span>
        <button
          onClick={handleCopy}
          type="button"
          aria-label={copied ? "Copied to clipboard" : "Copy JSON to clipboard"}
          className="inline-flex items-center gap-1 px-2 py-1 rounded bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs transition-colors focus:outline-none focus:ring-1 focus:ring-slate-400"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre
        tabIndex={0}
        className={`p-4 overflow-x-auto overflow-y-auto text-xs font-mono leading-relaxed select-text ${maxHeight}`}
      >
        <code>{formatted}</code>
      </pre>
    </div>
  );
}
