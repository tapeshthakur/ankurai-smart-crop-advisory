import React from "react";

function formatPercent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  return `${(number * 100).toFixed(1)}%`;
}

function PestOutbreakCard({ forecast, loading, status = "idle" }) {
  if (loading) {
    return (
      <section className="surface-card p-5">
        <span className="section-badge">Pest outbreak model</span>
        <h3 className="mt-3 text-xl font-semibold text-text-heading">Forecasting next-7-day pest risk...</h3>
      </section>
    );
  }

  if (!forecast) {
    const unsupportedCrop = String(status || "").startsWith("unsupported:")
      ? String(status).replace("unsupported:", "")
      : "";
    const message = unsupportedCrop
      ? `The outbreak model currently supports rice, wheat, maize, cotton, and soybean. It is not trained for ${unsupportedCrop} yet, so AnkurAI cannot show a threshold forecast for this crop.`
      : status === "error"
        ? "The pest outbreak model could not be scored right now. Confirm the backend is restarted and the pest model artifact is available."
        : "Run a crop prediction first. AnkurAI will combine the crop, weather, rainfall, crop age, and scouting defaults to estimate outbreak risk.";

    return (
      <section className="surface-card-highlight p-5">
        <span className="section-badge">Pest outbreak model</span>
        <h3 className="mt-3 text-xl font-semibold text-text-heading">Next-7-day outbreak forecast</h3>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-text-muted">
          {message}
        </p>
      </section>
    );
  }

  const highest = forecast.highest_risk || {};
  const riskTone = highest.risk_level === "high" ? "status-risk" : highest.risk_level === "moderate" ? "status-watch" : "status-good";
  const isFallback = forecast.source === "planning_outlook_fallback" || status === "fallback";

  return (
    <section className="surface-card space-y-5 p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <span className="section-badge">Pest outbreak model</span>
          <h3 className="mt-3 text-xl font-semibold text-text-heading">{isFallback ? "Pest scouting risk" : "Next-7-day pest outbreak forecast"}</h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-text-muted">
            {isFallback
              ? "Using the advisory planning outlook because the dedicated outbreak model is unavailable or not trained for this crop."
              : "Uses the trained weekly outbreak CSV model, not leaf images, to rank pest risk for the selected crop."}
          </p>
        </div>
        <div className="surface-card-soft min-w-[190px] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-subtle">Highest risk</p>
          <p className="mt-2 text-lg font-semibold capitalize text-text-heading">{highest.pest || "-"}</p>
          <span className={`status-chip mt-3 ${riskTone}`}>{highest.risk_level || "low"}</span>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        {(forecast.forecasts || []).map((item) => {
          const tone = item.risk_level === "high" ? "status-risk" : item.risk_level === "moderate" ? "status-watch" : "status-good";
          return (
            <article key={item.pest} className="surface-card-soft p-4">
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-semibold capitalize text-text-heading">{item.pest}</p>
                <span className={`status-chip ${tone}`}>{item.risk_level}</span>
              </div>
              <p className="mt-3 text-2xl font-bold text-accent-700">{isFallback ? item.risk_level : formatPercent(item.outbreak_probability)}</p>
              <p className="mt-1 text-xs leading-5 text-text-muted">
                {isFallback ? "Scouting priority from planning outlook" : item.outbreak_next_7d ? "Likely to cross threshold" : "Below outbreak threshold"}
              </p>
            </article>
          );
        })}
      </div>

      <p className="text-xs leading-5 text-text-subtle">
        {isFallback
          ? "Confirm field symptoms and local extension thresholds before applying control measures."
          : "Forecast uses defaults for trap counts unless field scouting values are supplied later. Confirm symptoms and local thresholds before control measures."}
      </p>
    </section>
  );
}

export default PestOutbreakCard;
