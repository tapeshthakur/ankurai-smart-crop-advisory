import React, { useEffect, useState } from "react";
import api from "../api/client";
import { useLanguage } from "../i18n/LanguageContext";

function RationaleCard({ farmId, fieldId, crop }) {
  const { t } = useLanguage();
  const [rationale, setRationale] = useState(null);

  useEffect(() => {
    if (!farmId || !crop) return;
    api.get(`/api/farms/${farmId}/rationale`, { params: { crop, field_id: fieldId || undefined } })
      .then((response) => setRationale(response.data.rationale))
      .catch(() => setRationale(null));
  }, [crop, farmId, fieldId]);

  if (!rationale) return null;
  const evidence = rationale.evidence || {};
  const percent = (value) => `${Math.round(Number(value || 0) * 100)}%`;
  return (
    <section className="surface-card-highlight p-5">
      <span className="section-badge">{t("farmIntelligence.rationaleEyebrow", "Evidence")}</span>
      <h3 className="mt-3 text-xl font-semibold text-text-heading">{t("farmIntelligence.why", "Why this recommendation?")}</h3>
      <p className="mt-2 text-sm leading-6 text-text-muted">{rationale.reason}</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div><p className="text-xs text-text-subtle">{t("farmIntelligence.observedImprovement", "Observed improvement")}</p><p className="mt-1 text-lg font-semibold text-text-heading">{evidence.intervention_cases ? percent(evidence.intervention_improvement_rate) : "-"}</p></div>
        <div><p className="text-xs text-text-subtle">{t("farmIntelligence.comparison", "Comparable cases")}</p><p className="mt-1 text-lg font-semibold text-text-heading">{evidence.comparison_cases ? percent(evidence.comparison_improvement_rate) : `${evidence.comparison_cases || 0}`}</p></div>
        <div><p className="text-xs text-text-subtle">{t("farmIntelligence.evidenceStrength", "Evidence strength")}</p><p className="mt-1 text-lg font-semibold text-accent-700">{rationale.evidence_strength}</p></div>
      </div>
      <p className="mt-4 text-xs leading-5 text-text-muted">{rationale.limitations?.join(" ")}</p>
    </section>
  );
}

export default RationaleCard;
