import React, { useState } from "react";
import { Bell, BellRing, Bug, CalendarDays, Check, Droplets, ExternalLink, Sprout } from "lucide-react";
import { useLanguage } from "../i18n/LanguageContext";
import { soilDataText } from "../i18n/soilTranslations";

function parseLocalDate(value) {
  if (!value) return null;
  const date = new Date(`${String(value).slice(0, 10)}T00:00:00`);
  return Number.isNaN(date.getTime()) ? null : date;
}

function localDateKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function FieldTimeline({ irrigation, pestForecast, harvest, weatherForecast, soilTasks = [], onCompleteTask, onOpenItem }) {
  const { language, t, tv } = useLanguage();
  const locale = language === "hi" ? "hi-IN" : language === "mr" ? "mr-IN" : "en-IN";
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const formatDate = (date) => date.toLocaleDateString(locale, { day: "numeric", month: "short", year: "numeric" });
  const [reminders, setReminders] = useState(() => {
    try {
      const stored = JSON.parse(localStorage.getItem("ankurai_field_reminders") || "{}");
      return stored && typeof stored === "object" && !Array.isArray(stored) ? stored : {};
    } catch {
      return {};
    }
  });
  const [completingTask, setCompletingTask] = useState(null);
  const [actionError, setActionError] = useState("");
  const events = [];

  if (irrigation?.level) {
    events.push({
      date: today,
      title: t("farmer.timelineIrrigation"),
      detail: t("farmer.timelineIrrigationDetail", undefined, { level: tv("statuses", irrigation.level) }),
      Icon: Droplets,
      tone: "text-sky-600 bg-sky-50 border-sky-100",
      reminderId: `irrigation-${localDateKey(today)}`,
      action: "crop",
    });
  }

  if (pestForecast) {
    const days = Math.max(1, Number(pestForecast.forecast_window_days) || 7);
    const due = new Date(today);
    due.setDate(due.getDate() + days);
    const highest = pestForecast.highest_risk || {};
    events.push({
      date: due,
      title: t("farmer.timelineScout"),
      detail: t("farmer.timelineScoutDetail", undefined, {
        pest: soilDataText(language, highest.pest) || t("farmer.fieldScout"),
        risk: tv("statuses", highest.risk_level || "moderate"),
      }),
      Icon: Bug,
      tone: "text-warning-700 bg-warning-50 border-warning-100",
      reminderId: `scout-${localDateKey(due)}`,
      action: "pest",
    });
  }

  const forecastDays = weatherForecast?.days || [];
  const rainDays = forecastDays.filter((day) => (Number(day.precipitation_mm) || 0) >= 5 || (Number(day.precipitation_probability) || 0) >= 60);
  const hotDays = forecastDays.filter((day) => (Number(day.temperature_max_c) || 0) >= 35);
  if (rainDays.length) {
    const day = rainDays[0];
    const date = parseLocalDate(day.date);
    if (date) events.push({
      date,
      title: t("farmer.timelineRain"),
      detail: t("farmer.timelineRainDetail", undefined, { amount: Number(day.precipitation_mm || 0).toFixed(1), chance: Number(day.precipitation_probability || 0) }),
      Icon: Droplets,
      tone: "text-sky-600 bg-sky-50 border-sky-100",
      reminderId: `weather-rain-${day.date}`,
      action: "crop",
    });
  }
  if (hotDays.length) {
    const day = hotDays[0];
    const date = parseLocalDate(day.date);
    if (date) events.push({
      date,
      title: t("farmer.timelineHeat"),
      detail: t("farmer.timelineHeatDetail", undefined, { temperature: Number(day.temperature_max_c).toFixed(1) }),
      Icon: CalendarDays,
      tone: "text-warning-700 bg-warning-50 border-warning-100",
      reminderId: `weather-heat-${day.date}`,
      action: "crop",
    });
  }

  const todayKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  const plannedTasks = soilTasks
    .filter((task) => task.status === "planned" && parseLocalDate(task.due_date))
    .sort((a, b) => a.due_date.localeCompare(b.due_date));
  const nextSoilTask = plannedTasks.find((task) => task.due_date >= todayKey) || plannedTasks[plannedTasks.length - 1];
  if (nextSoilTask) {
    events.push({
      date: parseLocalDate(nextSoilTask.due_date),
      title: soilDataText(language, nextSoilTask.title),
      detail: soilDataText(language, nextSoilTask.description),
      Icon: Sprout,
      tone: "text-success-700 bg-success-50 border-success-100",
      reminderId: `soil-${nextSoilTask.id}`,
      task: nextSoilTask,
      action: "soil",
    });
  }

  const harvestDate = parseLocalDate(harvest?.start);
  if (harvestDate && harvestDate >= today) {
    events.push({
      date: harvestDate,
      title: t("farmer.timelineHarvest"),
      detail: t("farmer.timelineHarvestDetail", undefined, {
        end: formatDate(parseLocalDate(harvest.end) || harvestDate),
      }),
      Icon: CalendarDays,
      tone: "text-accent-800 bg-accent-50 border-accent-200",
      reminderId: `harvest-${localDateKey(harvestDate)}`,
      action: "crop",
    });
  }

  if (!events.length) return null;
  events.sort((a, b) => a.date - b.date);
  const toggleReminder = (event) => {
    const next = { ...reminders };
    if (next[event.reminderId]) delete next[event.reminderId];
    else next[event.reminderId] = { title: event.title, due_date: localDateKey(event.date) };
    try {
      localStorage.setItem("ankurai_field_reminders", JSON.stringify(next));
      setReminders(next);
      setActionError("");
      window.dispatchEvent(new Event("ankurai-reminders-change"));
    } catch {
      setActionError(t("farmer.reminderSaveFailed"));
    }
  };

  const completeTask = async (task) => {
    setCompletingTask(task.id);
    setActionError("");
    try {
      await onCompleteTask(task);
    } catch {
      setActionError(t("farmer.timelineTaskFailed"));
    } finally {
      setCompletingTask(null);
    }
  };

  return (
    <section className="surface-card p-5 sm:p-6" aria-labelledby="field-timeline-title">
      <div className="flex flex-wrap items-end justify-between gap-2 border-b border-surface-border pb-3">
        <div>
          <span className="section-badge">{t("farmer.fieldStatus")}</span>
          <h2 id="field-timeline-title" className="mt-2 text-xl font-semibold text-text-heading">{t("farmer.fieldTimeline")}</h2>
          <p className="mt-1 text-xs text-text-subtle">{t("farmer.reminderNote")}</p>
        </div>
        <p className="text-xs tabular-nums text-text-subtle">{formatDate(today)}</p>
      </div>
      {actionError ? <p role="alert" className="mt-3 text-sm text-danger-700">{actionError}</p> : null}
      <ol className="mt-4 grid gap-x-5 gap-y-4 sm:grid-cols-2 xl:grid-cols-4">
        {events.map((event) => (
          <li key={`${event.title}-${event.date.toISOString()}`} className="relative min-w-0 border-l-2 border-surface-border pl-3">
            <span className={`absolute -left-[0.7rem] top-0 inline-flex h-5 w-5 items-center justify-center rounded-full border ${event.tone}`}>
              <event.Icon size={12} aria-hidden="true" />
            </span>
            <time className="text-xs font-medium tabular-nums text-text-subtle" dateTime={`${event.date.getFullYear()}-${String(event.date.getMonth() + 1).padStart(2, "0")}-${String(event.date.getDate()).padStart(2, "0")}`}>{formatDate(event.date)}</time>
            <h3 className="mt-1 break-words text-sm font-semibold text-text-heading">{event.title}</h3>
            <p className="mt-1 break-words text-xs leading-5 text-text-muted">{event.detail}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <button type="button" className="theme-button-ghost inline-flex min-h-10 items-center gap-1.5 px-2 text-xs" onClick={() => onOpenItem?.(event.action)}>
                <ExternalLink size={14} aria-hidden="true" />{event.action === "pest" ? t("farmer.timelineOpenPest") : event.action === "soil" ? t("farmer.timelineOpenSoil") : t("farmer.timelineOpenCrop")}
              </button>
              <button type="button" className="theme-button-ghost inline-flex min-h-10 items-center gap-1.5 px-2 text-xs" aria-pressed={Boolean(reminders[event.reminderId])} onClick={() => toggleReminder(event)}>
                {reminders[event.reminderId] ? <BellRing size={14} aria-hidden="true" /> : <Bell size={14} aria-hidden="true" />}
                {reminders[event.reminderId] ? t("farmer.reminderSet") : t("farmer.remindMe")}
              </button>
              {event.task && event.task.status === "planned" ? (
                <button type="button" className="theme-button-secondary inline-flex min-h-10 items-center gap-1.5 px-2 text-xs" disabled={completingTask === event.task.id} onClick={() => completeTask(event.task)}>
                  <Check size={14} aria-hidden="true" />{completingTask === event.task.id ? t("farmer.savingTask") : t("farmer.markComplete")}
                </button>
              ) : null}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

export default FieldTimeline;
