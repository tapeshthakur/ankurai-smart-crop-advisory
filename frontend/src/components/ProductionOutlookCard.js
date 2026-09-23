import React from "react";
import { useLanguage } from "../i18n/LanguageContext";

function ProductionOutlookCard({ outlook }) {
  const { t } = useLanguage();
  if (!outlook) return null;

  const yieldEstimate = outlook.yield_estimate || {};
  const harvest = outlook.harvest_window || {};
  const pestRisk = outlook.pest_risk || {};
  const range = Array.isArray(yieldEstimate.planning_range_t_ha)
    ? `${yieldEstimate.planning_range_t_ha[0]}-${yieldEstimate.planning_range_t_ha[1]} t/ha`
    : "-";

  return (
    <section className="surface-card space-y-5 p-5">
      <div>
        <span className="section-badge">{t("production.eyebrow", "Planning outlook")}</span>
        <h3 className="mt-3 text-xl font-semibold text-text-heading">{t("production.title", "Yield, harvest, and pest scouting")}</h3>
        <p className="mt-2 text-sm leading-6 text-text-muted">{t("production.subtitle", "A field-planning estimate from the crop, soil, weather, and season values you entered.")}</p>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <div className="surface-card-soft p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-subtle">{t("production.yield", "Yield planning range")}</p>
          <p className="mt-2 text-xl font-semibold text-accent-700">{range}</p>
          <p className="mt-2 text-xs leading-5 text-text-muted">{t("production.score", "Input suitability")}: {yieldEstimate.suitability_score ?? "-"}/100</p>
        </div>
        <div className="surface-card-soft p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-subtle">{t("production.harvest", "Estimated harvest window")}</p>
          <p className="mt-2 text-base font-semibold text-text-heading">{harvest.start || "-"}</p>
          <p className="text-sm text-text-muted">{t("production.to", "to")} {harvest.end || "-"}</p>
          {harvest.planting_date_assumed_today ? <p className="mt-2 text-xs text-warning-700">{t("production.assumedToday", "Assumes planting today. Add a planting date for a better window.")}</p> : null}
        </div>
        <div className="surface-card-soft p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-subtle">{t("production.pestRisk", "Pest scouting risk")}</p>
          <p className="mt-2 text-xl font-semibold capitalize text-text-heading">{pestRisk.level || "-"}</p>
          <p className="mt-2 text-xs leading-5 text-text-muted">{(pestRisk.likely_pests || []).join(", ") || "-"}</p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <p className="text-sm font-semibold text-text-heading">{t("production.watch", "What to watch")}</p>
          <ul className="mt-2 space-y-1 text-sm leading-6 text-text-muted">
            {(pestRisk.drivers || []).map((driver) => <li key={driver}>- {driver}</li>)}
            {(yieldEstimate.constraints || []).map((constraint) => <li key={constraint}>- {constraint}</li>)}
          </ul>
        </div>
        <div>
          <p className="text-sm font-semibold text-text-heading">{t("production.nextAction", "Next action")}</p>
          <p className="mt-2 text-sm leading-6 text-text-muted">{pestRisk.recommended_action}</p>
        </div>
      </div>
    </section>
  );
}

export default ProductionOutlookCard;
