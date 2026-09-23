import React, { useEffect, useState } from "react";
import api from "../api/client";
import { useLanguage } from "../i18n/LanguageContext";

function FarmWorkspace({ crop, fieldId, onContextChange }) {
  const { t } = useLanguage();
  const [farms, setFarms] = useState([]);
  const [farmId, setFarmId] = useState("");
  const [reminders, setReminders] = useState([]);
  const [error, setError] = useState("");
  const [newFarmName, setNewFarmName] = useState("");
  const [newFieldName, setNewFieldName] = useState("");
  const [selectedFieldId, setSelectedFieldId] = useState(fieldId || "");

  const load = async () => {
    try {
      const response = await api.get("/api/farms");
      const nextFarms = response.data.farms || [];
      setFarms(nextFarms);
      const nextId = farmId || String(nextFarms[0]?.id || "");
      setFarmId(nextId);
      onContextChange?.(nextId, nextFarms.find((farm) => String(farm.id) === nextId)?.fields?.[0]?.id || fieldId || "");
    } catch (err) {
      setError(err.response?.data?.error || "Could not load farm workspace.");
    }
  };

  const loadReminders = async (id = farmId) => {
    if (!id) return;
    try {
      const response = await api.get(`/api/farms/${id}/reminders`);
      setReminders(response.data.reminders || []);
    } catch (err) {
      setError(err.response?.data?.error || "Could not load reminders.");
    }
  };

  useEffect(() => { load(); }, []);
  useEffect(() => { loadReminders(); }, [farmId]);

  const selectFarm = (value) => {
    setFarmId(value);
    const farm = farms.find((item) => String(item.id) === value);
    const nextField = farm?.fields?.[0]?.id || "";
    setSelectedFieldId(String(nextField));
    onContextChange?.(value, nextField);
  };

  const selectField = (value) => {
    setSelectedFieldId(value);
    onContextChange?.(farmId, value);
  };

  const acknowledge = async (id) => {
    await api.post(`/api/interventions/${id}/acknowledge`);
    loadReminders();
  };

  const outcome = async (id, status) => {
    await api.post(`/api/interventions/${id}/outcome`, { status });
    loadReminders();
  };

  const addFarm = async () => {
    if (!newFarmName.trim()) return;
    await api.post("/api/farms", { name: newFarmName.trim() });
    setNewFarmName("");
    load();
  };

  const addField = async () => {
    if (!farmId || !newFieldName.trim()) return;
    await api.post(`/api/farms/${farmId}/fields`, { name: newFieldName.trim(), crop });
    setNewFieldName("");
    load();
  };

  return (
    <section className="surface-card-soft space-y-3 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <span className="section-badge">{t("farmIntelligence.eyebrow", "Recommendation follow-up")}</span>
          <h2 className="mt-2 text-lg font-semibold text-text-heading">{t("farmIntelligence.title", "Keep the recommendation connected to the field")}</h2>
        </div>
        {farms.length ? <select className="field-shell max-w-xs" value={farmId} onChange={(event) => selectFarm(event.target.value)} aria-label={t("farmIntelligence.selectFarm", "Select farm")}>
          {farms.map((farm) => <option key={farm.id} value={farm.id}>{farm.name}</option>)}
        </select> : <div className="flex gap-2"><input className="field-shell max-w-xs" value={newFarmName} onChange={(event) => setNewFarmName(event.target.value)} placeholder={t("farmIntelligence.farmName", "Farm name")} /><button type="button" className="theme-button-primary px-3 py-2" onClick={addFarm}>{t("farmIntelligence.addFarm", "Add farm")}</button></div>}
      </div>
      {farmId ? <div className="flex flex-wrap gap-2"><select className="field-shell max-w-xs" value={selectedFieldId} onChange={(event) => selectField(event.target.value)} aria-label={t("farmIntelligence.selectField", "Select field")}><option value="">{t("farmIntelligence.allFields", "Farm-level recommendation")}</option>{(farms.find((farm) => String(farm.id) === String(farmId))?.fields || []).map((field) => <option key={field.id} value={field.id}>{field.name}</option>)}</select><input className="field-shell max-w-xs" value={newFieldName} onChange={(event) => setNewFieldName(event.target.value)} placeholder={t("farmIntelligence.fieldName", "Field name")} /><button type="button" className="theme-button-secondary px-3 py-2" onClick={addField}>{t("farmIntelligence.addField", "Add field")}</button></div> : null}
      {error ? <p className="text-sm text-danger-700">{error}</p> : null}
      {reminders.length ? reminders.slice(0, 3).map((reminder) => (
        <div key={reminder.id} className="rounded-2xl border border-accent-200 bg-accent-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent-700">{reminder.kind === "action" ? t("farmIntelligence.actionNeeded", "Action needed") : t("farmIntelligence.followUp", "Follow-up")}</p>
          <p className="mt-2 font-semibold text-text-heading">{reminder.crop || crop || "Crop"} {reminder.field_name ? `· ${reminder.field_name}` : ""}</p>
          <p className="mt-1 text-sm text-text-muted">{reminder.title}</p>
          {reminder.kind === "action" ? (
            <button type="button" className="theme-button-primary mt-3 px-4 py-2" onClick={() => acknowledge(reminder.id)}>{t("farmIntelligence.recordAction", "Record action")}</button>
          ) : (
            <div className="mt-3 flex flex-wrap gap-2">
              {["improved", "no_change", "worsened", "unknown"].map((status) => <button key={status} type="button" className="theme-button-secondary px-3 py-2 text-sm" onClick={() => outcome(reminder.id, status)}>{t(`farmIntelligence.${status}`, status.replace("_", " "))}</button>)}
            </div>
          )}
        </div>
      )) : (
        <p className="text-sm text-text-muted">{t("farmIntelligence.empty", "New recommendations can be followed up here after you select a farm.")}</p>
      )}
    </section>
  );
}

export default FarmWorkspace;
