import React from "react";

function LoadingSkeleton({ cards = 3, rows = 3, className = "", label = "Loading content" }) {
  return (
    <div className={`grid gap-4 ${className}`} role="status" aria-label={label} aria-busy="true">
      {Array.from({ length: cards }).map((_, cardIndex) => (
        <div key={cardIndex} className="skeleton-card" aria-hidden="true">
          <div className="skeleton-line h-3 w-28" />
          <div className="skeleton-line mt-4 h-7 w-2/3" />
          <div className="mt-5 space-y-3">
            {Array.from({ length: rows }).map((__, rowIndex) => (
              <div
                key={rowIndex}
                className="skeleton-line h-3"
                style={{ width: `${92 - rowIndex * 14}%` }}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export default LoadingSkeleton;
