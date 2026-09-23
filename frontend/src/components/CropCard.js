import React from "react";
import { useLanguage } from "../i18n/LanguageContext";

function CropCard({ crop, confidence, irrigation, imageSrc, advisory }) {
  const { t, tv } = useLanguage();
  const generatedDate = new Date().toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
  const confidencePercent = Number.isFinite(Number(confidence))
    ? Math.max(0, Math.min(100, Number(confidence) <= 1 ? Number(confidence) * 100 : Number(confidence)))
    : 0;
  const irrigationValue = Number.isFinite(Number(irrigation)) ? Number(irrigation).toFixed(4) : "-";
  const confidenceTone = confidencePercent >= 75 ? "status-good" : confidencePercent >= 50 ? "status-watch" : "status-risk";
  const irrigationLevel = String(advisory?.irrigation?.level || "").toLowerCase();
  const irrigationTone = irrigationLevel === "high" ? "status-watch" : "status-info";
  const seasonTone = advisory?.seasonal_advice?.season_fit ? "status-good" : "status-watch";
  const confidenceStyle = {
    background: `conic-gradient(#2F5233 ${confidencePercent * 3.6}deg, #E7E1D3 0deg)`,
  };
  const cropLabel = tv("crops", crop || "-");
  const seasonLabel = tv("seasons", advisory?.seasonal_advice?.current_season || "-");
  const stateLabel = tv("states", advisory?.seasonal_advice?.state || "-");
  const normalizedCrop = String(crop || "").trim().toLowerCase();
  const summaryText = crop
    ? t("cropCard.summary", undefined, { crop: cropLabel, confidence: confidencePercent.toFixed(2) })
    : t("cropCard.defaultReason");
  const driverText = advisory?.explanation?.main_drivers?.length
    ? `${t("cropCard.reasonPrefix")} ${advisory.explanation.main_drivers
        .map((driver) => `${tv("features", driver.feature)}=${driver.value} (${Number(driver.importance).toFixed(2)}% ${t("cropCard.importance")})`)
        .join(", ")}.`
    : t("cropCard.defaultReason");
  const translateFertilizerRecommendation = (item) => {
    const nutrient = String(item?.nutrient || "").toLowerCase();
    const status = String(item?.status || "").toLowerCase();
    const key = `${nutrient}${status.charAt(0).toUpperCase()}${status.slice(1)}`;
    return t(`cropCard.fertilizerMessages.${key}`, item?.recommendation || "-");
  };
  const translateIrrigationMessage = (level) => {
    const keyByLevel = {
      "very low": "irrigationVeryLow",
      "low to moderate": "irrigationLowModerate",
      moderate: "irrigationModerate",
      high: "irrigationHigh",
    };
    return t(`cropCard.messages.${keyByLevel[String(level || "").toLowerCase()] || "irrigationModerate"}`);
  };
  const stateNote = (state) => t(`cropCard.stateNotes.${String(state || "").trim().toLowerCase()}`, t("cropCard.messages.localGuidance"));
  const translateSeasonMessage = () => {
    if (!advisory?.seasonal_advice) return "";
    const params = { crop: cropLabel, season: seasonLabel };
    return advisory.seasonal_advice.season_fit
      ? t("cropCard.messages.seasonGood", undefined, params)
      : t("cropCard.messages.seasonLessCommon", undefined, params);
  };
  const translateLocationMessage = () => {
    const state = advisory?.seasonal_advice?.state;
    const stateName = tv("states", state || "not specified");
    const note = stateNote(state);
    const isPreferred = String(advisory?.seasonal_advice?.location_message || "").toLowerCase().includes("commonly cultivated");
    const isReview = String(advisory?.seasonal_advice?.location_message || "").toLowerCase().includes("may still work");
    if (isPreferred) return t("cropCard.messages.stateCommon", undefined, { crop: cropLabel, state: stateName, note });
    if (isReview) return t("cropCard.messages.stateReview", undefined, { crop: cropLabel, state: stateName, note });
    return note;
  };
  const translateSeasonAdjustedMessage = () => {
    const adjusted = advisory?.season_adjusted;
    if (!adjusted) return "";
    const adjustedCrop = tv("crops", adjusted.season_adjusted_crop);
    const originalCrop = tv("crops", adjusted.original_ml_crop || crop);
    const activeSeason = tv("seasons", adjusted.active_season);
    return adjusted.changed_from_ml
      ? t("cropCard.messages.seasonReview", undefined, { crop: adjustedCrop, season: activeSeason })
      : t("cropCard.messages.seasonKept", undefined, { crop: originalCrop });
  };

  return (
    <div id="advisory-report" className="fade-in-up surface-card overflow-hidden">
      <div className="border-b border-surface-border bg-surface-card p-4 sm:p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-accent-700">{t("cropCard.reportBadge")}</p>
            <div className="mt-1 flex items-center gap-2">
              <span className="inline-flex h-7 w-7 items-center justify-center rounded-lg bg-primary-700 text-[10px] font-bold text-text-inverse">AI</span>
              <h3 className="text-xl font-semibold text-text-heading">{t("cropCard.reportTitle")}</h3>
            </div>
            <p className="mt-1 text-xs leading-5 text-text-muted">
              {t("cropCard.reportDesc")}
            </p>
          </div>
          <div className="grid gap-1.5 rounded-2xl border border-surface-border bg-surface-card p-3 text-xs text-text-muted sm:min-w-[220px]">
            <div className="flex justify-between gap-4">
              <span>{t("cropCard.generated")}</span>
              <strong className="text-text-heading">{generatedDate}</strong>
            </div>
            <div className="flex justify-between gap-4">
              <span>{t("cropCard.season")}</span>
              <strong className="text-text-heading">{seasonLabel}</strong>
            </div>
            <div className="flex justify-between gap-4">
              <span>{t("cropCard.state")}</span>
              <strong className="min-w-0 break-words text-right text-text-heading">{stateLabel}</strong>
            </div>
          </div>
        </div>
        <div className="mt-4 grid gap-2 border-t border-accent-200 pt-3 sm:grid-cols-4">
          {[
            { label: t("cropCard.recommended"), value: cropLabel, tone: "text-accent-700" },
            { label: t("cropCard.confidence"), value: `${confidencePercent.toFixed(1)}%`, tone: confidenceTone },
            { label: t("cropCard.irrigationRequirement"), value: irrigationValue, tone: "text-text-heading" },
            { label: t("cropCard.season"), value: seasonLabel, tone: "text-text-heading" },
          ].map((item) => (
            <div key={item.label} className="rounded-2xl border border-surface-border bg-surface-card px-3 py-2">
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-text-subtle">{item.label}</p>
              <p className={`mt-1 truncate text-sm font-semibold ${item.tone}`} title={String(item.value)}>{item.value}</p>
            </div>
          ))}
        </div>
      </div>
      <div className="grid gap-0 xl:grid-cols-[0.85fr,1.15fr]">
        <div className="relative min-h-[240px] overflow-hidden xl:min-h-[300px]">
          <img src={imageSrc} alt={cropLabel} className="absolute inset-0 h-full w-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-t from-primary-900 via-primary-900/30 to-transparent" />
          <div className="absolute inset-x-0 bottom-0 p-4">
            <span className="section-badge">{t("cropCard.recommended")}</span>
            <p className="mt-3 text-3xl font-bold capitalize text-white sm:text-4xl">{cropLabel}</p>
            <p className="mt-2 max-w-md text-xs leading-5 text-white/85">
              {summaryText}
            </p>
          </div>
        </div>

        <div className="grid gap-3 p-4">
          <div className="grid gap-3 sm:grid-cols-[140px,1fr]">
            <div className="surface-card-soft flex flex-col items-center justify-center p-3 text-center">
              <div className="flex h-28 w-28 items-center justify-center rounded-full p-2" style={confidenceStyle}>
                <div className="flex h-full w-full items-center justify-center rounded-full bg-surface-card text-center shadow-inner shadow-card">
                  <div className="min-w-0 px-2">
                    <p className="text-[9px] font-semibold uppercase tracking-[0.08em] text-text-muted">{t("cropCard.confidence")}</p>
                    <p className="mt-1 text-xl font-bold leading-none text-accent-700">{confidencePercent.toFixed(1)}%</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid gap-3">
              <div className="surface-card-soft p-3">
                <p className="text-[11px] uppercase tracking-[0.2em] text-text-muted">{t("cropCard.irrigationRequirement")}</p>
                <div className="mt-1 flex flex-wrap items-end justify-between gap-2">
                  <p className="text-2xl font-bold text-text-heading">{irrigationValue}</p>
                  {advisory?.irrigation?.level ? (
                    <span className={`status-chip ${irrigationTone}`}>
                      {tv("statuses", advisory.irrigation.level)}
                    </span>
                  ) : null}
                </div>
                {advisory?.irrigation ? (
                  <p className="mt-2 text-xs leading-5 text-text-muted">{translateIrrigationMessage(advisory.irrigation.level)}</p>
                ) : null}
              </div>

              <div className="grid gap-3 sm:grid-cols-[minmax(120px,0.8fr),minmax(150px,1.2fr)]">
                <div className="surface-card-soft min-w-0 p-3">
                  <p className="text-[11px] uppercase tracking-[0.2em] text-text-muted">{t("cropCard.currentSeason")}</p>
                  <p className="mt-1 break-words text-base font-semibold text-text-heading">{seasonLabel}</p>
                </div>
                <div className="surface-card-soft min-w-0 p-3">
                  <p className="text-[11px] uppercase tracking-[0.2em] text-text-muted">{t("cropCard.state")}</p>
                  <p className="mt-1 break-words text-base font-semibold leading-snug text-text-heading">{stateLabel}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="surface-card-soft p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-[11px] uppercase tracking-[0.2em] text-accent-600">{t("cropCard.aiExplanation")}</p>
                <h4 className="mt-1 text-lg font-semibold text-text-heading">{t("cropCard.why")}</h4>
              </div>
              <span className={`status-chip ${seasonTone}`}>
                {advisory?.seasonal_advice?.season_fit ? t("cropCard.goodFit") : t("cropCard.seasonContext")}
              </span>
            </div>
            <p className="mt-2 text-xs leading-5 text-text-muted">{driverText}</p>

            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              {advisory?.explanation?.main_drivers?.map((driver) => (
                <div key={driver.feature} className="rounded-2xl border border-surface-border bg-surface-card p-3">
                  <p className="text-[11px] uppercase tracking-[0.2em] text-text-muted">{tv("features", driver.feature)}</p>
                  <p className="mt-1 text-lg font-semibold text-accent-700">{driver.value}</p>
                  <p className="mt-1 text-xs text-text-subtle">{Number(driver.importance).toFixed(2)}% {t("cropCard.importance")}</p>
                </div>
              ))}
            </div>
          </div>

          {advisory?.season_adjusted ? (
            <div className="surface-card-highlight border-t border-accent-200 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.2em] text-accent-700">{t("cropCard.seasonAdjusted")}</p>
                  <h4 className="mt-1 text-lg font-semibold text-text-heading">{tv("crops", advisory.season_adjusted.season_adjusted_crop)}</h4>
                </div>
                <span className="rounded-full border border-accent-200 bg-accent-50 px-3 py-1 text-xs font-semibold text-accent-800">
                  {tv("seasons", advisory.season_adjusted.active_season)}
                </span>
              </div>
              <p className="mt-2 text-xs leading-5 text-text-muted">{translateSeasonAdjustedMessage()}</p>
              <div className="mt-3 space-y-2">
                {advisory.season_adjusted.ranking?.slice(0, 3).map((item) => (
                  <div key={item.crop} className="rounded-2xl border border-surface-border bg-surface-card p-2.5">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-semibold text-text-heading">{tv("crops", item.crop)}</p>
                      <p className="text-sm font-semibold text-accent-700">{item.season_adjusted_score}%</p>
                    </div>
                    <div className="mt-2 h-2 rounded-full bg-surface-muted">
                      <div className="h-2 rounded-full bg-accent-500" style={{ width: `${Math.min(100, item.season_adjusted_score)}%` }} />
                    </div>
                    <p className="mt-2 text-xs text-text-subtle">
                      {t("cropCard.rankingMeta", undefined, {
                        ml: item.ml_confidence,
                        input: item.input_suitability,
                        seasonStatus: item.season_fit ? t("cropCard.fit") : t("cropCard.review"),
                      })}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {advisory ? (
        <details className="advisory-details border-t border-accent-200" open>
          <summary className="flex cursor-pointer items-center justify-between gap-3 px-4 py-4 text-sm font-semibold text-text-heading">
            <span>{t("cropCard.moreDetails", "Advisory details")}</span>
            <span className="text-accent-700">+</span>
          </summary>
        <div className="grid gap-3 px-4 pb-4 lg:grid-cols-[1.15fr,0.85fr]">
          <section className="surface-card-soft border-t border-accent-200 p-4">
            <p className="text-[11px] uppercase tracking-[0.2em] text-accent-600">{t("cropCard.fertilizerAdvice")}</p>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              {advisory.fertilizer?.map((item) => (
                <div key={item.nutrient} className="rounded-2xl border border-surface-border bg-surface-card p-3">
                  <div className="flex items-center justify-between gap-2">
                    <strong className="text-text-heading">{tv("features", item.nutrient)}</strong>
                    <span className="rounded-full bg-accent-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-accent-700">
                      {tv("statuses", item.status)}
                    </span>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-text-muted">
                    {t("cropCard.current")} {item.value} | {t("cropCard.target")} {item.target}
                  </p>
                  <p className="mt-2 text-xs leading-5 text-text-muted">{translateFertilizerRecommendation(item)}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="surface-card-soft p-4">
            <p className="text-[11px] uppercase tracking-[0.2em] text-accent-600">{t("cropCard.seasonContext")}</p>
            <div className="mt-3 space-y-3">
              <div className="rounded-2xl border border-surface-border bg-surface-card p-3">
                <p className="text-[11px] uppercase tracking-[0.18em] text-text-muted">{t("cropCard.goodFit")}</p>
                <p className="mt-1 text-lg font-semibold text-accent-700">
                  {advisory.seasonal_advice?.season_fit ? t("cropCard.yes") : t("cropCard.no")}
                </p>
                {advisory.seasonal_advice?.season_priority ? (
                  <p className="mt-2 text-xs capitalize text-text-subtle">{tv("statuses", advisory.seasonal_advice.season_priority)}</p>
                ) : null}
              </div>
              <p className="text-xs leading-5 text-text-muted">{translateSeasonMessage()}</p>
              <p className="text-xs leading-5 text-text-muted">{translateLocationMessage()}</p>
              {advisory.seasonal_advice?.recommended_season_crops?.length ? (
                <div className="rounded-2xl border border-surface-border bg-surface-card p-3">
                  <p className="text-[11px] uppercase tracking-[0.18em] text-text-muted">{t("cropCard.seasonCropOptions")}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {advisory.seasonal_advice.recommended_season_crops.slice(0, 6).map((seasonCrop) => (
                      <span key={seasonCrop} className="rounded-full border border-accent-200 bg-accent-50 px-3 py-1 text-xs capitalize text-accent-800">
                        {tv("crops", seasonCrop)}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </section>

          {advisory.crop_comparison?.length ? (
            <section className="surface-card-soft border-t border-accent-200 p-4 lg:col-span-2">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.2em] text-accent-600">{t("cropCard.cropComparisonMode")}</p>
                  <h4 className="mt-1 text-lg font-semibold text-text-heading">{t("cropCard.comparisonTitle")}</h4>
                </div>
                <p className="text-xs text-text-muted">{t("cropCard.comparisonSubtitle")}</p>
              </div>
              <div className="mt-3 grid gap-3 md:grid-cols-3">
                {advisory.crop_comparison.map((item) => (
                  <div key={item.crop} className="rounded-2xl border border-surface-border bg-surface-card p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-base font-semibold text-text-heading">{tv("crops", item.crop)}</p>
                        <p className="mt-1 text-xs text-text-subtle">{t("cropCard.waterNeed")}: {tv("waterNeeds", item.water_need)}</p>
                      </div>
                      <span className="rounded-full border border-accent-200 bg-accent-50 px-2.5 py-1 text-xs font-semibold text-accent-800">
                        {item.suitability_score}%
                      </span>
                    </div>
                    <div className="mt-3 h-2 rounded-full bg-surface-muted">
                      <div className="h-2 rounded-full bg-accent-500" style={{ width: `${Math.min(100, item.suitability_score)}%` }} />
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <span className={`rounded-full px-2.5 py-1 text-xs ${item.season_fit ? "bg-accent-50 text-accent-800" : "bg-warning-50 text-warning-700"}`}>
                        {item.season_fit ? t("cropCard.seasonFit") : t("cropCard.seasonReview")}
                      </span>
                      <span className="rounded-full bg-primary-50 px-2.5 py-1 text-xs text-text-muted">
                        {t("cropCard.fertilizerFocus")}: {item.fertilizer_focus}
                      </span>
                    </div>
                    <p className="mt-2 text-xs leading-5 text-text-muted">{t(`cropCard.risks.${String(item.crop || normalizedCrop).toLowerCase()}`, item.risk)}</p>
                  </div>
                ))}
              </div>
            </section>
          ) : null}
        </div>
        </details>
      ) : null}
    </div>
  );
}

export default CropCard;
