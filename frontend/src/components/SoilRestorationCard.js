import React from "react";
import { useLanguage } from "../i18n/LanguageContext";

function SoilRestorationCard({ plan, onStart }) {
  const { t } = useLanguage();
  if (!plan) {
    return (
      <section className="surface-card-highlight p-6">
        <span className="section-badge">{t("soil.eyebrow", "Long-term soil care")}</span>
        <h2 className="mt-4 text-2xl font-semibold text-text-heading">{t("soil.title", "Three-year soil restoration plan")}</h2>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-text-muted">{t("soil.empty", "Run a crop advisory first. AnkurAI will use your NPK, pH, crop, rainfall, and season inputs to prepare this plan.")}</p>
        <button type="button" onClick={onStart} className="theme-button-primary mt-5 px-5 py-3">{t("soil.start", "Open crop advisory")}</button>
      </section>
    );
  }

  return (
    <section className="surface-card p-5">
      <div>
        <span className="section-badge">{t("soil.eyebrow", "Long-term soil care")}</span>
        <h2 className="mt-3 text-2xl font-semibold text-text-heading">{t("soil.title", "Three-year soil restoration plan")}</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-text-muted">{t("soil.subtitle", "A practical crop-rotation and soil-recovery guide from the values already used in your advisory.")}</p>
      </div>

      <div className="mt-5 border-t border-surface-border pt-5">
          <div className="rounded-xl border border-warning-100 bg-warning-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-warning-700">{t("soil.priorities", "Current priorities")}</p>
            <p className="mt-2 text-sm leading-6 text-text-heading">{(plan.priority_issues || []).join(", ")}</p>
          </div>
          <div className="mt-4 grid gap-3 lg:grid-cols-3">
            {(plan.plan || []).map((year) => (
              <article key={year.year} className="surface-card-soft p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-accent-700">{t("soil.year", "Year")} {year.year}</p>
                <h4 className="mt-2 text-base font-semibold text-text-heading">{year.focus}</h4>
                <p className="mt-3 text-sm font-medium text-text-heading">{t("soil.rotation", "Rotation")}</p>
                <p className="mt-1 text-sm leading-6 text-text-muted">{year.rotation}</p>
                <p className="mt-3 text-sm font-medium text-text-heading">{t("soil.coverCrop", "Cover crop")}</p>
                <p className="mt-1 text-sm leading-6 text-text-muted">{year.cover_crop}</p>
                <p className="mt-3 text-sm font-medium text-text-heading">{t("soil.microbial", "Microbial support")}</p>
                <p className="mt-1 text-sm leading-6 text-text-muted">{year.microbial_support}</p>
              </article>
            ))}
          </div>
          <p className="mt-4 text-xs leading-5 text-text-subtle">{(plan.limitations || []).join(" ")}</p>
      </div>
    </section>
  );
}

export default SoilRestorationCard;
