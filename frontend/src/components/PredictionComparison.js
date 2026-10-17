import React, { useEffect, useMemo, useState } from "react";
import { ArrowDown, ArrowRight, ArrowUp } from "lucide-react";
import { useLanguage } from "../i18n/LanguageContext";
import ThemedSelect from "./ThemedSelect";

const INPUTS = ["N", "P", "K", "ph", "temperature", "humidity", "rainfall"];

function rowId(row, index) {
  return String(row.id ?? row.ids?.[0] ?? index);
}

function PredictionComparison({ rows = [] }) {
  const { language, t, tv } = useLanguage();
  const options = useMemo(
    () => rows.filter((row) => row.input_data && typeof row.input_data === "object").slice(0, 20),
    [rows]
  );
  const [firstId, setFirstId] = useState("");
  const [secondId, setSecondId] = useState("");

  useEffect(() => {
    if (!options.length) return;
    const ids = options.map(rowId);
    if (!ids.includes(firstId)) setFirstId(ids[0]);
    if (!ids.includes(secondId) || secondId === firstId) setSecondId(ids[1] || ids[0]);
  }, [options, firstId, secondId]);

  const first = options.find((row, index) => rowId(row, index) === firstId);
  const second = options.find((row, index) => rowId(row, index) === secondId);
  if (options.length < 2) return null;

  const locale = language === "hi" ? "hi-IN" : language === "mr" ? "mr-IN" : "en-IN";
  const labelFor = (row, index) => {
    const date = new Date(row.timestamp || "");
    const formatted = Number.isNaN(date.getTime()) ? t("farmer.unknownDate") : date.toLocaleString(locale, { dateStyle: "medium", timeStyle: "short" });
    const crop = row.crop_prediction ? tv("crops", row.crop_prediction) : t("farmer.irrigationOnly");
    return `${formatted} · ${crop} · ${rowId(row, index)}`;
  };
  const recordOptions = options.map((row, index) => ({ value: rowId(row, index), label: labelFor(row, index) }));
  const fields = INPUTS.map((key) => ({
    key,
    before: first?.input_data?.[key],
    after: second?.input_data?.[key],
  })).filter((item) => item.before !== undefined || item.after !== undefined);
  const changedCount = fields.filter((item) => String(item.before ?? "") !== String(item.after ?? "")).length;
  const cropChanged = first?.crop_prediction !== second?.crop_prediction;
  const irrigationChanged = first?.irrigation_prediction != null && second?.irrigation_prediction != null
    ? Number(first.irrigation_prediction) !== Number(second.irrigation_prediction)
    : false;

  const changeIcon = (item) => {
    const delta = Number(item.after) - Number(item.before);
    if (!Number.isFinite(delta) || delta === 0) return <ArrowRight size={14} aria-hidden="true" />;
    return delta > 0 ? <ArrowUp size={14} aria-hidden="true" /> : <ArrowDown size={14} aria-hidden="true" />;
  };
  const formatValue = (value) => value === undefined || value === null || value === ""
    ? "-"
    : Number.isFinite(Number(value)) ? Number(value).toFixed(2).replace(/\.00$/, "") : value;

  return (
    <section className="min-w-0 border-b border-surface-border pb-5" aria-labelledby="prediction-comparison-title">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <span className="section-badge">{t("farmer.comparisonEyebrow")}</span>
          <h3 id="prediction-comparison-title" className="mt-2 text-xl font-semibold text-text-heading">{t("farmer.comparisonTitle")}</h3>
          <p className="mt-1 break-words text-sm text-text-muted">{t("farmer.comparisonSubtitle")}</p>
        </div>
        <p className="break-words text-xs text-text-subtle sm:text-right">{t("farmer.changedInputs", undefined, { count: changedCount })}</p>
      </div>
      <div className="mt-4 grid min-w-0 gap-3 sm:grid-cols-2">
        <label className="min-w-0 space-y-1 text-xs font-medium text-text-muted">
          {t("farmer.comparisonFirst")}
          <ThemedSelect className="min-w-0 max-w-full truncate" value={firstId} onChange={setFirstId} options={recordOptions} />
        </label>
        <label className="min-w-0 space-y-1 text-xs font-medium text-text-muted">
          {t("farmer.comparisonSecond")}
          <ThemedSelect className="min-w-0 max-w-full truncate" value={secondId} onChange={setSecondId} options={recordOptions} />
        </label>
      </div>
      {first && second ? (
        <div className="mt-4 grid min-w-0 gap-4 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
          <dl className="grid min-w-0 grid-cols-2 gap-3">
            <div className="min-w-0 border-l-2 border-primary-500 pl-3"><dt className="break-words text-xs text-text-subtle">{t("farmer.comparisonFirst")} · {t("farmer.crop")}</dt><dd className="mt-1 break-words font-semibold text-text-heading">{first.crop_prediction ? tv("crops", first.crop_prediction) : "-"}</dd></div>
            <div className="min-w-0 border-l-2 border-accent-500 pl-3"><dt className="break-words text-xs text-text-subtle">{t("farmer.comparisonSecond")} · {t("farmer.crop")}</dt><dd className="mt-1 break-words font-semibold text-text-heading">{second.crop_prediction ? tv("crops", second.crop_prediction) : "-"}</dd></div>
            <div className="min-w-0 border-l-2 border-primary-500 pl-3"><dt className="break-words text-xs text-text-subtle">{t("farmer.comparisonFirst")} · {t("farmer.irrigation")}</dt><dd className="mt-1 break-all font-semibold tabular-nums text-text-heading">{formatValue(first.irrigation_prediction)}</dd></div>
            <div className="min-w-0 border-l-2 border-accent-500 pl-3"><dt className="break-words text-xs text-text-subtle">{t("farmer.comparisonSecond")} · {t("farmer.irrigation")}</dt><dd className="mt-1 break-all font-semibold tabular-nums text-text-heading">{formatValue(second.irrigation_prediction)}</dd></div>
            <p className="col-span-2 text-xs text-text-muted">{t("farmer.predictionOutcomeChange", undefined, { crop: cropChanged ? t("farmer.changed") : t("farmer.unchanged"), irrigation: irrigationChanged ? t("farmer.changed") : t("farmer.unchanged") })}</p>
          </dl>
          <div className="hidden min-w-0 overflow-x-auto md:block">
            <table className="prediction-comparison-table w-full min-w-0 border-collapse text-sm">
              <thead><tr className="border-b border-surface-border text-left text-xs text-text-subtle"><th className="py-2 pr-3">{t("farmer.input")}</th><th className="px-3 py-2">{t("farmer.comparisonFirst")}</th><th className="px-3 py-2">{t("farmer.comparisonSecond")}</th><th className="px-3 py-2">{t("farmer.change")}</th></tr></thead>
              <tbody>{fields.map((item) => {
                const changed = String(item.before ?? "") !== String(item.after ?? "");
                return <tr key={item.key} className="border-b border-surface-border last:border-0">
                  <th scope="row" className="py-2 pr-3 text-left font-medium text-text-heading">{tv("features", item.key)}</th>
                  <td className="px-3 py-2 tabular-nums text-text-muted">{formatValue(item.before)}</td>
                  <td className="px-3 py-2 tabular-nums text-text-muted">{formatValue(item.after)}</td>
                  <td className={`px-3 py-2 ${changed ? "font-semibold text-accent-800" : "text-text-subtle"}`}><span className="inline-flex items-center gap-1">{changeIcon(item)}{changed ? t("farmer.changed") : t("farmer.unchanged")}</span></td>
                </tr>;
              })}</tbody>
            </table>
          </div>
          <dl className="grid min-w-0 gap-2 md:hidden">
            {fields.map((item) => {
              const changed = String(item.before ?? "") !== String(item.after ?? "");
              return <div key={item.key} className="grid min-w-0 grid-cols-[minmax(0,0.8fr),minmax(0,1.2fr)] gap-3 border-b border-surface-border py-2.5 last:border-0">
                <dt className="min-w-0 break-words text-sm font-medium text-text-heading">{tv("features", item.key)}</dt>
                <dd className="min-w-0">
                  <p className="break-words text-xs tabular-nums text-text-muted">{t("farmer.comparisonFirst")}: <strong className="text-text-heading">{formatValue(item.before)}</strong></p>
                  <p className="mt-1 break-words text-xs tabular-nums text-text-muted">{t("farmer.comparisonSecond")}: <strong className="text-text-heading">{formatValue(item.after)}</strong></p>
                  <p className={`mt-1 inline-flex items-center gap-1 text-xs ${changed ? "font-semibold text-accent-800" : "text-text-subtle"}`}>{changeIcon(item)}{changed ? t("farmer.changed") : t("farmer.unchanged")}</p>
                </dd>
              </div>;
            })}
          </dl>
        </div>
      ) : null}
    </section>
  );
}

export default PredictionComparison;
