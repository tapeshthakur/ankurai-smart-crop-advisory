import React, { useCallback, useEffect, useState } from "react";
import { Check, Languages, RefreshCw } from "lucide-react";
import api from "../api/client";
import { useLanguage } from "../i18n/LanguageContext";
import LoadingSpinner from "./LoadingSpinner";

function TranslationFeedbackReview() {
  const { language, t } = useLanguage();
  const [status, setStatus] = useState("open");
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [workingId, setWorkingId] = useState(null);
  const locale = language === "hi" ? "hi-IN" : language === "mr" ? "mr-IN" : "en-IN";

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get("/api/admin/translation-feedback", { params: { status } });
      setEntries(response.data.feedback || []);
    } catch {
      setError(t("translationFeedback.admin.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [status, t]);

  useEffect(() => { load(); }, [load]);

  const updateStatus = async (entry, nextStatus) => {
    setWorkingId(entry.id);
    setError("");
    try {
      await api.patch(`/api/admin/translation-feedback/${entry.id}`, { status: nextStatus });
      setEntries((current) => current.filter((item) => item.id !== entry.id));
    } catch {
      setError(t("translationFeedback.admin.updateFailed"));
    } finally {
      setWorkingId(null);
    }
  };

  return (
    <section className="surface-card min-w-0 p-4 sm:p-6" aria-labelledby="translation-feedback-review-title">
      <div className="flex flex-col gap-4 border-b border-surface-border pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <span className="section-badge"><Languages size={14} aria-hidden="true" /> {t("translationFeedback.admin.eyebrow")}</span>
          <h2 id="translation-feedback-review-title" className="mt-2 text-xl font-semibold text-text-heading sm:text-2xl">{t("translationFeedback.admin.title")}</h2>
          <p className="mt-1 text-sm leading-6 text-text-muted">{t("translationFeedback.admin.subtitle")}</p>
        </div>
        <div className="flex gap-2">
          <select className="theme-select min-w-36" value={status} onChange={(event) => setStatus(event.target.value)} aria-label={t("translationFeedback.admin.filter")}>
            {["open", "reviewed", "resolved"].map((value) => <option key={value} value={value}>{t(`translationFeedback.admin.status.${value}`)}</option>)}
          </select>
          <button type="button" onClick={load} disabled={loading} className="theme-button-secondary inline-flex min-h-11 items-center gap-2 px-3" aria-label={t("translationFeedback.admin.refresh")}><RefreshCw size={16} aria-hidden="true" />{t("translationFeedback.admin.refresh")}</button>
        </div>
      </div>
      {error ? <p className="mt-4 rounded-md border border-danger-100 bg-danger-50 px-3 py-2 text-sm text-danger-700" role="alert">{error}</p> : null}
      {loading ? <div className="mt-5"><LoadingSpinner label={t("translationFeedback.admin.loading")} /></div> : entries.length ? (
        <ul className="divide-y divide-surface-border">
          {entries.map((entry) => (
            <li key={entry.id} className="grid gap-4 py-5 lg:grid-cols-[minmax(0,1fr),auto]">
              <div className="min-w-0 space-y-3">
                <div className="flex flex-wrap items-center gap-2 text-xs text-text-muted">
                  <span className="status-chip status-info">{entry.language.toUpperCase()}</span>
                  <span>{entry.page || "/"}</span><span aria-hidden="true">·</span><span>{entry.user_name}</span>
                  <time dateTime={entry.created_at}>{new Date(entry.created_at).toLocaleString(locale)}</time>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="border-l-2 border-warning-500 pl-3"><p className="text-xs font-semibold text-text-muted">{t("translationFeedback.admin.reported")}</p><p className="mt-1 whitespace-pre-wrap break-words text-sm text-text-heading">{entry.reported_text}</p></div>
                  {entry.suggested_text ? <div className="border-l-2 border-primary-500 pl-3"><p className="text-xs font-semibold text-text-muted">{t("translationFeedback.admin.suggestion")}</p><p className="mt-1 whitespace-pre-wrap break-words text-sm text-text-heading">{entry.suggested_text}</p></div> : null}
                </div>
                <p className="whitespace-pre-wrap break-words text-sm leading-6 text-text-muted">{entry.note}</p>
              </div>
              <div className="flex flex-wrap gap-2 lg:justify-end">
                {status !== "reviewed" ? <button type="button" disabled={workingId === entry.id} onClick={() => updateStatus(entry, "reviewed")} className="theme-button-secondary min-h-10 px-3">{t("translationFeedback.admin.markReviewed")}</button> : null}
                {status !== "resolved" ? <button type="button" disabled={workingId === entry.id} onClick={() => updateStatus(entry, "resolved")} className="theme-button-primary inline-flex min-h-10 items-center gap-2 px-3"><Check size={15} aria-hidden="true" />{t("translationFeedback.admin.resolve")}</button> : null}
                {status !== "open" ? <button type="button" disabled={workingId === entry.id} onClick={() => updateStatus(entry, "open")} className="theme-button-ghost min-h-10 px-3">{t("translationFeedback.admin.reopen")}</button> : null}
              </div>
            </li>
          ))}
        </ul>
      ) : <p className="mt-5 border-t border-surface-border pt-5 text-sm text-text-muted">{t("translationFeedback.admin.empty")}</p>}
    </section>
  );
}

export default TranslationFeedbackReview;
