import React, { useEffect, useState } from "react";
import api from "../api/client";
import LoadingSpinner from "./LoadingSpinner";
import { useLanguage } from "../i18n/LanguageContext";

const MAX_IMAGE_SIZE = 5 * 1024 * 1024;
const ALLOWED_TYPES = ["image/jpeg", "image/jpg", "image/png"];

function DiseaseDetector() {
  const { t, tv } = useLanguage();
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    if (!file) {
      setPreviewUrl("");
      return undefined;
    }

    const nextPreview = URL.createObjectURL(file);
    setPreviewUrl(nextPreview);
    return () => URL.revokeObjectURL(nextPreview);
  }, [file]);

  const chooseFile = (nextFile) => {
    setError("");
    setResult(null);

    if (!nextFile) return;
    if (!ALLOWED_TYPES.includes(nextFile.type)) {
      setError(t("disease.badType"));
      return;
    }
    if (nextFile.size > MAX_IMAGE_SIZE) {
      setError(t("disease.bigFile"));
      return;
    }

    setFile(nextFile);
  };

  const detectDisease = async () => {
    if (!file) {
      setError(t("disease.selectFile"));
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      setLoading(true);
      setError("");
      const response = await api.post("/api/disease/detect", formData, { headers: { "Content-Type": "multipart/form-data" } });
       setResult(response.data.result || null);
    } catch (err) {
      setError(err.response?.data?.error || t("disease.failed"));
    } finally {
      setLoading(false);
    }
  };
  const diseaseKey = (name = "") => {
    const lower = String(name).toLowerCase();
    if (lower.includes("healthy")) return "healthy";
    if (lower.includes("rust")) return "rust";
    if (lower.includes("yellow") || lower.includes("mosaic") || lower.includes("virus") || lower.includes("nutrient")) return "nutrient";
    if (lower.includes("scorch") || lower.includes("dry")) return "scorch";
    if (lower.includes("spot") || lower.includes("blight") || lower.includes("scab") || lower.includes("rot")) return "spot";
    return "generic";
  };
  const translateDiseaseName = (name) => {
    const key = diseaseKey(name);
    return key === "generic" ? name : t(`disease.names.${key}`, name);
  };
  const translateTreatment = (name, text) => t(`disease.treatments.${diseaseKey(name)}`, text);
  const translatePrevention = (name, text) => t(`disease.preventionText.${diseaseKey(name)}`, text);
  const translateModelNote = (note) => {
    const lower = String(note || "").toLowerCase();
    if (lower.includes("mobilenet")) return t("disease.modelNoteCnn");
    if (lower.includes("fallback")) return t("disease.modelNoteFallback");
    return note;
  };
  const confidenceLabel = (status) => t(`disease.confidenceLevels.${status}`, status || "-");
  const qualityWarnings = result?.upload_quality?.warnings || [];

  return (
    <section className="surface-card p-4 sm:p-6">
      <div className="mb-6 flex flex-col gap-2">
        <span className="section-badge">{t("disease.module")}</span>
        <h2 className="text-2xl font-semibold text-text-heading sm:text-3xl">{t("disease.title")}</h2>
        <p className="max-w-2xl text-sm leading-6 text-text-muted">{t("disease.subtitle")}</p>
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.95fr,1.05fr]">
        <div
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            chooseFile(event.dataTransfer.files?.[0]);
          }}
          className={[
            "flex cursor-pointer flex-col rounded-[1.7rem] text-center transition-all duration-200",
            previewUrl
              ? "border border-surface-border/55 bg-surface-card p-3"
              : "min-h-[260px] items-center justify-center border-2 border-dashed p-5 sm:min-h-[340px]",
            dragging
              ? "border-accent-400 bg-accent-50"
              : "border-surface-border bg-surface-muted hover:border-accent-300",
          ].join(" ")}
        >
          {previewUrl ? (
            <div className="w-full">
              <img src={previewUrl} alt={t("disease.previewAlt")} className="aspect-[4/3] w-full rounded-[1.25rem] object-cover shadow-card" />
              <div className="mt-3 rounded-[1.1rem] border border-surface-border bg-surface-card p-3">
                <div className="flex flex-col gap-2 text-left sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-text-heading">{file?.name}</p>
                    <p className="mt-1 text-xs text-text-subtle">{t("disease.ready")}</p>
                  </div>
                  <span className="w-fit rounded-full border border-accent-200 bg-accent-50 px-3 py-1 text-xs font-semibold text-accent-800">
                    {(file?.size / (1024 * 1024)).toFixed(2)} MB
                  </span>
                </div>
                <p className="mt-3 text-left text-xs leading-5 text-text-subtle">{t("disease.changeImage")}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <label htmlFor="disease-camera" className="disease-capture-button disease-capture-button-primary">CAM <span>Retake</span></label>
                  <label htmlFor="disease-gallery" className="disease-capture-button">IMG <span>Change photo</span></label>
                </div>
              </div>
              <div className="mt-3 rounded-[1.1rem] border border-accent-200 bg-accent-50 p-4 text-left">
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-accent-700">
                  {result ? t("disease.analysisDetails", "Analysis details") : t("disease.photoChecklist", "Photo checklist")}
                </p>
                {result ? (
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    <div>
                      <p className="text-xs text-text-subtle">{t("disease.plant", "Plant")}</p>
                      <p className="mt-1 text-sm font-semibold text-text-heading">{result.plant || t("disease.unknownPlant")}</p>
                    </div>
                    <div>
                      <p className="text-xs text-text-subtle">{t("disease.condition", "Condition")}</p>
                      <p className="mt-1 text-sm font-semibold text-text-heading">{result.condition || translateDiseaseName(result.disease)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-text-subtle">{t("disease.leafArea", "Leaf area")}</p>
                      <p className="mt-1 text-sm font-semibold text-accent-700">
                        {result.upload_quality?.leaf_area_percent !== undefined ? `${Number(result.upload_quality.leaf_area_percent).toFixed(1)}%` : "-"}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-text-subtle">{t("disease.brightness", "Brightness")}</p>
                      <p className="mt-1 text-sm font-semibold text-accent-700">
                        {result.upload_quality?.brightness !== undefined ? Number(result.upload_quality.brightness).toFixed(1) : "-"}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-text-subtle">{t("disease.focus", "Focus")}</p>
                      <p className="mt-1 text-sm font-semibold text-accent-700">
                        {result.upload_quality?.focus_score !== undefined ? Number(result.upload_quality.focus_score).toFixed(1) : "-"}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-text-subtle">{t("disease.margin", "Model margin")}</p>
                      <p className="mt-1 text-sm font-semibold text-accent-700">
                        {result.prediction_margin !== null && result.prediction_margin !== undefined ? `${Number(result.prediction_margin).toFixed(1)}%` : "-"}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="mt-3 grid gap-2 text-sm leading-6 text-text-muted">
                    <p>{t("disease.tipSingleLeaf", "Use one clear leaf, close to the camera.")}</p>
                    <p>{t("disease.tipLighting", "Keep good natural light and avoid blur.")}</p>
                    <p>{t("disease.tipBackground", "Avoid too much soil, hand, or background in the photo.")}</p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="w-full">
              <div className="disease-camera-mark">LD</div>
              <p className="text-xl font-semibold text-text-heading">{t("disease.drop")}</p>
              <p className="mt-3 text-sm leading-6 text-text-muted">{t("disease.browse")}</p>
              <div className="disease-capture-actions mt-5">
                <label htmlFor="disease-camera" className="disease-capture-button disease-capture-button-primary">CAM <span>Take photo</span></label>
                <label htmlFor="disease-gallery" className="disease-capture-button">IMG <span>Choose photo</span></label>
              </div>
              <div className="disease-quality-guide mt-5">
                <span>1 leaf</span>
                <span>Good light</span>
                <span>No blur</span>
              </div>
            </div>
          )}
          <input id="disease-camera" type="file" accept="image/png,image/jpeg,image/jpg" capture="environment" className="hidden" onChange={(event) => chooseFile(event.target.files?.[0])} />
          <input id="disease-gallery" type="file" accept="image/png,image/jpeg,image/jpg" className="hidden" onChange={(event) => chooseFile(event.target.files?.[0])} />
        </div>

        <div className="surface-card-soft p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="text-xl font-semibold text-text-heading">{t("disease.result")}</h3>
              <p className="mt-1 text-sm text-text-muted">{t("disease.resultSubtitle")}</p>
            </div>
            <button type="button" onClick={detectDisease} disabled={loading || !file} className="theme-button-primary w-full px-4 py-3 sm:w-auto disabled:opacity-60">
              {t("disease.detect")}
            </button>
          </div>

          {loading ? <div className="mt-5"><LoadingSpinner label={t("disease.analysing")} /></div> : null}
          {error ? <p className="mt-5 rounded-2xl border border-danger-100 bg-danger-50 px-4 py-3 text-sm text-danger-700">{error}</p> : null}

          {result ? (
            <div className="mt-5 space-y-4">
              <div className="surface-card-highlight p-5">
                <p className="text-[11px] uppercase tracking-[0.22em] text-accent-700">{t("disease.predicted")}</p>
                <div className="mt-3 grid gap-4 lg:grid-cols-[1fr,auto] lg:items-end">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.16em] text-text-subtle">{result.plant || t("disease.unknownPlant")}</p>
                    <p className="mt-2 text-3xl font-bold text-text-heading">
                      {result.is_healthy ? t("disease.healthyStatus", "Healthy") : (result.condition || translateDiseaseName(result.disease))}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 lg:justify-end">
                    <p className="rounded-full border border-accent-200 bg-accent-50 px-3 py-1 text-sm font-semibold text-accent-700">
                      {Number(result.confidence).toFixed(2)}% {t("disease.confidence")}
                    </p>
                    <p className="rounded-full border border-surface-border bg-surface-card px-3 py-1 text-sm font-semibold text-text-muted">
                      {confidenceLabel(result.confidence_status)}
                    </p>
                  </div>
                </div>
                <p className="mt-3 text-sm capitalize text-text-muted">{t("disease.severity")}: {tv("statuses", result.severity)}</p>
                {result.warning ? (
                  <p className="mt-3 rounded-2xl border border-warning-100 bg-warning-50 px-4 py-3 text-sm leading-6 text-warning-700">
                    {result.warning}
                  </p>
                ) : null}
                {result.crop_mismatch?.message ? (
                  <p className="mt-3 rounded-2xl border border-danger-100 bg-danger-50 px-4 py-3 text-sm leading-6 text-danger-700">
                    {result.crop_mismatch.message}
                  </p>
                ) : null}
                {result.needs_review ? (
                  <p className="mt-3 rounded-2xl border border-warning-100 bg-warning-50 px-4 py-3 text-sm leading-6 text-warning-700">
                    {t("disease.reviewWarning")}
                  </p>
                ) : null}
              </div>

              {qualityWarnings.length ? (
                <div className="rounded-[1.35rem] border border-warning-100 bg-warning-50 p-4">
                  <p className="text-sm font-semibold text-warning-700">{t("disease.photoQuality")}</p>
                  <ul className="mt-2 space-y-2 text-sm leading-6 text-text-muted">
                    {qualityWarnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-[1.35rem] border border-surface-border bg-surface-card p-4">
                  <p className="text-sm font-semibold text-text-heading">{t("disease.treatment")}</p>
                  <p className="mt-2 text-sm leading-7 text-text-muted">{translateTreatment(result.disease, result.treatment)}</p>
                </div>
                <div className="rounded-[1.35rem] border border-surface-border bg-surface-card p-4">
                  <p className="text-sm font-semibold text-text-heading">{t("disease.prevention")}</p>
                  <p className="mt-2 text-sm leading-7 text-text-muted">{translatePrevention(result.disease, result.prevention)}</p>
                </div>
              </div>

              {result.next_steps?.length ? (
                <div className="rounded-[1.35rem] border border-accent-200 bg-accent-50 p-4">
                  <p className="text-sm font-semibold text-accent-800">{t("disease.nextSteps")}</p>
                  <div className="mt-3 grid gap-2 sm:grid-cols-3">
                    {result.next_steps.map((step, index) => (
                      <div key={step} className="rounded-2xl border border-surface-border bg-surface-card p-3">
                        <p className="text-[11px] uppercase tracking-[0.18em] text-accent-700">{t("farmer.step")} {index + 1}</p>
                        <p className="mt-2 text-sm leading-6 text-text-muted">{step}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              <div className="rounded-[1.35rem] border border-surface-border bg-surface-card p-4">
                <p className="text-sm font-semibold text-text-heading">{t("disease.topMatches")}</p>
                <div className="mt-3 grid gap-2 sm:grid-cols-3">
                  {result.top_3?.map(([name, score]) => (
                    <div key={name} className="rounded-2xl border border-surface-border bg-primary-50 p-3">
                      <p className="text-xs leading-5 text-text-muted">{name}</p>
                      <p className="mt-1 text-base font-semibold text-accent-700">{Number(score).toFixed(2)}%</p>
                    </div>
                  ))}
                </div>
              </div>

              <p className="text-xs leading-6 text-text-subtle">{translateModelNote(result.model_note)}</p>
            </div>
          ) : (
            <p className="mt-5 rounded-[1.35rem] border border-dashed border-surface-border bg-surface-muted p-5 text-sm leading-7 text-text-muted">
              {t("disease.helper")}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

export default DiseaseDetector;
