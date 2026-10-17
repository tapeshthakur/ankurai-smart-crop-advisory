import React, { useEffect, useState } from "react";
import api from "../api/client";
import { getFieldSnapshot, saveFieldSnapshot } from "../api/offlineFieldStore";
import { useLanguage } from "../i18n/LanguageContext";

function FarmWorkspace({ crop, fieldId, userId, onContextChange }) {
  const { t } = useLanguage();
  const [farms, setFarms] = useState([]);
  const [farmId, setFarmId] = useState("");
  const [error, setError] = useState("");
  const [newFarmName, setNewFarmName] = useState("");
  const [newFieldName, setNewFieldName] = useState("");
  const [newFieldArea, setNewFieldArea] = useState("");
  const [selectedFieldArea, setSelectedFieldArea] = useState("");
  const [selectedFieldId, setSelectedFieldId] = useState(fieldId || "");

  const load = async () => {
    try {
      const response = await api.get("/api/farms");
      const nextFarms = response.data.farms || [];
      setFarms(nextFarms);
      saveFieldSnapshot(`farms:${userId || "current"}`, { farms: nextFarms }).catch(() => {});
      const nextId = farmId || String(nextFarms[0]?.id || "");
      setFarmId(nextId);
      const selectedFarm = nextFarms.find((farm) => String(farm.id) === nextId);
      const nextField = selectedFarm?.fields?.find((field) => String(field.id) === String(fieldId)) || selectedFarm?.fields?.[0];
      setSelectedFieldId(String(nextField?.id || ""));
      setSelectedFieldArea(nextField?.area_ha ?? "");
      onContextChange?.(nextId, nextField?.id || "", { ...nextField, farmName: selectedFarm?.name || "" });
    } catch {
      const snapshot = await getFieldSnapshot(`farms:${userId || "current"}`).catch(() => null);
      if (snapshot?.data?.farms) {
        const cachedFarms = snapshot.data.farms;
        setFarms(cachedFarms);
        const nextId = farmId || String(cachedFarms[0]?.id || "");
        setFarmId(nextId);
        const selectedFarm = cachedFarms.find((farm) => String(farm.id) === nextId);
        const nextField = selectedFarm?.fields?.find((field) => String(field.id) === String(fieldId)) || selectedFarm?.fields?.[0];
        setSelectedFieldId(String(nextField?.id || ""));
        setSelectedFieldArea(nextField?.area_ha ?? "");
        onContextChange?.(nextId, nextField?.id || "", { ...nextField, farmName: selectedFarm?.name || "" });
      } else {
        setError(t("farmIntelligence.loadError", "Could not load farm workspace."));
      }
    }
  };

  useEffect(() => { load(); }, []);

  const selectFarm = (value) => {
    setFarmId(value);
    const farm = farms.find((item) => String(item.id) === value);
    const nextField = farm?.fields?.[0] || null;
    setSelectedFieldId(String(nextField?.id || ""));
    setSelectedFieldArea(nextField?.area_ha ?? "");
    onContextChange?.(value, nextField?.id || "", { ...nextField, farmName: farm?.name || "" });
  };

  const selectField = (value) => {
    setSelectedFieldId(value);
    const field = farms.find((item) => String(item.id) === String(farmId))?.fields?.find((item) => String(item.id) === String(value));
    setSelectedFieldArea(field?.area_ha ?? "");
    const farm = farms.find((item) => String(item.id) === String(farmId));
    onContextChange?.(farmId, value, { ...field, farmName: farm?.name || "" });
  };

  const addFarm = async () => {
    if (!newFarmName.trim()) return;
    try {
      await api.post("/api/farms", { name: newFarmName.trim() });
      setNewFarmName("");
      await load();
    } catch {
      setError(t("farmIntelligence.addFarmFailed", "Could not add this farm. Try again."));
    }
  };

  const addField = async () => {
    if (!farmId || !newFieldName.trim()) return;
    try {
      await api.post(`/api/farms/${farmId}/fields`, { name: newFieldName.trim(), crop, area_ha: newFieldArea || undefined });
      setNewFieldName("");
      setNewFieldArea("");
      await load();
    } catch {
      setError(t("farmIntelligence.addFieldFailed", "Could not add this field. Try again."));
    }
  };

  const saveFieldArea = async () => {
    if (!farmId || !selectedFieldId) return;
    try {
      await api.patch(`/api/farms/${farmId}/fields/${selectedFieldId}`, { area_ha: selectedFieldArea || null });
      await load();
    } catch {
      setError(t("farmIntelligence.saveAreaFailed", "Could not update the field area. Try again."));
    }
  };

  return (
    <section className="surface-card p-4 sm:p-5">
      <div>
        <span className="section-badge">{t("farmIntelligence.eyebrow", "Recommendation follow-up")}</span>
        <h2 className="mt-2 text-lg font-semibold text-text-heading">{t("farmIntelligence.title", "Keep the recommendation connected to the field")}</h2>
      </div>

      <div className={`mt-4 grid gap-3 border-t border-surface-border pt-4 ${farms.length ? "lg:grid-cols-2" : ""}`}>
        {farms.length ? <label className="min-w-0 text-xs font-medium text-text-muted">{t("farmIntelligence.farmLabel", "Farm")}
          <select className="theme-select mt-1 w-full" value={farmId} onChange={(event) => selectFarm(event.target.value)} aria-label={t("farmIntelligence.selectFarm", "Select farm")}>
            {farms.map((farm) => <option key={farm.id} value={farm.id}>{farm.name}</option>)}
          </select>
        </label> : null}
        <div className="min-w-0">
          <label className="text-xs font-medium text-text-muted" htmlFor="new-farm-name">{t("farmIntelligence.farmName", "New farm")}</label>
          <div className="mt-1 grid gap-2 sm:grid-cols-[minmax(0,1fr),auto]">
            <input id="new-farm-name" className="field-shell min-w-0" value={newFarmName} onChange={(event) => setNewFarmName(event.target.value)} placeholder={t("farmIntelligence.farmNamePlaceholder", "Farm name")} />
            <button type="button" className="theme-button-secondary whitespace-nowrap" onClick={addFarm} disabled={!newFarmName.trim()}>{t("farmIntelligence.addFarm", "Add farm")}</button>
          </div>
        </div>
      </div>

      {farmId ? <div className="mt-4 grid gap-4 border-t border-surface-border pt-4 lg:grid-cols-[minmax(0,0.9fr),minmax(0,1.1fr)]">
        <div className="grid min-w-0 gap-3 sm:grid-cols-2">
          <label className="min-w-0 text-xs font-medium text-text-muted">{t("farmIntelligence.fieldLabel", "Field")}
            <select className="theme-select mt-1 w-full" value={selectedFieldId} onChange={(event) => selectField(event.target.value)} aria-label={t("farmIntelligence.selectField", "Select field")}><option value="">{t("farmIntelligence.allFields", "Farm-level recommendation")}</option>{(farms.find((farm) => String(farm.id) === String(farmId))?.fields || []).map((field) => <option key={field.id} value={field.id}>{field.name}</option>)}</select>
          </label>
          <div className="min-w-0">
            <label className="text-xs font-medium text-text-muted" htmlFor="selected-field-area">{t("farmIntelligence.areaLabel", "Area (ha)")}</label>
            <div className="mt-1 grid grid-cols-[minmax(0,1fr),auto] gap-2">
              <input id="selected-field-area" className="field-shell min-w-0" type="number" min="0.01" step="0.01" value={selectedFieldArea} onChange={(event) => setSelectedFieldArea(event.target.value)} placeholder={t("farmIntelligence.areaPlaceholder", "Field area")} />
              <button type="button" className="theme-button-secondary whitespace-nowrap" onClick={saveFieldArea} disabled={!selectedFieldId}>{t("farmIntelligence.saveArea", "Save area")}</button>
            </div>
          </div>
        </div>

        <div className="min-w-0 border-t border-surface-border pt-3 lg:border-l lg:border-t-0 lg:pl-4 lg:pt-0">
          <h3 className="text-xs font-semibold text-text-muted">{t("farmIntelligence.addFieldHeading", "Add a field")}</h3>
          <div className="mt-1 grid min-w-0 gap-2 sm:grid-cols-[minmax(0,1fr),minmax(7rem,0.55fr),auto]">
            <label className="min-w-0 text-xs text-text-muted">{t("farmIntelligence.nameLabel", "Name")}<input className="field-shell mt-1 min-w-0" value={newFieldName} onChange={(event) => setNewFieldName(event.target.value)} placeholder={t("farmIntelligence.fieldNamePlaceholder", "Field name")} /></label>
            <label className="min-w-0 text-xs text-text-muted">{t("farmIntelligence.areaLabel", "Area (ha)")}<input className="field-shell mt-1 min-w-0" type="number" min="0.01" step="0.01" value={newFieldArea} onChange={(event) => setNewFieldArea(event.target.value)} placeholder={t("farmIntelligence.optional", "Optional")} /></label>
            <div className="flex items-end"><button type="button" className="theme-button-primary w-full whitespace-nowrap" onClick={addField} disabled={!newFieldName.trim()}>{t("farmIntelligence.addField", "Add field")}</button></div>
          </div>
        </div>
      </div> : <p className="mt-4 border-t border-surface-border pt-4 text-sm text-text-muted">{t("farmIntelligence.createFarmFirst", "Create a farm above to start adding fields and area details.")}</p>}
      {error ? <p role="alert" className="mt-3 rounded-md border border-danger-100 bg-danger-50 px-3 py-2 text-sm text-danger-700">{error}</p> : null}
    </section>
  );
}

export default FarmWorkspace;
