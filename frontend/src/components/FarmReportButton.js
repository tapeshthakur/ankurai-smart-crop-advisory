import React, { useRef, useState } from "react";
import { Download, X } from "lucide-react";
import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";
import api from "../api/client";
import { getFieldSnapshot, saveFieldSnapshot } from "../api/offlineFieldStore";
import { useLanguage } from "../i18n/LanguageContext";
import { soilDataText } from "../i18n/soilTranslations";

function FarmReportButton({ farmId, fieldId, userId, result, advisory, predictions = [], tasks = [], weatherForecast }) {
  const { t, tv, language } = useLanguage();
  const [report, setReport] = useState(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const reportRef = useRef(null);
  const tr = (key, fallback, params) => t(`farmReport.${key}`, fallback, params);

  const prepareReport = async () => {
    if (!farmId || !fieldId) return;
    setBusy(true);
    setError("");
    const cacheKey = `field:${farmId}:${fieldId}`;
    try {
      const cached = await getFieldSnapshot(cacheKey).catch(() => null);
      let farm = null;
      let soilData = cached?.data || {};
      soilData = { ...soilData, tasks: tasks.length ? tasks : soilData.tasks };
      if (navigator.onLine) {
        try {
          const response = await api.get("/api/farms");
          farm = (response.data.farms || []).find((item) => String(item.id) === String(farmId)) || null;
          const fieldQuery = `?field_id=${encodeURIComponent(fieldId)}`;
          const [plan, readiness] = await Promise.all([
            api.get(`/api/farms/${farmId}/soil-plan${fieldQuery}`),
            api.get(`/api/farms/${farmId}/carbon-readiness${fieldQuery}`),
          ]);
          soilData = { ...soilData, plan: plan.data.plan, tasks: tasks.length ? tasks : (plan.data.tasks || []), readiness: readiness.data };
          await saveFieldSnapshot(cacheKey, soilData).catch(() => {});
        } catch {
          farm = null;
        }
      }
      if (!farm) {
        const farmsSnapshot = await getFieldSnapshot(`farms:${userId || "current"}`).catch(() => null);
        farm = (farmsSnapshot?.data?.farms || []).find((item) => String(item.id) === String(farmId)) || null;
      }
      const field = farm?.fields?.find((item) => String(item.id) === String(fieldId));
      setReport({
        farmName: farm?.name || tr("farmFallback", "Farm {{id}}", { id: farmId }),
        fieldName: field?.name || tr("fieldFallback", "Field {{id}}", { id: fieldId }),
        fieldArea: field?.area_ha || soilData.readiness?.field?.area_ha,
        result,
        advisory,
        predictions: predictions.slice(0, 5),
        weatherForecast,
        ...soilData,
        generatedAt: new Date(),
      });
      setOpen(true);
    } catch {
      setError(tr("loadFailed", "Could not prepare the farm report."));
    } finally {
      setBusy(false);
    }
  };

  const downloadPdf = async () => {
    if (!reportRef.current) return;
    setBusy(true);
    setError("");
    try {
      const canvas = await html2canvas(reportRef.current, { scale: 2, backgroundColor: "#ffffff", useCORS: true });
      const pdf = new jsPDF("p", "mm", "a4");
      const pageWidth = pdf.internal.pageSize.getWidth() - 24;
      const pageHeight = pdf.internal.pageSize.getHeight() - 24;
      const sliceHeight = Math.floor(canvas.width * pageHeight / pageWidth);
      const pageCanvas = document.createElement("canvas");
      const context = pageCanvas.getContext("2d");
      pageCanvas.width = canvas.width;
      for (let offset = 0, page = 0; offset < canvas.height; offset += sliceHeight, page += 1) {
        const height = Math.min(sliceHeight, canvas.height - offset);
        pageCanvas.height = height;
        context.clearRect(0, 0, pageCanvas.width, height);
        context.drawImage(canvas, 0, offset, canvas.width, height, 0, 0, canvas.width, height);
        if (page) pdf.addPage();
        pdf.addImage(pageCanvas.toDataURL("image/png"), "PNG", 12, 12, pageWidth, height * pageWidth / canvas.width, undefined, "FAST");
      }
      pdf.save(`${report.fieldName.replace(/[^\p{L}\p{N}_-]+/gu, "-")}-farm-report.pdf`);
    } catch {
      setError(tr("pdfFailed", "Could not create the PDF. Try again or use your browser's print option."));
    } finally {
      setBusy(false);
    }
  };

  const locale = language === "hi" ? "hi-IN" : language === "mr" ? "mr-IN" : "en-IN";
  const dateLabel = (value) => value ? new Date(value).toLocaleDateString(locale, { dateStyle: "medium" }) : tr("notRecorded", "Not recorded");
  const sectionClass = "mt-6 border-t border-surface-border pt-4";

  return <>
    <button type="button" onClick={prepareReport} disabled={!farmId || !fieldId || busy} className="theme-button-primary inline-flex min-h-11 w-full items-center justify-center gap-2 px-4 py-2.5 text-center disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto">
      <Download size={17} aria-hidden="true" />{busy ? tr("preparing", "Preparing…") : tr("download", "Download farm report")}
    </button>
    {open && report ? (
      <div className="fixed inset-0 z-[100] flex items-end justify-center bg-black/50 p-0 sm:items-center sm:p-5" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) setOpen(false); }}>
        <section className="flex max-h-[94dvh] w-full max-w-3xl flex-col overflow-hidden bg-white shadow-xl sm:max-h-[90dvh] sm:rounded-lg" role="dialog" aria-modal="true" aria-labelledby="farm-report-title">
          <header className="flex items-center justify-between gap-3 border-b border-surface-border px-4 py-3 sm:px-5">
            <h2 id="farm-report-title" className="min-w-0 break-words text-base font-semibold text-text-heading">{tr("previewTitle", "Farm report preview")}</h2>
            <button type="button" onClick={() => setOpen(false)} className="inline-flex h-10 w-10 items-center justify-center rounded-md text-text-muted hover:bg-surface-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary-700" aria-label={tr("close", "Close report preview")} title={tr("close", "Close report preview")}><X size={19} /></button>
          </header>
          <div className="overflow-y-auto p-3 sm:p-5">
            <article ref={reportRef} className="mx-auto max-w-[760px] bg-white p-5 text-sm leading-6 text-[#29332B] sm:p-8">
              <p className="text-xs font-semibold uppercase text-[#8F6E24]">AnkurAI · {tr("reportLabel", "Farm report")}</p>
              <h1 className="mt-2 text-2xl font-bold text-[#203A29]">{report.farmName}</h1>
              <p className="mt-1 text-base">{report.fieldName}{report.fieldArea ? ` · ${report.fieldArea} ha` : ""}</p>
              <p className="mt-2 text-xs text-[#5F6C61]">{tr("generated", "Generated")}: {report.generatedAt.toLocaleString(locale)}</p>

              <section className={sectionClass}>
                <h2 className="text-base font-bold">{tr("advisory", "Latest crop advisory")}</h2>
                {report.result ? <ul className="mt-2 space-y-1">
                  <li>{tr("crop", "Recommended crop")}: <strong>{tv("crops", report.result.crop)}</strong></li>
                  <li>{tr("confidence", "Model confidence")}: <strong>{Number((Number(report.result.confidence) <= 1 ? Number(report.result.confidence) * 100 : Number(report.result.confidence)) || 0).toFixed(1)}%</strong></li>
                  {report.result.irrigation !== undefined && report.result.irrigation !== null ? <li>{tr("irrigation", "Irrigation estimate")}: <strong>{report.result.irrigation}</strong></li> : null}
                  {report.advisory?.production_outlook?.harvest_window ? <li>{tr("harvest", "Expected harvest")}: {report.advisory.production_outlook.harvest_window.start || ""} {report.advisory.production_outlook.harvest_window.end ? `– ${report.advisory.production_outlook.harvest_window.end}` : ""}</li> : null}
                </ul> : <p>{tr("noAdvisory", "No crop recommendation is saved in this dashboard snapshot.")}</p>}
              </section>

              {report.plan?.plan?.length ? <section className={sectionClass}>
                <h2 className="text-base font-bold">{tr("soilPlan", "Soil restoration plan")}</h2>
                <ul className="mt-2 space-y-2">{report.plan.plan.map((year, index) => <li key={`${year.year || index}`}><strong>{tr("year", "Year")} {year.year || index + 1}</strong>: {[year.rotation, year.cover_crop, year.microbial_support].filter(Boolean).join(" · ")}</li>)}</ul>
              </section> : null}

              {report.tasks?.length ? <section className={sectionClass}>
                <h2 className="text-base font-bold">{tr("fieldTasks", "Field tasks")}</h2>
                <ul className="mt-2 space-y-1">{report.tasks.map((task) => <li key={task.id}><strong>{dateLabel(task.due_date)} · {soilDataText(language, task.status)}</strong>: {soilDataText(language, task.title)}{task.notes ? ` — ${task.notes}` : ""}</li>)}</ul>
              </section> : null}

              {report.readiness?.soil_tests?.length ? <section className={sectionClass}>
                <h2 className="text-base font-bold">{tr("soilTests", "Soil test records")}</h2>
                <ul className="mt-2 space-y-1">{report.readiness.soil_tests.map((item) => <li key={item.id}><strong>{dateLabel(item.sample_date)}</strong>: {tr("organicCarbon", "Organic carbon")} {item.organic_carbon_pct}%{item.ph !== null ? ` · pH ${item.ph}` : ""}{item.lab_name ? ` · ${item.lab_name}` : ""}</li>)}</ul>
              </section> : null}

              {report.readiness?.practices?.length ? <section className={sectionClass}>
                <h2 className="text-base font-bold">{tr("practices", "Recorded farm practices")}</h2>
                <ul className="mt-2 space-y-1">{report.readiness.practices.map((item) => <li key={item.id}><strong>{dateLabel(item.start_date)}</strong>: {soilDataText(language, item.practice_type)}{item.area_ha ? ` · ${item.area_ha} ha` : ""}{item.notes ? ` · ${item.notes}` : ""}</li>)}</ul>
              </section> : null}

              {report.weatherForecast?.days?.length ? <section className={sectionClass}>
                <h2 className="text-base font-bold">{tr("weather", "Weather outlook")}</h2>
                <ul className="mt-2 grid grid-cols-2 gap-x-4">{report.weatherForecast.days.slice(0, 7).map((day) => <li key={day.date}>{dateLabel(day.date)}: {day.temperature_max_c ?? "–"} °C · {day.precipitation_mm ?? "–"} mm</li>)}</ul>
              </section> : null}

              {report.predictions.length ? <section className={sectionClass}>
                <h2 className="text-base font-bold">{tr("recentHistory", "Recent account predictions")}</h2>
                <ul className="mt-2 space-y-1">{report.predictions.map((item, index) => <li key={item.id || index}>{dateLabel(item.timestamp)}: {item.crop_prediction ? tv("crops", item.crop_prediction) : tr("irrigationOnly", "Irrigation only")}{item.irrigation_prediction != null ? ` · ${tr("irrigation", "Irrigation")}: ${item.irrigation_prediction}` : ""}</li>)}</ul>
                <p className="mt-2 text-xs text-[#5F6C61]">{tr("accountHistoryNote", "Prediction history is account-wide and is not attributed to this field.")}</p>
              </section> : null}
              <p className="mt-7 border-t border-[#DDE5DD] pt-3 text-xs text-[#5F6C61]">{tr("disclaimer", "Planning information only. Verify field actions with current soil tests and local agricultural guidance.")}</p>
            </article>
          </div>
          {error ? <p className="px-4 pb-2 text-sm text-danger-700" role="alert">{error}</p> : null}
          <footer className="flex flex-col-reverse gap-2 border-t border-surface-border p-3 sm:flex-row sm:justify-end sm:px-5">
            <button type="button" className="theme-button-secondary min-h-11 px-4 py-2" onClick={() => setOpen(false)} disabled={busy}>{tr("close", "Close")}</button>
            <button type="button" className="theme-button-primary inline-flex min-h-11 items-center justify-center gap-2 px-4 py-2" onClick={downloadPdf} disabled={busy}><Download size={16} aria-hidden="true" />{busy ? tr("creatingPdf", "Creating PDF…") : tr("savePdf", "Download PDF")}</button>
          </footer>
        </section>
      </div>
    ) : null}
    {error && !open ? <p className="sr-only" role="alert">{error}</p> : null}
  </>;
}

export default FarmReportButton;
