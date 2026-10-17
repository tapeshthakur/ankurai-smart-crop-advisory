import React from "react";
import { useLanguage } from "../i18n/LanguageContext";
import { soilText } from "../i18n/soilTranslations";

const riskStyles = {
  high: "status-risk",
  moderate: "status-watch",
  medium: "status-watch",
  low: "status-good",
};

function RiskBadge({ level, className = "" }) {
  const { language } = useLanguage();
  const key = String(level || "low").toLowerCase();
  return (
    <span className={`status-chip ${riskStyles[key] || "status-info"} ${className}`.trim()}>
      {soilText(language, key, level || "low")}
    </span>
  );
}

export default RiskBadge;
