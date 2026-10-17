import React from "react";
import { useLanguage } from "../i18n/LanguageContext";
import { soilDataText, soilText } from "../i18n/soilTranslations";
import RiskBadge from "./RiskBadge";

function formatPercent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  return `${(number * 100).toFixed(1)}%`;
}

function PestOutbreakCard({ forecast, loading, status = "idle" }) {
  const { language, tv } = useLanguage();
  const tr = (key, fallback) => soilText(language, key, fallback);
  if (loading) {
    return (
      <section id="pest-outbreak" className="surface-card p-5 scroll-mt-24">
        <span className="section-badge">{tr("pestModel", "Pest outbreak model")}</span>
        <h3 className="mt-3 text-xl font-semibold text-text-heading">{tr("loadingForecast", "Forecasting next-7-day pest risk...")}</h3>
      </section>
    );
  }

  if (!forecast) {
    const unsupportedCrop = String(status || "").startsWith("unsupported:")
      ? String(status).replace("unsupported:", "")
      : "";
    const message = unsupportedCrop
      ? tr("unsupported", "The outbreak model currently supports rice, wheat, maize, cotton, and soybean. It is not trained for {{crop}} yet, so AnkurAI cannot show a threshold forecast for this crop.").replace("{{crop}}", tv("crops", unsupportedCrop))
      : status === "error"
        ? tr("errorForecast", "The pest outbreak model could not be scored right now. Confirm the backend is restarted and the pest model artifact is available.")
        : tr("runFirst", "Run a crop prediction first. AnkurAI will combine the crop, weather, rainfall, crop age, and scouting defaults to estimate outbreak risk.");

    return (
      <section id="pest-outbreak" className="surface-card-highlight p-5 scroll-mt-24">
        <span className="section-badge">{tr("pestModel", "Pest outbreak model")}</span>
        <h3 className="mt-3 text-xl font-semibold text-text-heading">{tr("forecast", "Next-7-day outbreak forecast")}</h3>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-text-muted">
          {message}
        </p>
      </section>
    );
  }

  const highest = forecast.highest_risk || {};
  const isFallback = forecast.source === "planning_outlook_fallback" || status === "fallback";

  return (
    <section id="pest-outbreak" className="surface-card space-y-5 p-5 scroll-mt-24">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <span className="section-badge">{tr("pestModel", "Pest outbreak model")}</span>
          <h3 className="mt-3 text-xl font-semibold text-text-heading">{isFallback ? tr("scoutingRisk", "Pest scouting risk") : tr("forecast", "Next-7-day pest outbreak forecast")}</h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-text-muted">
            {isFallback
              ? tr("fallbackDescription", "Using the advisory planning outlook because the dedicated outbreak model is unavailable or not trained for this crop.")
              : tr("modelDescription", "Uses the trained weekly outbreak CSV model, not leaf images, to rank pest risk for the selected crop.")}
          </p>
        </div>
        <div className="surface-card-soft min-w-[190px] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-subtle">{tr("highestRisk", "Highest risk")}</p>
          <p className="mt-2 text-lg font-semibold capitalize text-text-heading">{soilDataText(language, highest.pest) || "-"}</p>
          <RiskBadge level={highest.risk_level} className="mt-3" />
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        {(forecast.forecasts || []).map((item) => {
          return (
            <article key={item.pest} className="surface-card-soft p-4">
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-semibold capitalize text-text-heading">{soilDataText(language, item.pest)}</p>
                <RiskBadge level={item.risk_level} />
              </div>
              <p className="mt-3 text-2xl font-bold text-accent-700">{isFallback ? item.risk_level : formatPercent(item.outbreak_probability)}</p>
              <p className="mt-1 text-xs leading-5 text-text-muted">
                {isFallback ? tr("scoutingPriority", "Scouting priority from planning outlook") : item.outbreak_next_7d ? tr("likelyThreshold", "Likely to cross threshold") : tr("belowThreshold", "Below outbreak threshold")}
              </p>
            </article>
          );
        })}
      </div>

    </section>
  );
}

export default PestOutbreakCard;
