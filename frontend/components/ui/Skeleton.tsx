import React from "react";

export function SkeletonBlock({
  height = "20px",
  width = "100%",
  borderRadius = "var(--radius-sm)",
  style = {},
}: {
  height?: string;
  width?: string;
  borderRadius?: string;
  style?: React.CSSProperties;
}) {
  return (
    <div
      className="skeleton"
      style={{
        height,
        width,
        borderRadius,
        ...style,
      }}
    />
  );
}

export function SkeletonCard({ height = "120px" }: { height?: string }) {
  return (
    <div className="panel-card" style={{ height, display: "flex", flexDirection: "column", gap: "10px" }}>
      <SkeletonBlock height="16px" width="40%" />
      <SkeletonBlock height="24px" width="70%" />
      <SkeletonBlock height="14px" width="55%" />
    </div>
  );
}
