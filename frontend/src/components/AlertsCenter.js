import React, { useEffect, useMemo, useState } from "react";
import { Bell, BellRing, CalendarDays, Check, CircleAlert, ExternalLink, History, RefreshCw, SlidersHorizontal, X } from "lucide-react";
import api from "../api/client";
import LoadingSpinner from "./LoadingSpinner";
import { useLanguage } from "../i18n/LanguageContext";
import { soilDataText } from "../i18n/soilTranslations";

const LOCAL_REMINDER_KEY = "ankurai_field_reminders";
const DEFAULT_PREFERENCES = { types: { field: true, action: true, follow_up: true }, advanceDays: 1, browserNotifications: false };

function readLocalReminders() {
  try {
    const parsed = JSON.parse(localStorage.getItem(LOCAL_REMINDER_KEY) || "{}");
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

function readStoredJson(key, fallback) {
  try {
    const value = JSON.parse(localStorage.getItem(key) || "null");
    return value && typeof value === "object" ? value : fallback;
  } catch {
    return fallback;
  }
}

function AlertsCenter({ farmId, userId, onOpenModule, onDueCountChange }) {
  const { language, t, tv } = useLanguage();
  const [localReminders, setLocalReminders] = useState(readLocalReminders);
  const [farmReminders, setFarmReminders] = useState([]);
  const [farms, setFarms] = useState([]);
  const storageSuffix = userId || "current";
  const preferencesKey = `ankurai_alert_preferences:${storageSuffix}`;
  const historyKey = `ankurai_alert_history:${storageSuffix}`;
  const notificationKey = `ankurai_notified_alerts:${storageSuffix}`;
  const [preferences, setPreferences] = useState(() => ({ ...DEFAULT_PREFERENCES, ...readStoredJson(preferencesKey, {}), types: { ...DEFAULT_PREFERENCES.types, ...(readStoredJson(preferencesKey, {}).types || {}) } }));
  const [history, setHistory] = useState(() => {
    const stored = readStoredJson(historyKey, []);
    return Array.isArray(stored) ? stored : [];
  });
  const [view, setView] = useState("inbox");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");
  const [farmFilter, setFarmFilter] = useState("all");
  const [fieldFilter, setFieldFilter] = useState("all");
  const [cropFilter, setCropFilter] = useState("all");
  const [notificationMessage, setNotificationMessage] = useState("");
  const [workingId, setWorkingId] = useState("");
  const locale = language === "hi" ? "hi-IN" : language === "mr" ? "mr-IN" : "en-IN";

  const loadFarmReminders = async () => {
    setLoading(true);
    setError("");
    setFarmReminders([]);
    try {
      const response = await api.get("/api/farms");
      const nextFarms = response.data.farms || [];
      setFarms(nextFarms);
      const results = await Promise.all(nextFarms.map(async (farm) => {
        try {
          const remindersResponse = await api.get(`/api/farms/${farm.id}/reminders`);
          return (remindersResponse.data.reminders || []).map((item) => ({ ...item, farm_id: farm.id, farm_name: farm.name, origin: "farm" }));
        } catch {
          return [];
        }
      }));
      setFarmReminders(results.flat());
    } catch {
      setError(t("alerts.loadFailed"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFarmReminders();
  }, [farmId, userId]);

  useEffect(() => {
    const sync = () => setLocalReminders(readLocalReminders());
    window.addEventListener("ankurai-reminders-change", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("ankurai-reminders-change", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  const items = useMemo(() => {
    const deviceItems = Object.entries(localReminders).map(([id, reminder]) => ({
      id,
      origin: "device",
      due: reminder?.due_date ? `${reminder.due_date}T00:00:00` : "",
      title: reminder?.title || "",
      kind: "saved",
      crop: "",
      field_name: "",
    }));
    return [...deviceItems, ...farmReminders.map((reminder) => ({ ...reminder, origin: "farm" }))]
      .sort((a, b) => (Date.parse(a.due || "") || Infinity) - (Date.parse(b.due || "") || Infinity));
  }, [farmReminders, localReminders]);

  const today = new Date();
  today.setHours(23, 59, 59, 999);
  const withinWeek = new Date(today);
  withinWeek.setDate(withinWeek.getDate() + 7);
  const isDue = (item) => Boolean(item.due_now || (item.due && Date.parse(item.due) <= withinWeek.getTime()));
  const typeOf = (item) => item.origin === "device" ? "field" : item.kind === "action" ? "action" : "follow_up";
  const isEnabled = (item) => preferences.types?.[typeOf(item)] !== false;
  const dueCount = items.filter(isDue).length;
  useEffect(() => {
    onDueCountChange?.(dueCount);
  }, [dueCount, onDueCountChange]);
  const fields = farms.flatMap((farm) => (farm.fields || []).map((field) => ({ ...field, farm_id: farm.id, farm_name: farm.name })));
  const crops = [...new Set([...fields.map((field) => field.crop), ...farmReminders.map((item) => item.crop)].filter(Boolean))].sort();
  const inboxItems = items.filter((item) => {
    if (!isEnabled(item)) return false;
    if (farmFilter !== "all" && String(item.farm_id || "") !== String(farmFilter)) return false;
    if (fieldFilter !== "all" && String(item.field_id || "") !== String(fieldFilter)) return false;
    if (cropFilter !== "all" && String(item.crop || "").toLowerCase() !== cropFilter.toLowerCase()) return false;
    return true;
  });
  const filteredItems = inboxItems.filter((item) => filter === "all" || (filter === "due" ? isDue(item) : !isDue(item)));
  const formatDate = (value) => {
    if (!value) return "-";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "-" : date.toLocaleDateString(locale, { day: "numeric", month: "short", year: "numeric" });
  };
  const removeLocalReminder = (id) => {
    const next = { ...readLocalReminders() };
    delete next[id];
    try {
      localStorage.setItem(LOCAL_REMINDER_KEY, JSON.stringify(next));
      setLocalReminders(next);
      saveHistory({ id, origin: "device", due: localReminders[id]?.due_date, title: titleFor(items.find((item) => item.id === id) || { id, origin: "device", title: localReminders[id]?.title }), result: "dismissed" });
      window.dispatchEvent(new Event("ankurai-reminders-change"));
    } catch {
      setError(t("alerts.removeFailed"));
    }
  };
  const submitOutcome = async (item, outcome) => {
    setWorkingId(String(item.id));
    setError("");
    try {
      if (item.kind === "action") {
        await api.post(`/api/interventions/${item.id}/acknowledge`);
      } else {
        await api.post(`/api/interventions/${item.id}/outcome`, { status: outcome });
      }
      saveHistory({ ...item, title: titleFor(item), result: item.kind === "action" ? "recorded" : outcome });
      await loadFarmReminders();
    } catch (err) {
      setError(t("alerts.actionFailed"));
    } finally {
      setWorkingId("");
    }
  };
  const moduleFor = (id) => id.startsWith("scout-") ? "soil" : id.startsWith("soil-") ? "soil" : "crop";
  const titleFor = (item) => {
    if (item.origin === "device") {
      const titleKeys = [
        ["irrigation-", "farmer.timelineIrrigation"], ["scout-", "farmer.timelineScout"],
        ["weather-rain-", "farmer.timelineRain"], ["weather-heat-", "farmer.timelineHeat"], ["harvest-", "farmer.timelineHarvest"],
      ];
      const key = titleKeys.find(([prefix]) => String(item.id).startsWith(prefix))?.[1];
      return (key ? t(key) : null) || soilDataText(language, item.title) || t("alerts.savedReminder");
    }
    return item.kind === "action" ? t("alerts.actionPrompt") : t("alerts.followUpPrompt");
  };
  const saveHistory = (item) => {
    const next = [{
      id: `${item.origin || "farm"}-${item.id}-${Date.now()}`,
      title: item.title || titleFor(item),
      crop: item.crop || "",
      field_name: item.field_name || item.farm_name || "",
      due: item.due || "",
      result: item.result || "dismissed",
      completed_at: new Date().toISOString(),
    }, ...history].slice(0, 250);
    try {
      localStorage.setItem(historyKey, JSON.stringify(next));
      setHistory(next);
    } catch {
      setError(t("alerts.historySaveFailed"));
    }
  };
  const savePreferences = (next) => {
    try {
      localStorage.setItem(preferencesKey, JSON.stringify(next));
      setPreferences(next);
    } catch {
      setError(t("alerts.preferencesSaveFailed"));
    }
  };
  const enableBrowserNotifications = async (enabled) => {
    if (!enabled) {
      savePreferences({ ...preferences, browserNotifications: false });
      setNotificationMessage(t("alerts.notificationsDisabled"));
      return;
    }
    if (!("Notification" in window)) {
      setNotificationMessage(t("alerts.notificationsUnsupported"));
      return;
    }
    const permission = Notification.permission === "default" ? await Notification.requestPermission() : Notification.permission;
    if (permission !== "granted") {
      setNotificationMessage(t("alerts.notificationsDenied"));
      return;
    }
    savePreferences({ ...preferences, browserNotifications: true });
    setNotificationMessage(t("alerts.notificationsEnabled"));
  };

  useEffect(() => {
    if (!preferences.browserNotifications || !("Notification" in window) || Notification.permission !== "granted") return undefined;
    const notifyDue = () => {
      const threshold = Date.now() + Number(preferences.advanceDays || 0) * 86400000;
      const seen = readStoredJson(notificationKey, {});
      const updated = { ...seen };
      let changed = false;
      items.filter((item) => isEnabled(item) && item.due && Date.parse(item.due) <= threshold).forEach((item) => {
        const key = `${item.origin}:${item.id}:${String(item.due).slice(0, 10)}`;
        if (seen[key]) return;
        const options = { body: titleFor(item), tag: `ankurai-${key}`, icon: "/ankurai-192.png", data: { url: "/dashboard" } };
        if (navigator.serviceWorker?.getRegistration) {
          navigator.serviceWorker.getRegistration().then((registration) => registration
            ? registration.showNotification(t("alerts.title"), options)
            : new Notification(t("alerts.title"), options)).catch(() => {});
        } else {
          new Notification(t("alerts.title"), options);
        }
        updated[key] = new Date().toISOString();
        changed = true;
      });
      if (changed) {
        try { localStorage.setItem(notificationKey, JSON.stringify(updated)); } catch { /* Notification deduplication is best-effort. */ }
      }
    };
    notifyDue();
    const timer = window.setInterval(notifyDue, 60000);
    return () => window.clearInterval(timer);
  }, [items, preferences, notificationKey, language]);

  return (
    <section className="surface-card min-w-0 p-4 sm:p-6" aria-labelledby="alerts-center-title">
      <div className="flex flex-col gap-4 border-b border-surface-border pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <span className="section-badge">{t("alerts.eyebrow")}</span>
          <h2 id="alerts-center-title" className="mt-2 text-xl font-semibold text-text-heading sm:text-2xl">{t("alerts.title")}</h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-text-muted">{t("alerts.subtitle")}</p>
        </div>
        <button type="button" onClick={loadFarmReminders} disabled={loading} className="theme-button-secondary inline-flex min-h-11 items-center justify-center gap-2 px-3 py-2 disabled:opacity-60" aria-label={t("alerts.refresh")}>
          <RefreshCw size={16} aria-hidden="true" />{t("alerts.refresh")}
        </button>
      </div>

      <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label={t("alerts.views")}>
        {[["inbox", Bell, t("alerts.inbox")], ["history", History, t("alerts.history")]].map(([value, Icon, label]) => (
          <button key={value} type="button" aria-pressed={view === value} onClick={() => setView(value)} className={`inline-flex min-h-11 items-center gap-2 rounded-md border px-3 py-2 text-sm font-semibold ${view === value ? "border-primary-700 bg-primary-700 text-white" : "border-surface-border bg-white text-text-heading hover:bg-surface-muted"}`}>
            <Icon size={16} aria-hidden="true" />{label}<span className="tabular-nums opacity-80">{value === "inbox" ? inboxItems.length : history.length}</span>
          </button>
        ))}
      </div>

      <details className="mt-4 border-y border-surface-border py-3">
        <summary className="flex min-h-11 cursor-pointer items-center gap-2 text-sm font-semibold text-text-heading"><SlidersHorizontal size={16} aria-hidden="true" />{t("alerts.preferences")}</summary>
        <div className="mt-3 grid gap-4 lg:grid-cols-[1fr,1fr]">
          <fieldset className="min-w-0">
            <legend className="text-xs font-semibold text-text-muted">{t("alerts.typesHeading")}</legend>
            <div className="mt-2 grid gap-2 sm:grid-cols-3">
              {[["field", t("alerts.typeField")], ["action", t("alerts.typeAction")], ["follow_up", t("alerts.typeFollowUp")]].map(([key, label]) => (
                <label key={key} className="flex min-h-11 items-center gap-2 border-l-2 border-surface-border pl-3 text-sm text-text-heading">
                  <input type="checkbox" checked={preferences.types?.[key] !== false} onChange={(event) => savePreferences({ ...preferences, types: { ...preferences.types, [key]: event.target.checked } })} />{label}
                </label>
              ))}
            </div>
          </fieldset>
          <label className="max-w-sm text-xs font-semibold text-text-muted">{t("alerts.advanceLabel")}
            <select className="theme-select mt-1 w-full" value={preferences.advanceDays} onChange={(event) => savePreferences({ ...preferences, advanceDays: Number(event.target.value) })}>
              {[0, 1, 3, 7].map((days) => <option key={days} value={days}>{t(`alerts.advance.${days}`)}</option>)}
            </select>
          </label>
          <div className="lg:col-span-2">
            <label className="flex min-h-11 items-start gap-2 text-sm text-text-heading">
              <input className="mt-1" type="checkbox" checked={Boolean(preferences.browserNotifications)} onChange={(event) => enableBrowserNotifications(event.target.checked)} />
              <span><strong className="font-semibold">{t("alerts.browserNotifications")}</strong><span className="mt-0.5 block text-xs leading-5 text-text-muted">{t("alerts.browserNotificationsNote")}</span></span>
            </label>
            {notificationMessage ? <p className="mt-2 text-xs text-text-muted" role="status" aria-live="polite">{notificationMessage}</p> : null}
          </div>
        </div>
      </details>

      {view === "inbox" ? (
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label={t("alerts.filterLabel")}>
          <label className="text-xs font-semibold text-text-muted">{t("alerts.filterFarm")}<select className="theme-select mt-1 w-full" value={farmFilter} onChange={(event) => { setFarmFilter(event.target.value); setFieldFilter("all"); }}>
            <option value="all">{t("alerts.filterAll")}</option>{farms.map((farm) => <option key={farm.id} value={farm.id}>{farm.name}</option>)}
          </select></label>
          <label className="text-xs font-semibold text-text-muted">{t("alerts.filterField")}<select className="theme-select mt-1 w-full" value={fieldFilter} onChange={(event) => setFieldFilter(event.target.value)}>
            <option value="all">{t("alerts.filterAll")}</option>{fields.filter((field) => farmFilter === "all" || String(field.farm_id) === String(farmFilter)).map((field) => <option key={field.id} value={field.id}>{field.farm_name} · {field.name}</option>)}
          </select></label>
          <label className="text-xs font-semibold text-text-muted">{t("alerts.filterCrop")}<select className="theme-select mt-1 w-full" value={cropFilter} onChange={(event) => setCropFilter(event.target.value)}>
            <option value="all">{t("alerts.filterAll")}</option>{crops.map((cropName) => <option key={cropName} value={cropName}>{tv("crops", cropName)}</option>)}
          </select></label>
          <label className="text-xs font-semibold text-text-muted">{t("alerts.filterUrgency")}<select className="theme-select mt-1 w-full" value={filter} onChange={(event) => setFilter(event.target.value)}>
            <option value="all">{t("alerts.filterAll")}</option><option value="due">{t("alerts.filterDue")}</option><option value="upcoming">{t("alerts.filterUpcoming")}</option>
          </select></label>
        </div>
      ) : null}

      {loading ? <div className="mt-4"><LoadingSpinner label={t("alerts.loading")} /></div> : null}
      {error ? <p className="mt-4 rounded-md border border-danger-100 bg-danger-50 px-3 py-2 text-sm text-danger-700" role="alert">{error}</p> : null}
      {!farms.length && !loading ? <p className="mt-4 rounded-md border-l-2 border-warning-700 bg-warning-50 px-4 py-3 text-sm text-text-heading">{t("alerts.noFarm")}</p> : null}

      {view === "history" ? (
        history.length ? (
          <ul className="mt-4 divide-y divide-surface-border" aria-label={t("alerts.history")}>
            {history.map((entry) => (
              <li key={entry.id} className="grid gap-2 py-4 sm:grid-cols-[minmax(0,1fr),auto] sm:items-start">
                <div className="min-w-0">
                  <p className="break-words text-sm font-semibold text-text-heading">{entry.title || t("alerts.savedReminder")}</p>
                  <p className="mt-1 break-words text-sm text-text-muted">{entry.crop ? `${tv("crops", entry.crop)} · ` : ""}{entry.field_name || t("alerts.deviceOnly")} · {t(`alerts.historyResult.${entry.result}`, t("alerts.historyResult.dismissed"))}</p>
                </div>
                <time className="text-xs tabular-nums text-text-subtle" dateTime={entry.completed_at}>{formatDate(entry.completed_at)}</time>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-5 border-t border-surface-border pt-5 text-sm text-text-muted">{t("alerts.historyEmpty")}</p>
        )
      ) : filteredItems.length ? (
        <ul className="mt-4 divide-y divide-surface-border" aria-live="polite">
          {filteredItems.map((item) => {
            const due = isDue(item);
            const statusLabel = due ? t("alerts.statusDue") : t("alerts.statusUpcoming");
            return (
              <li key={`${item.origin}-${item.id}`} className="grid min-w-0 gap-3 py-4 sm:grid-cols-[minmax(0,1fr),auto] sm:items-start">
                <div className="flex min-w-0 gap-3">
                  <span className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md ${due ? "bg-warning-50 text-warning-700" : "bg-primary-50 text-primary-800"}`} aria-hidden="true">
                    {due ? <CircleAlert size={18} /> : <CalendarDays size={18} />}
                  </span>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="break-words text-sm font-semibold text-text-heading">{titleFor(item)}</h3>
                      <span className={`status-chip ${due ? "status-watch" : "status-info"}`}>{statusLabel}</span>
                    </div>
                    <p className="mt-1 break-words text-sm text-text-muted">
                      {item.crop ? `${tv("crops", item.crop)} · ` : ""}{item.field_name || item.farm_name || ""}
                      {(item.field_name || item.farm_name) ? " · " : ""}{t("alerts.dueOn", undefined, { date: formatDate(item.due) })}
                    </p>
                    {item.origin === "device" ? (
                      <button type="button" className="theme-button-ghost mt-2 inline-flex min-h-10 items-center gap-1 px-2 text-xs" onClick={() => onOpenModule?.(moduleFor(item.id))}>
                        <ExternalLink size={14} aria-hidden="true" />{t("alerts.openRelated")}
                      </button>
                    ) : null}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 sm:justify-end">
                  {item.origin === "device" ? (
                    <button type="button" className="theme-button-ghost inline-flex min-h-10 items-center gap-1 px-2 text-xs" onClick={() => removeLocalReminder(item.id)} aria-label={`${t("alerts.dismiss")}: ${titleFor(item)}`}>
                      <X size={14} aria-hidden="true" />{t("alerts.dismiss")}
                    </button>
                  ) : item.kind === "action" ? (
                    <button type="button" className="theme-button-primary inline-flex min-h-10 items-center gap-1 px-3 text-xs" disabled={workingId === String(item.id)} onClick={() => submitOutcome(item)}>
                      <Check size={14} aria-hidden="true" />{t("farmIntelligence.recordAction", "Record action")}
                    </button>
                  ) : ["improved", "no_change", "worsened", "unknown"].map((status) => (
                    <button key={status} type="button" className="theme-button-secondary min-h-10 px-2 text-xs" disabled={workingId === String(item.id)} onClick={() => submitOutcome(item, status)}>
                      {t(`farmIntelligence.${status}`, status.replace("_", " "))}
                    </button>
                  ))}
                </div>
              </li>
            );
          })}
        </ul>
      ) : !loading ? (
        <div className="mt-5 border-t border-surface-border pt-5 text-center">
          <Bell size={22} className="mx-auto text-primary-700" aria-hidden="true" />
          <p className="mt-2 text-sm font-semibold text-text-heading">{t("alerts.emptyTitle")}</p>
          <p className="mt-1 text-sm text-text-muted">{t("alerts.emptyDescription")}</p>
        </div>
      ) : null}
    </section>
  );
}

export default AlertsCenter;
