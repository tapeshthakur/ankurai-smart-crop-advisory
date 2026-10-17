import React, { useEffect, useState } from "react";
import api from "../api/client";
import { useLanguage } from "../i18n/LanguageContext";

function RationaleCard({ farmId, fieldId, crop, refreshToken = 0 }) {
  const { t } = useLanguage();
  const [rationale, setRationale] = useState(null);

  useEffect(() => {
    if (!farmId || !crop) return;
    api.get(`/api/farms/${farmId}/rationale`, { params: { crop, field_id: fieldId || undefined } })
      .then((response) => setRationale(response.data.rationale))
      .catch(() => setRationale(null));
  }, [crop, farmId, fieldId, refreshToken]);

  if (!rationale) return null;
  const evidence = rationale.evidence || {};
  const percent = (value) => `${Math.round(Number(value || 0) * 100)}%`;
  const reason = rationale.reason_code === "comparison_ready"
    ? t("farmIntelligence.comparisonReady", "Observed improvement: {{target}}% for the recommendation group and {{comparison}}% for usual practice. This is observational, not causal evidence.", { target: Math.round((evidence.intervention_improvement_rate || 0) * 100), comparison: Math.round((evidence.comparison_improvement_rate || 0) * 100) })
    : rationale.reason_code === "comparison_pending"
      ? t("farmIntelligence.comparisonPending", "{{target}} recommendation outcomes recorded. Add {{needed}} usual-practice outcome(s) for a side-by-side estimate.", { target: evidence.intervention_cases || 0, needed: Math.max(0, (evidence.minimum_cases || 3) - (evidence.comparison_cases || 0)) })
      : t("farmIntelligence.collecting", "Record {{needed}} more recommendation outcome(s) to meet the minimum of {{minimum}}. Usual-practice outcomes are counted separately.", { needed: Math.max(0, (evidence.minimum_cases || 3) - (evidence.intervention_cases || 0)), minimum: evidence.minimum_cases || 3 });
  const metric = (rate, count, improved) => (
    <>
      <p className="mt-1 text-lg font-semibold tabular-nums text-text-heading">{rate == null ? `${count || 0} / ${evidence.minimum_cases || 3}` : percent(rate)}</p>
      <p className="mt-1 text-xs text-text-subtle">{t("farmIntelligence.outcomeCount", "{{improved}} improved of {{count}} outcomes", { improved: improved || 0, count: count || 0 })}</p>
    </>
  );
  return (
    <section className="surface-card-highlight p-5">
      <span className="section-badge">{t("farmIntelligence.rationaleEyebrow", "Evidence")}</span>
      <h3 className="mt-3 text-xl font-semibold text-text-heading">{t("farmIntelligence.why", "Why this recommendation?")}</h3>
      <p className="mt-2 text-sm leading-6 text-text-muted">{reason}</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div><p className="text-xs text-text-subtle">{t("farmIntelligence.observedImprovement", "Recommendation group")}</p>{metric(evidence.intervention_improvement_rate, evidence.intervention_cases, evidence.intervention_improved)}</div>
        <div><p className="text-xs text-text-subtle">{t("farmIntelligence.comparison", "Usual-practice group")}</p>{metric(evidence.comparison_improvement_rate, evidence.comparison_cases, evidence.comparison_improved)}</div>
        <div><p className="text-xs text-text-subtle">{t("farmIntelligence.evidenceStrength", "Evidence strength")}</p><p className="mt-1 text-lg font-semibold text-accent-700">{t(`farmIntelligence.${String(rationale.evidence_strength || "insufficient").toLowerCase()}`, rationale.evidence_strength || "Insufficient")}</p></div>
      </div>
      <p className="mt-4 text-xs leading-5 text-text-muted">{rationale.limitations?.join(" ")}</p>
    </section>
  );
}

export default RationaleCard;
