import React, { useCallback, useEffect, useMemo, useState } from "react";
import api from "../api/client";
import { useLanguage } from "../i18n/LanguageContext";
import { soilDataText, soilText } from "../i18n/soilTranslations";
import { getFieldSnapshot, getPendingTaskNotes, removePendingTaskNote, saveFieldSnapshot, savePendingTaskNote } from "../api/offlineFieldStore";

const PRACTICE_OPTIONS = [
  ["cover_crop", "Cover crop"],
  ["crop_rotation", "Crop rotation"],
  ["reduced_tillage", "Reduced tillage"],
  ["residue_retention", "Residue retention"],
  ["compost", "Compost or organic amendments"],
  ["agroforestry", "Agroforestry"],
  ["nutrient_management", "Nutrient management"],
  ["other", "Other"],
];

function localDate() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function formatDate(value, language) {
  if (!value) return soilText(language, "noSchedule", "Not scheduled");
  const locale = language === "hi" ? "hi-IN" : language === "mr" ? "mr-IN" : undefined;
  return new Date(`${value}T00:00:00`).toLocaleDateString(locale);
}

function csvCell(value) {
  const text = String(value ?? "");
  const safeText = /^[=+@\-\t\r]/.test(text) ? `'${text}` : text;
  return `"${safeText.replaceAll('"', '""')}"`;
}

const ignoreTaskUpdate = () => {};

function SoilPlanningWorkspace({ farmId, fieldId, proposal, plantingDate, onOpenFarm, tasks = [], predictions = [], onTasksChange }) {
  const { language } = useLanguage();
  const tr = (key, fallback) => soilText(language, key, fallback);
  const practiceLabel = (value, fallback) => soilText(language, value, fallback);
  const [savedPlan, setSavedPlan] = useState(null);
  const [draftPlan, setDraftPlan] = useState(proposal);
  const [readiness, setReadiness] = useState(null);
  const [planStartDate, setPlanStartDate] = useState(plantingDate || localDate());
  const [sample, setSample] = useState({ sample_date: localDate(), organic_carbon_pct: "", ph: "", nitrogen: "", phosphorus: "", potassium: "", nutrient_units: "", lab_name: "", evidence_reference: "", notes: "" });
  const [practice, setPractice] = useState({ practice_type: "cover_crop", start_date: localDate(), end_date: "", area_ha: "", evidence_reference: "", notes: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const setTasks = onTasksChange || ignoreTaskUpdate;
  const fieldCacheKey = `field:${farmId}:${fieldId}`;

  const load = async () => {
    if (!farmId || !fieldId) {
      setSavedPlan(null);
      setTasks([]);
      setReadiness(null);
      return;
    }
    setError("");
    try {
      const query = `?field_id=${encodeURIComponent(fieldId)}`;
      const [planResponse, carbonResponse] = await Promise.all([
        api.get(`/api/farms/${farmId}/soil-plan${query}`),
        api.get(`/api/farms/${farmId}/carbon-readiness${query}`),
      ]);
      const cachedTasks = planResponse.data.tasks || [];
      const queued = await getPendingTaskNotes().catch(() => []);
      const queuedById = new Map(queued.map((entry) => [entry.task_id, entry]));
      const visibleTasks = cachedTasks.map((task) => queuedById.has(task.id)
        ? { ...task, ...queuedById.get(task.id) }
        : task);
      setSavedPlan(planResponse.data.plan);
      setDraftPlan(proposal || planResponse.data.plan?.plan || null);
      if (planResponse.data.plan?.start_date) setPlanStartDate(planResponse.data.plan.start_date);
      setTasks(visibleTasks);
      setReadiness(carbonResponse.data);
      try {
        await saveFieldSnapshot(fieldCacheKey, { plan: planResponse.data.plan, tasks: visibleTasks, readiness: carbonResponse.data });
      } catch { /* The online view remains usable without local caching. */ }
      setNotice(queued.length ? soilText(language, "offlinePending", "Offline field edits are waiting to sync.") : "");
    } catch (err) {
      const snapshot = await getFieldSnapshot(fieldCacheKey).catch(() => null);
      if (snapshot?.data) {
        setSavedPlan(snapshot.data.plan);
        setDraftPlan(proposal || snapshot.data.plan?.plan || null);
        setTasks(snapshot.data.tasks || []);
        setReadiness(snapshot.data.readiness || null);
        setNotice(soilText(language, "offlineSnapshot", "Showing the last saved field snapshot. Changes will sync when you are online."));
      } else {
        setError(tr("soilRecordsError", "Could not load soil records."));
      }
    }
  };

  useEffect(() => {
    if (proposal) setDraftPlan(proposal);
  }, [proposal]);

  useEffect(() => {
    load();
  }, [farmId, fieldId]);

  const syncQueuedChanges = useCallback(async () => {
    if (!navigator.onLine) return;
    const queued = await getPendingTaskNotes().catch(() => []);
    let synced = 0;
    for (const entry of queued) {
      try {
        const response = await api.patch(`/api/soil-plan-tasks/${entry.task_id}`, {
          status: entry.status || "planned",
          notes: entry.notes || "",
        });
        setTasks((current) => current.map((task) => task.id === entry.task_id ? response.data.task : task));
        await removePendingTaskNote(entry.task_id);
        synced += 1;
      } catch {
        break;
      }
    }
    if (synced) setNotice(soilText(language, "offlineSynced", "Offline field edits synced."));
  }, [farmId, fieldId, language, onTasksChange]);

  useEffect(() => {
    window.addEventListener("online", syncQueuedChanges);
    if (navigator.onLine) syncQueuedChanges();
    return () => window.removeEventListener("online", syncQueuedChanges);
  }, [syncQueuedChanges]);

  const tasksByYear = useMemo(() => tasks.reduce((groups, task) => {
    groups[task.year_number] = groups[task.year_number] || [];
    groups[task.year_number].push(task);
    return groups;
  }, {}), [tasks]);

  const savePlan = async () => {
    if (!draftPlan || !farmId || !fieldId) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const response = await api.post(`/api/farms/${farmId}/soil-plan`, {
        field_id: Number(fieldId),
        start_date: planStartDate,
        plan: draftPlan,
      });
      setSavedPlan(response.data.plan);
      setTasks(response.data.tasks || []);
      setNotice(tr("planSaved", "Five-year plan saved to this field."));
    } catch (err) {
      setError(tr("planSaveError", "Could not save the soil plan."));
    } finally {
      setBusy(false);
    }
  };

  const changeTask = async (task, status, notes = task.notes || "") => {
    setError("");
    try {
      const response = await api.patch(`/api/soil-plan-tasks/${task.id}`, { status, notes });
      setTasks((current) => current.map((item) => item.id === task.id ? response.data.task : item));
    } catch (err) {
      if (!err.response || !navigator.onLine) {
        try {
          await savePendingTaskNote(task.id, notes, status);
          setTasks((current) => current.map((item) => item.id === task.id ? { ...item, status, notes } : item));
          setNotice(tr("offlineEditSaved", "Saved on this device. It will sync when you are online."));
          return;
        } catch { /* Show the normal update error if local storage is unavailable. */ }
      }
      setError(tr("taskUpdateError", "Could not update this plan task."));
    }
  };

  const addSample = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post(`/api/farms/${farmId}/soil-tests`, { ...sample, field_id: Number(fieldId) });
      setSample({ sample_date: localDate(), organic_carbon_pct: "", ph: "", nitrogen: "", phosphorus: "", potassium: "", nutrient_units: "", lab_name: "", evidence_reference: "", notes: "" });
      setNotice(tr("soilTestAdded", "Soil test record added."));
      await load();
    } catch (err) {
      setError(tr("soilTestSaveError", "Could not save the soil test."));
    } finally {
      setBusy(false);
    }
  };

  const addPractice = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post(`/api/farms/${farmId}/regenerative-practices`, { ...practice, field_id: Number(fieldId) });
      setPractice({ practice_type: "cover_crop", start_date: localDate(), end_date: "", area_ha: "", evidence_reference: "", notes: "" });
      setNotice(tr("practiceAdded", "Practice record added."));
      await load();
    } catch (err) {
      setError(tr("practiceSaveError", "Could not save this practice."));
    } finally {
      setBusy(false);
    }
  };

  const exportFieldLog = () => {
    const rows = [["Record type", "Date", "Status or category", "Details", "Area (ha)", "Evidence", "Notes"]];
    rows.push(["Export scope", "", "", "Field records are for the selected field; saved predictions are account-wide because prediction records are not linked to fields.", "", "", ""]);
    predictions.forEach((prediction) => rows.push([
      "Crop and irrigation prediction",
      prediction.timestamp,
      prediction.crop_prediction || "Irrigation only",
      JSON.stringify(prediction.input_data || {}),
      "",
      "",
      prediction.irrigation_prediction ?? "",
    ]));
    tasks.forEach((task) => rows.push(["Plan task", task.due_date, `${task.year_number} ${task.season} / ${task.status}`, `${task.title}: ${task.description}`, "", "", task.notes]));
    (readiness?.soil_tests || []).forEach((record) => rows.push(["Soil test", record.sample_date, "Laboratory result", `Organic carbon ${record.organic_carbon_pct}%; pH ${record.ph ?? ""}; N ${record.nitrogen ?? ""}; P ${record.phosphorus ?? ""}; K ${record.potassium ?? ""} ${record.nutrient_units || ""}; ${record.lab_name || ""}`, "", record.evidence_reference, record.notes]));
    (readiness?.practices || []).forEach((record) => rows.push(["Practice", record.start_date, record.practice_type, record.end_date ? `Through ${record.end_date}` : "", record.area_ha, record.evidence_reference, record.notes]));
    (readiness?.checklist || []).forEach((item) => rows.push(["Readiness", "", item.complete ? "Recorded" : "Needed", item.label, "", "", ""]));
    const content = `\uFEFF${rows.map((row) => row.map(csvCell).join(",")).join("\r\n")}`;
    const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `${(fieldName || "field").replace(/[^a-z0-9_-]+/gi, "-")}-season-summary.csv`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const editRecord = async (event, record, kind) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget).entries());
    const endpoint = kind === "soil_test" ? `/api/soil-tests/${record.id}` : `/api/regenerative-practices/${record.id}`;
    try {
      await api.put(endpoint, data);
      setNotice(tr("recordCorrected", "Record corrected."));
      await load();
    } catch (err) {
      setError(tr("recordUpdateError", "Could not update this record."));
    }
  };

  if (!farmId || !fieldId) {
    return (
      <section className="surface-card-highlight p-5 sm:p-6">
        <span className="section-badge">{tr("fieldPlanning", "Field planning")}</span>
        <h2 className="mt-3 text-xl font-semibold text-text-heading">{tr("chooseFieldTitle", "Choose a farm field to start a plan")}</h2>
        <p className="mt-2 text-sm leading-6 text-text-muted">{tr("chooseFieldDesc", "Select or create a farm and field in the crop workspace. Soil plans and measurement records are saved to that field.")}</p>
        <button type="button" onClick={onOpenFarm} className="theme-button-primary mt-4 px-4 py-3">{tr("openFarm", "Open farm workspace")}</button>
      </section>
    );
  }

  const fieldName = readiness?.field?.name || tr("selectedField", "Selected field");
  const completedTasks = tasks.filter((task) => task.status === "completed").length;
  const checklistDone = readiness?.completed_items || 0;
  const editableYears = draftPlan?.plan || [];

  const updatePlanYear = (index, key, value) => {
    setDraftPlan((current) => ({
      ...current,
      plan: current.plan.map((year, yearIndex) => yearIndex === index ? { ...year, [key]: value } : year),
    }));
  };

  return (
    <div className="space-y-6">
      <section id="soil-plan-workspace" className="surface-card p-5 sm:p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <span className="section-badge">{tr("regenerativePlan", "Regenerative soil plan")}</span>
            <h2 className="mt-2 text-xl font-semibold text-text-heading">{tr("calendar", "Five-year field calendar")}</h2>
            <p className="mt-1 text-sm text-text-muted">{fieldName} | {tr("tasksCompleted", "{{done}} of {{total}} tasks completed").replace("{{done}}", completedTasks).replace("{{total}}", tasks.length)}</p>
            <div className="mt-3 h-1.5 w-full max-w-sm overflow-hidden rounded-full bg-primary-100" role="progressbar" aria-label={tr("tasksCompleted", "Completed plan tasks")} aria-valuemin="0" aria-valuemax={tasks.length} aria-valuenow={completedTasks}>
              <div className="h-full rounded-full bg-primary-700 transition-[width] duration-300" style={{ width: `${tasks.length ? (completedTasks / tasks.length) * 100 : 0}%` }} />
            </div>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
            <label className="text-sm text-text-muted">{tr("planStarts", "Plan starts")}
              <input className="field-shell mt-1" type="date" value={planStartDate} onChange={(event) => setPlanStartDate(event.target.value)} />
            </label>
            <button type="button" disabled={!draftPlan || busy} onClick={savePlan} className="theme-button-primary px-4 py-3 disabled:opacity-50">
              {busy ? tr("saving", "Saving...") : savedPlan ? tr("updatePlan", "Update field plan") : tr("savePlan", "Save plan to field")}
            </button>
          </div>
        </div>
        <p className="mt-4 border-t border-surface-border pt-4 text-xs leading-5 text-text-subtle">{tr("taskDateInfo", "Task dates are planning reminders anchored to this start date (before sowing, 30 days after, and 180 days after). Adjust them to the actual crop calendar and local conditions.")}</p>
        {notice ? <p role="status" className="mt-3 text-sm text-accent-800">{notice}</p> : null}
        {!draftPlan ? <p className="mt-3 text-sm text-text-muted">{tr("runAdvisory", "Run a crop advisory to prepare a soil plan for this field. Any saved plan and progress remain available here.")}</p> : null}
        {savedPlan ? <p className="mt-3 text-xs text-text-subtle">{tr("lastSaved", "Plan last saved {{date}}. Tasks already marked complete keep their status when the plan is updated.").replace("{{date}}", new Date(savedPlan.updated_at).toLocaleString(language === "hi" ? "hi-IN" : language === "mr" ? "mr-IN" : undefined))}</p> : null}
        {editableYears.length ? <div className="mt-5 border-t border-surface-border pt-4">
          <h3 className="font-semibold text-text-heading">{tr("adaptSuggestions", "Adapt each year's suggestions")}</h3>
          <p className="mt-1 text-sm leading-6 text-text-muted">{tr("adaptHelp", "Edit rotations and support notes for this field. Choose cover crops and inoculants with local agronomy advice; confirm soil needs with current tests.")}</p>
          <div className="mt-3 divide-y divide-surface-border">
            {editableYears.map((year, index) => <details key={year.year || index} className="py-3">
              <summary className="cursor-pointer font-medium text-text-heading">{tr("year", "Year {{year}}").replace("{{year}}", year.year || index + 1)}</summary>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                {[["rotation", tr("cropRotation", "Crop rotation")], ["cover_crop", tr("coverResidue", "Cover crop and residue")], ["microbial_support", tr("microbialNotes", "Microbial inoculant notes")]].map(([key, label]) => <label key={key} className="text-sm text-text-muted">{label}<textarea className="field-shell mt-1 min-h-20" maxLength="1200" value={soilDataText(language, year[key] || "")} onChange={(event) => updatePlanYear(index, key, event.target.value)} /></label>)}
              </div>
            </details>)}
          </div>
        </div> : null}
        {tasks.length ? (
          <div className="mt-5 space-y-6">
            {Object.entries(tasksByYear).map(([year, yearTasks]) => (
              <section key={year} className="border-t border-surface-border pt-4">
                <h3 className="text-base font-semibold text-text-heading">{tr("year", "Year {{year}}").replace("{{year}}", year)}</h3>
                <div className="mt-3 divide-y divide-surface-border">
                  {yearTasks.map((task) => (
                    <article key={task.id} className="grid gap-3 py-4 md:grid-cols-[minmax(0,1fr),auto] md:items-start">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                          <h4 className="font-semibold text-text-heading">{soilDataText(language, task.title)}</h4>
                          <span className="text-xs text-text-subtle">{soilDataText(language, task.season)} | {formatDate(task.due_date, language)}</span>
                        </div>
                        <p className="mt-1 text-sm leading-6 text-text-muted">{soilDataText(language, task.description)}</p>
                        <input className="field-shell mt-2 max-w-xl" aria-label={`${tr("notes", "Notes")}: ${soilDataText(language, task.title)}`} value={task.notes || ""} placeholder={tr("fieldNotes", "Field notes or actual completion date")} onChange={(event) => setTasks((current) => current.map((item) => item.id === task.id ? { ...item, notes: event.target.value } : item))} onBlur={(event) => changeTask(task, task.status, event.target.value)} />
                      </div>
                      <select className="theme-select w-full md:w-36" aria-label={`${tr("taskStatus", "Status")}: ${soilDataText(language, task.title)}`} value={task.status} onChange={(event) => changeTask(task, event.target.value)}>
                        <option value="planned">{tr("planned", "Planned")}</option>
                        <option value="completed">{tr("completed", "Completed")}</option>
                        <option value="skipped">{tr("skipped", "Skipped")}</option>
                      </select>
                    </article>
                  ))}
                </div>
              </section>
            ))}
          </div>
        ) : <p className="mt-5 border-t border-surface-border pt-4 text-sm text-text-muted">{tr("saveTasksHint", "Save the current advisory plan to create dated seasonal tasks for this field.")}</p>}
      </section>

      <section className="surface-card p-5 sm:p-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <span className="section-badge">{tr("carbonDocs", "Carbon documentation")}</span>
            <h2 className="mt-2 text-xl font-semibold text-text-heading">{tr("readinessRecords", "Readiness records")}</h2>
            <p className="mt-1 text-sm text-text-muted">{tr("carbonDisclaimer", "Documentation checklist only; no carbon credits or sequestration estimates are calculated.")}</p>
          </div>
          <div className="flex items-center gap-3">
            {readiness ? <p className="text-sm font-semibold text-accent-700">{tr("recordsReady", "{{done}} of {{total}} records ready").replace("{{done}}", checklistDone).replace("{{total}}", readiness.total_items)}</p> : null}
            <button type="button" onClick={exportFieldLog} className="theme-button-secondary px-3 py-2 text-sm" title={tr("downloadCsv", "Download field plan and evidence log as CSV")}>{tr("exportCsv", "Export CSV")}</button>
          </div>
        </div>

        {readiness ? (
          <>
            <ul className="mt-4 grid gap-x-8 sm:grid-cols-2">
              {readiness.checklist.map((item) => (
                <li key={item.key} className="flex items-start justify-between gap-3 border-t border-surface-border py-3 text-sm">
                  <span className="text-text-heading">{soilDataText(language, item.label)}</span>
                  <span className={item.complete ? "font-semibold text-success-700" : "text-text-subtle"}>{item.complete ? tr("recorded", "Recorded") : tr("needed", "Needed")}</span>
                </li>
              ))}
            </ul>
            {!readiness.field.area_ha ? <p className="mt-2 text-sm text-warning-700">{tr("addArea", "Add this field's area in the farm workspace to complete the area record.")}</p> : <p className="mt-2 text-sm text-text-muted">{tr("recordedArea", "Recorded area: {{area}} ha").replace("{{area}}", readiness.field.area_ha)}</p>}
            <p className="mt-4 border-l-2 border-warning-100 pl-3 text-sm leading-6 text-text-muted">{soilDataText(language, readiness.carbon_credits.message)}</p>
          </>
        ) : null}

        <details className="mt-5 border-t border-surface-border pt-4">
          <summary className="cursor-pointer font-semibold text-text-heading">{tr("soilLabRecord", "Record a soil laboratory result")}</summary>
          <form className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3" onSubmit={addSample}>
            <label className="text-sm text-text-muted">{tr("sampleDate", "Sample date")}<input className="field-shell mt-1" type="date" required value={sample.sample_date} onChange={(event) => setSample({ ...sample, sample_date: event.target.value })} /></label>
            <label className="text-sm text-text-muted">{tr("organicCarbon", "Soil organic carbon (%)")}<input className="field-shell mt-1" type="number" min="0" max="100" step="0.01" required value={sample.organic_carbon_pct} onChange={(event) => setSample({ ...sample, organic_carbon_pct: event.target.value })} /></label>
            <label className="text-sm text-text-muted">{tr("optionalPh", "Soil pH (optional)")}<input className="field-shell mt-1" type="number" min="0" max="14" step="0.1" value={sample.ph} onChange={(event) => setSample({ ...sample, ph: event.target.value })} /></label>
            {["nitrogen", "phosphorus", "potassium"].map((key) => <label key={key} className="min-w-0 text-sm text-text-muted">{tr(({ nitrogen: "nitrogenLabel", phosphorus: "phosphorusLabel", potassium: "potassiumLabel" })[key], key)} {tr("optional", "(optional)")}<input className="field-shell mt-1 min-w-0" type="number" min="0" step="0.01" value={sample[key]} onChange={(event) => setSample({ ...sample, [key]: event.target.value })} /></label>)}
            <label className="text-sm text-text-muted">{tr("npkUnits", "NPK units (if entered)")}<select className="theme-select mt-1 w-full" value={sample.nutrient_units} onChange={(event) => setSample({ ...sample, nutrient_units: event.target.value })}><option value="">{tr("chooseUnits", "Choose units")}</option><option value="mg/kg">mg/kg</option><option value="kg/ha">kg/ha</option><option value="ppm">ppm</option><option value="%">%</option></select></label>
            <label className="text-sm text-text-muted">{tr("laboratory", "Laboratory")}<input className="field-shell mt-1" maxLength="200" value={sample.lab_name} onChange={(event) => setSample({ ...sample, lab_name: event.target.value })} /></label>
            <label className="text-sm text-text-muted sm:col-span-2">{tr("labReference", "Lab report reference (file name or URL)")}<input className="field-shell mt-1" maxLength="500" value={sample.evidence_reference} onChange={(event) => setSample({ ...sample, evidence_reference: event.target.value })} /></label>
            <label className="text-sm text-text-muted sm:col-span-2 lg:col-span-3">{tr("notes", "Notes")}<textarea className="field-shell mt-1 min-h-20" maxLength="1500" value={sample.notes} onChange={(event) => setSample({ ...sample, notes: event.target.value })} /></label>
            <button className="theme-button-primary w-full px-4 py-3 sm:w-fit" disabled={busy} type="submit">{tr("saveSoilTest", "Save soil test")}</button>
          </form>
        </details>

        <details className="mt-4 border-t border-surface-border pt-4">
          <summary className="cursor-pointer font-semibold text-text-heading">{tr("logPractice", "Log a regenerative practice")}</summary>
          <form className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3" onSubmit={addPractice}>
            <label className="text-sm text-text-muted">{tr("practice", "Practice")}<select className="theme-select mt-1 w-full" value={practice.practice_type} onChange={(event) => setPractice({ ...practice, practice_type: event.target.value })}>{PRACTICE_OPTIONS.map(([value, label]) => <option key={value} value={value}>{practiceLabel({ cover_crop: "practiceCover", crop_rotation: "practiceRotation", reduced_tillage: "reducedTillage", residue_retention: "residueRetention", compost: "compost", agroforestry: "agroforestry", nutrient_management: "nutrientManagement", other: "other" }[value], label)}</option>)}</select></label>
            <label className="text-sm text-text-muted">{tr("startDate", "Start date")}<input className="field-shell mt-1" type="date" required value={practice.start_date} onChange={(event) => setPractice({ ...practice, start_date: event.target.value })} /></label>
            <label className="text-sm text-text-muted">{tr("endDate", "End date (optional)")}<input className="field-shell mt-1" type="date" value={practice.end_date} onChange={(event) => setPractice({ ...practice, end_date: event.target.value })} /></label>
            <label className="text-sm text-text-muted">{tr("areaCovered", "Area covered (ha, optional)")}<input className="field-shell mt-1" type="number" min="0.01" step="0.01" value={practice.area_ha} onChange={(event) => setPractice({ ...practice, area_ha: event.target.value })} /></label>
            <label className="text-sm text-text-muted sm:col-span-2">{tr("evidenceReference", "Evidence reference (photo, invoice, or field log)")}<input className="field-shell mt-1" maxLength="500" value={practice.evidence_reference} onChange={(event) => setPractice({ ...practice, evidence_reference: event.target.value })} /></label>
            <label className="text-sm text-text-muted sm:col-span-2 lg:col-span-3">{tr("notes", "Notes")}<textarea className="field-shell mt-1 min-h-20" maxLength="1500" value={practice.notes} onChange={(event) => setPractice({ ...practice, notes: event.target.value })} /></label>
            <button className="theme-button-primary w-full px-4 py-3 sm:w-fit" disabled={busy} type="submit">{tr("savePractice", "Save practice")}</button>
          </form>
        </details>

        {readiness?.soil_tests?.length ? (
          <div className="mt-5 border-t border-surface-border pt-4">
            <h3 className="font-semibold text-text-heading">{tr("soilHistory", "Soil test history")}</h3>
            <div className="mt-2 divide-y divide-surface-border">
              {readiness.soil_tests.map((record) => (
                <details key={record.id} className="py-2">
                  <summary className="cursor-pointer text-sm text-text-muted">{record.sample_date}: {tr("organicCarbonShort", "organic carbon")} {record.organic_carbon_pct}%{record.ph !== null ? ` | pH ${record.ph}` : ""}{record.lab_name ? ` | ${record.lab_name}` : ""} | {tr("edit", "Edit")}</summary>
                  <form className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3" onSubmit={(event) => editRecord(event, record, "soil_test")}>
                    {[["sample_date", "sampleDate", "Sample date", "date"], ["organic_carbon_pct", "organicCarbon", "Organic carbon (%)", "number"], ["ph", "optionalPh", "pH", "number"], ["nitrogen", "nitrogenLabel", "Nitrogen", "number"], ["phosphorus", "phosphorusLabel", "Phosphorus", "number"], ["potassium", "potassiumLabel", "Potassium", "number"], ["nutrient_units", "npkUnits", "NPK units", "text"], ["lab_name", "laboratory", "Laboratory", "text"], ["evidence_reference", "evidence", "Evidence reference", "text"], ["notes", "notes", "Notes", "text"]].map(([key, translationKey, fallback, type]) => <label key={key} className="text-xs text-text-muted">{tr(translationKey, fallback)}<input className="field-shell mt-1" name={key} type={type} step={type === "number" ? "any" : undefined} defaultValue={record[key] ?? ""} /></label>)}
                    <button className="theme-button-primary px-3 py-2 text-sm" type="submit">{tr("saveCorrection", "Save correction")}</button>
                  </form>
                </details>
              ))}
            </div>
          </div>
        ) : null}
        {readiness?.practices?.length ? (
          <div className="mt-5 border-t border-surface-border pt-4">
            <h3 className="font-semibold text-text-heading">{tr("practiceHistory", "Practice history")}</h3>
            <div className="mt-2 divide-y divide-surface-border">
              {readiness.practices.map((record) => (
                <details key={record.id} className="py-2">
                  <summary className="cursor-pointer text-sm text-text-muted">{soilDataText(language, PRACTICE_OPTIONS.find(([value]) => value === record.practice_type)?.[1] || record.practice_type)} | {record.start_date}{record.end_date ? ` ${tr("to", "to")} ${record.end_date}` : ""}{record.area_ha ? ` | ${record.area_ha} ha` : ""} | {tr("edit", "Edit")}</summary>
                  <form className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3" onSubmit={(event) => editRecord(event, record, "practice")}>
                    <label className="text-xs text-text-muted">{tr("practice", "Practice")}<select className="theme-select mt-1 w-full" name="practice_type" defaultValue={record.practice_type}>{PRACTICE_OPTIONS.map(([value, label]) => <option key={value} value={value}>{soilDataText(language, label)}</option>)}</select></label>
                    {[["start_date", "startDate", "Start date", "date"], ["end_date", "endDate", "End date", "date"], ["area_ha", "area", "Area (ha)", "number"], ["evidence_reference", "evidence", "Evidence reference", "text"], ["notes", "notes", "Notes", "text"]].map(([key, translationKey, fallback, type]) => <label key={key} className="text-xs text-text-muted">{tr(translationKey, fallback)}<input className="field-shell mt-1" name={key} type={type} step={type === "number" ? "any" : undefined} defaultValue={record[key] ?? ""} /></label>)}
                    <button className="theme-button-primary px-3 py-2 text-sm" type="submit">{tr("saveCorrection", "Save correction")}</button>
                  </form>
                </details>
              ))}
            </div>
          </div>
        ) : null}
      </section>

      {error ? <p role="alert" className="rounded-md border border-danger-200 bg-danger-50 px-4 py-3 text-sm text-danger-700">{error}</p> : null}
      {notice ? <p role="status" className="rounded-md border border-success-200 bg-success-50 px-4 py-3 text-sm text-success-700">{notice}</p> : null}
    </div>
  );
}

export default SoilPlanningWorkspace;
