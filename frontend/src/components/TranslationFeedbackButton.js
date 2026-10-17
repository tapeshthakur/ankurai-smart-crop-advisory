import React, { useEffect, useRef, useState } from "react";
import { Languages, X } from "lucide-react";
import api from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { useLanguage } from "../i18n/LanguageContext";

function TranslationFeedbackButton() {
  const { isAuthenticated } = useAuth();
  const { language, t } = useLanguage();
  const [open, setOpen] = useState(false);
  const [reportedText, setReportedText] = useState("");
  const [suggestedText, setSuggestedText] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);
  const firstInput = useRef(null);
  const trigger = useRef(null);

  useEffect(() => {
    if (open) firstInput.current?.focus();
    else trigger.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const closeOnEscape = (event) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [open]);

  if (!isAuthenticated || !["hi", "mr"].includes(language)) return null;

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post("/api/translation-feedback", {
        language,
        page: window.location.pathname,
        reported_text: reportedText.trim(),
        suggested_text: suggestedText.trim(),
        note: note.trim(),
      });
      setSent(true);
    } catch {
      setError(t("translationFeedback.submitFailed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button ref={trigger} type="button" onClick={() => { setOpen(true); setSent(false); setError(""); }} className="theme-button-ghost inline-flex h-10 w-10 items-center justify-center px-0 sm:h-11 sm:w-auto sm:px-3" aria-label={t("translationFeedback.open")} title={t("translationFeedback.open")}>
        <Languages size={18} aria-hidden="true" /><span className="sr-only sm:not-sr-only sm:ml-2 sm:text-xs">{t("translationFeedback.shortLabel")}</span>
      </button>
      {open ? (
        <div className="fixed inset-0 z-[80] flex items-end justify-center bg-black/45 p-0 sm:items-center sm:p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false); }}>
          <section role="dialog" aria-modal="true" aria-labelledby="translation-feedback-title" className="max-h-[92dvh] w-full max-w-xl overflow-y-auto rounded-t-lg border border-surface-border bg-white p-4 shadow-lift sm:rounded-lg sm:p-6">
            <div className="flex items-start justify-between gap-3 border-b border-surface-border pb-4">
              <div>
                <span className="section-badge">{t("translationFeedback.eyebrow")}</span>
                <h2 id="translation-feedback-title" className="mt-2 text-lg font-semibold text-text-heading">{t("translationFeedback.title")}</h2>
                <p className="mt-1 text-sm leading-5 text-text-muted">{t("translationFeedback.subtitle")}</p>
              </div>
              <button type="button" onClick={() => setOpen(false)} className="theme-button-ghost h-10 w-10 shrink-0 px-0" aria-label={t("translationFeedback.close")}><X size={18} aria-hidden="true" /></button>
            </div>
            {sent ? (
              <div className="py-6" role="status" aria-live="polite">
                <p className="text-base font-semibold text-text-heading">{t("translationFeedback.thanks")}</p>
                <p className="mt-2 text-sm leading-6 text-text-muted">{t("translationFeedback.privacy")}</p>
                <button type="button" onClick={() => setOpen(false)} className="theme-button-primary mt-4 px-4 py-2.5">{t("translationFeedback.done")}</button>
              </div>
            ) : (
              <form className="mt-4 space-y-4" onSubmit={submit}>
                <label className="block text-sm font-medium text-text-heading">{t("translationFeedback.reportedLabel")}
                  <textarea ref={firstInput} className="field-shell mt-1 min-h-20 w-full" maxLength={1000} required value={reportedText} onChange={(event) => setReportedText(event.target.value)} placeholder={t("translationFeedback.reportedPlaceholder")} />
                </label>
                <label className="block text-sm font-medium text-text-heading">{t("translationFeedback.suggestionLabel")}
                  <textarea className="field-shell mt-1 min-h-20 w-full" maxLength={1000} value={suggestedText} onChange={(event) => setSuggestedText(event.target.value)} placeholder={t("translationFeedback.suggestionPlaceholder")} />
                </label>
                <label className="block text-sm font-medium text-text-heading">{t("translationFeedback.noteLabel")}
                  <textarea className="field-shell mt-1 min-h-20 w-full" maxLength={2000} required value={note} onChange={(event) => setNote(event.target.value)} placeholder={t("translationFeedback.notePlaceholder")} />
                </label>
                <p className="text-xs leading-5 text-text-subtle">{t("translationFeedback.privacy")}</p>
                {error ? <p className="text-sm text-danger-700" role="alert">{error}</p> : null}
                <div className="flex flex-wrap justify-end gap-2 border-t border-surface-border pt-4">
                  <button type="button" onClick={() => setOpen(false)} className="theme-button-secondary px-4 py-2.5">{t("translationFeedback.cancel")}</button>
                  <button type="submit" disabled={busy} className="theme-button-primary px-4 py-2.5">{busy ? t("translationFeedback.sending") : t("translationFeedback.submit")}</button>
                </div>
              </form>
            )}
          </section>
        </div>
      ) : null}
    </>
  );
}

export default TranslationFeedbackButton;
