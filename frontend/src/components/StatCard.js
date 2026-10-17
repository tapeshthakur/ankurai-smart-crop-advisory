import React from "react";

function StatCard({ title, value, subtitle, accent = "primary", align = "left" }) {
  const titleTone = {
    primary: "text-primary-700",
    accent: "text-accent-700",
    success: "text-success-700",
    warning: "text-warning-700",
  };

  return (
    <div className="metric-panel">
      <div className={`${align === "right" ? "text-right" : ""} flex h-full flex-col`}>
        <p className={`text-xs font-semibold ${titleTone[accent] || titleTone.primary}`}>{title}</p>
        <p className="mt-2 break-words text-xl font-semibold leading-tight tabular-nums text-text-heading">{value}</p>
        {subtitle ? <p className="mt-auto pt-1 text-xs leading-5 text-text-muted">{subtitle}</p> : null}
      </div>
    </div>
  );
}

export default StatCard;
