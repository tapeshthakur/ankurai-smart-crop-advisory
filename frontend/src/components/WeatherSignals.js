import React from "react";
import { CloudRain, Sun } from "lucide-react";
import { useLanguage } from "../i18n/LanguageContext";

function WeatherSignals({ forecast }) {
  const { language, t } = useLanguage();
  if (!forecast?.days?.length) return null;

  const locale = language === "hi" ? "hi-IN" : language === "mr" ? "mr-IN" : "en-IN";
  const days = forecast.days.slice(0, 3);
  const rainfall = days.reduce((sum, day) => sum + (Number(day.precipitation_mm) || 0), 0);
  const maxRainChance = Math.max(0, ...days.map((day) => Number(day.precipitation_probability) || 0));
  const hottest = days.reduce((value, day) => Math.max(value, Number(day.temperature_max_c) || 0), 0);
  const rainSignal = rainfall >= 5 || maxRainChance >= 60;
  const heatSignal = hottest >= 35;
  const fetchedAt = new Date(forecast.fetched_at || "");
  const fetchedLabel = Number.isNaN(fetchedAt.getTime())
    ? "-"
    : fetchedAt.toLocaleString(locale, { dateStyle: "medium", timeStyle: "short" });

  return (
    <section className="surface-card p-5 sm:p-6" aria-labelledby="weather-signals-title">
      <div className="flex flex-col gap-2 border-b border-surface-border pb-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <span className="section-badge">{t("farmer.weatherSourceLabel")}</span>
          <h2 id="weather-signals-title" className="mt-2 text-xl font-semibold text-text-heading">{t("farmer.weatherSignalsTitle")}</h2>
        </div>
        <p className="text-xs text-text-subtle">{forecast.source} · {t("farmer.weatherUpdated")}: {fetchedLabel}</p>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-3">
        {days.map((day) => {
          const date = new Date(`${day.date}T00:00:00`);
          return (
            <div key={day.date} className="border-l-2 border-surface-border pl-3 py-1">
              <p className="text-sm font-semibold text-text-heading">{date.toLocaleDateString(locale, { weekday: "short", day: "numeric", month: "short" })}</p>
              <p className="mt-1 text-xs tabular-nums text-text-muted">{t("farmer.rainForecast")}: {Number(day.precipitation_mm || 0).toFixed(1)} mm · {Number(day.precipitation_probability || 0)}%</p>
              <p className="mt-1 text-xs tabular-nums text-text-muted">{t("farmer.highTemperature")}: {Number(day.temperature_max_c || 0).toFixed(1)} °C</p>
            </div>
          );
        })}
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        {rainSignal ? (
          <p className="flex items-start gap-2 border-l-2 border-sky-600 bg-sky-50 px-3 py-2 text-sm leading-5 text-text-heading">
            <CloudRain size={17} className="mt-0.5 shrink-0 text-sky-600" aria-hidden="true" />
            {t("farmer.rainSignal", undefined, { amount: rainfall.toFixed(1), chance: maxRainChance })}
          </p>
        ) : null}
        {heatSignal ? (
          <p className="flex items-start gap-2 border-l-2 border-accent-500 bg-accent-50 px-3 py-2 text-sm leading-5 text-text-heading">
            <Sun size={17} className="mt-0.5 shrink-0 text-accent-700" aria-hidden="true" />
            {t("farmer.heatSignal", undefined, { temperature: hottest.toFixed(1) })}
          </p>
        ) : null}
        {!rainSignal && !heatSignal ? <p className="sm:col-span-2 text-sm text-text-muted">{t("farmer.weatherNoSignal")}</p> : null}
      </div>
      <p className="mt-3 text-xs leading-5 text-text-subtle">{t("farmer.weatherDisclaimer")}</p>
    </section>
  );
}

export default WeatherSignals;
