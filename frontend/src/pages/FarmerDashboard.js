import React, { useEffect, useMemo, useState } from "react";
import api from "../api/client";
import { getFieldSnapshot, saveFieldSnapshot, savePendingTaskNote } from "../api/offlineFieldStore";
import { useAuth } from "../auth/AuthContext";
import AskAiAssistant from "../components/AskAiAssistant";
import CropCard from "../components/CropCard";
import DiseaseDetector from "../components/DiseaseDetector";
import EmptyState from "../components/EmptyState";
import LoadingSkeleton from "../components/LoadingSkeleton";
import LoadingSpinner from "../components/LoadingSpinner";
import MarketInsights from "../components/MarketInsights";
import FarmWorkspace from "../components/FarmWorkspace";
import Sidebar from "../components/Sidebar";
import MobileBottomNav from "../components/MobileBottomNav";
import PestOutbreakCard from "../components/PestOutbreakCard";
import ProductionOutlookCard from "../components/ProductionOutlookCard";
import SoilRestorationCard from "../components/SoilRestorationCard";
import SoilPlanningWorkspace from "../components/SoilPlanningWorkspace";
import FieldTimeline from "../components/FieldTimeline";
import PredictionComparison from "../components/PredictionComparison";
import WeatherSignals from "../components/WeatherSignals";
import ThemedSelect from "../components/ThemedSelect";
import FarmReportButton from "../components/FarmReportButton";
import AlertsCenter from "../components/AlertsCenter";
import { useLanguage } from "../i18n/LanguageContext";

import riceImage from "../assets/crops/rice.jpg";
import wheatImage from "../assets/crops/wheat.jpg";
import maizeImage from "../assets/crops/maize.jpg";
import chickpeaImage from "../assets/crops/chickpea.jpg";
import coffeeImage from "../assets/crops/coffee.jpg";
import cottonImage from "../assets/crops/cotton.jpg";
import soybeanImage from "../assets/crops/soybean.jpg";
import sugarcaneImage from "../assets/crops/sugarcane.jpg";

const FEATURE_FIELDS = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"];
const FIELD_RANGES = {
  N: { min: 0, max: 140, step: 1, fallback: 50 },
  P: { min: 0, max: 140, step: 1, fallback: 45 },
  K: { min: 0, max: 140, step: 1, fallback: 45 },
  temperature: { min: 0, max: 50, step: 0.1, fallback: 25 },
  humidity: { min: 0, max: 100, step: 1, fallback: 70 },
  ph: { min: 4, max: 9, step: 0.1, fallback: 6.5 },
  rainfall: { min: 0, max: 350, step: 1, fallback: 120 },
};
const STATE_OPTIONS = ["Maharashtra", "Punjab", "Uttar Pradesh", "Karnataka", "Gujarat"];
const SEASON_OPTIONS = ["Auto", "Kharif", "Rabi", "Zaid"];
const CROP_PRESETS = {
  wheat: {
    labelKey: "wheat",
    descriptionKey: "farmer.presets.wheatDesc",
    values: { N: "52", P: "50", K: "52", temperature: "20", humidity: "68", ph: "6.7", rainfall: "140" },
  },
  rice: {
    labelKey: "rice",
    descriptionKey: "farmer.presets.riceDesc",
    values: { N: "90", P: "45", K: "42", temperature: "27", humidity: "84", ph: "6.4", rainfall: "245" },
  },
  maize: {
    labelKey: "maize",
    descriptionKey: "farmer.presets.maizeDesc",
    values: { N: "65", P: "40", K: "40", temperature: "27", humidity: "62", ph: "6.5", rainfall: "145" },
  },
  chickpea: {
    labelKey: "chickpea",
    descriptionKey: "farmer.presets.chickpeaDesc",
    values: { N: "35", P: "55", K: "50", temperature: "23", humidity: "58", ph: "6.8", rainfall: "90" },
  },
  coffee: {
    labelKey: "coffee",
    descriptionKey: "farmer.presets.coffeeDesc",
    values: { N: "30", P: "40", K: "35", temperature: "22", humidity: "60", ph: "6.0", rainfall: "90" },
  },
  cotton: {
    labelKey: "cotton",
    descriptionKey: "farmer.presets.cottonDesc",
    values: { N: "60", P: "35", K: "45", temperature: "30", humidity: "60", ph: "6.8", rainfall: "85" },
  },
  sugarcane: {
    labelKey: "sugarcane",
    descriptionKey: "farmer.presets.sugarcaneDesc",
    values: { N: "110", P: "60", K: "90", temperature: "28", humidity: "72", ph: "6.8", rainfall: "220" },
  },
  soybean: {
    labelKey: "soybean",
    descriptionKey: "farmer.presets.soybeanDesc",
    values: { N: "35", P: "45", K: "45", temperature: "25", humidity: "65", ph: "6.7", rainfall: "350" },
  },
};
const CROP_IMAGE_MAP = {
  chickpea: chickpeaImage,
  coffee: coffeeImage,
  rice: riceImage,
  paddy: riceImage,
  wheat: wheatImage,
  maize: maizeImage,
  corn: maizeImage,
  cotton: cottonImage,
  soybean: soybeanImage,
  sugarcane: sugarcaneImage,
};
const HISTORY_PAIR_WINDOW_MS = 10000;
const PEST_MODEL_CROPS = new Set(["rice", "wheat", "maize", "corn", "cotton", "soybean"]);

function clampNumber(value, min, max) {
  const number = Number(value);
  if (!Number.isFinite(number)) return min;
  return Math.max(min, Math.min(max, number));
}

function daysAfterPlanting(plantingDate) {
  if (!plantingDate) return 45;
  const planted = new Date(`${plantingDate}T00:00:00`);
  if (Number.isNaN(planted.getTime())) return 45;
  const diffDays = Math.ceil((Date.now() - planted.getTime()) / (1000 * 60 * 60 * 24));
  return clampNumber(diffDays, 1, 180);
}

function formatHistoryDate(value, language) {
  const date = new Date(value || "");
  if (Number.isNaN(date.getTime())) return value || "-";
  const locale = language === "hi" ? "hi-IN" : language === "mr" ? "mr-IN" : "en-IN";
  return date.toLocaleString(locale, { dateStyle: "medium", timeStyle: "short" });
}

function buildPestFallbackForecast(crop, advisory) {
  const pestRisk = advisory?.production_outlook?.pest_risk;
  if (!pestRisk) return null;
  const level = String(pestRisk.level || "low").toLowerCase();
  const probabilityByLevel = { high: 0.75, moderate: 0.5, low: 0.2 };
  const probability = probabilityByLevel[level] ?? 0.2;
  const pests = pestRisk.likely_pests?.length ? pestRisk.likely_pests : ["field pests"];
  const forecasts = pests.map((pest) => ({
    pest,
    outbreak_probability: probability,
    outbreak_next_7d: probability >= 0.5 ? 1 : 0,
    risk_level: level,
  }));
  return {
    crop,
    forecast_window_days: 7,
    source: "planning_outlook_fallback",
    highest_risk: forecasts[0],
    forecasts,
  };
}

function predictionInputKey(inputData) {
  if (!inputData || typeof inputData !== "object") return "";
  return Object.keys(inputData)
    .sort()
    .map((key) => `${key}:${inputData[key]}`)
    .join("|");
}

function mergePredictionHistory(rows) {
  const groups = [];

  rows.forEach((row) => {
    const timestampMs = Date.parse(row.timestamp || "");
    const inputKey = predictionInputKey(row.input_data);
    const userKey = row.user_id ?? "current";
    const match = groups.find((group) => {
      if (group.inputKey !== inputKey || group.userKey !== userKey) return false;
      if (!Number.isFinite(timestampMs) || !Number.isFinite(group.timestampMs)) return false;
      return Math.abs(group.timestampMs - timestampMs) <= HISTORY_PAIR_WINDOW_MS;
    });

    if (match) {
      match.crop_prediction = match.crop_prediction || row.crop_prediction;
      match.irrigation_prediction =
        match.irrigation_prediction ?? row.irrigation_prediction;
      match.ids.push(row.id);
      if (Number.isFinite(timestampMs) && timestampMs > match.timestampMs) {
        match.timestamp = row.timestamp;
        match.timestampMs = timestampMs;
      }
      return;
    }

    groups.push({
      ...row,
      ids: [row.id],
      inputKey,
      userKey,
      timestampMs,
    });
  });

  return groups;
}

function FarmerDashboard() {
  const { user } = useAuth();
  const { t, tv, language } = useLanguage();
  const [activeTab, setActiveTab] = useState("crop");
  const [selectedState, setSelectedState] = useState("Maharashtra");
  const [selectedSeason, setSelectedSeason] = useState("Auto");
  const [plantingDate, setPlantingDate] = useState("");
  const [liveWeather, setLiveWeather] = useState(null);
  const [weatherForecast, setWeatherForecast] = useState(null);
  const [form, setForm] = useState({ N: "", P: "", K: "", temperature: "", humidity: "", ph: "", rainfall: "" });
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [advisory, setAdvisory] = useState(null);
  const [pestForecast, setPestForecast] = useState(null);
  const [pestLoading, setPestLoading] = useState(false);
  const [pestForecastStatus, setPestForecastStatus] = useState("idle");
  const [predictions, setPredictions] = useState([]);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [farmId, setFarmId] = useState("");
  const [fieldId, setFieldId] = useState("");
  const [selectedField, setSelectedField] = useState(null);
  const [soilTasks, setSoilTasks] = useState([]);
  const [savedReminders, setSavedReminders] = useState({});
  const [farmDueCount, setFarmDueCount] = useState(0);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [dashboardCacheLoaded, setDashboardCacheLoaded] = useState(false);
  const [hasOfflineSnapshot, setHasOfflineSnapshot] = useState(false);
  const dashboardCacheKey = `dashboard:${user?.id || user?.email || "current"}`;

  const tabs = [
    { id: "crop", label: t("farmer.cropTab"), mobileLabel: t("farmer.mobileCropTab", "Crop"), eyebrow: t("farmer.cropEyebrow"), description: t("farmer.cropDesc") },
    { id: "soil", label: t("farmer.soilTab", "Planning & Soil Care"), mobileLabel: t("farmer.mobileSoilTab", "Soil"), eyebrow: t("farmer.soilEyebrow", "Outlook + recovery plan"), description: t("farmer.soilDesc", "Review yield outlook, pest scouting, rotations, and long-term soil recovery.") },
    { id: "disease", label: t("farmer.diseaseTab"), mobileLabel: t("farmer.mobileDiseaseTab", "Disease"), eyebrow: t("farmer.diseaseEyebrow"), description: t("farmer.diseaseDesc") },
    { id: "market", label: t("farmer.marketTab"), mobileLabel: t("farmer.mobileMarketTab", "Market"), eyebrow: t("farmer.marketEyebrow"), description: t("farmer.marketDesc") },
    {
      id: "ai",
      label: t("ai.tab", "Ask AI"),
      mobileLabel: t("ai.mobileTab", "AI"),
      eyebrow: t("ai.eyebrow", "Farm assistant"),
      description: t("ai.description", "Ask follow-up questions about your crop, irrigation, disease, and market guidance."),
    },
    { id: "history", label: t("farmer.historyTab"), mobileLabel: t("farmer.mobileHistoryTab", "History"), eyebrow: t("farmer.historyEyebrow"), description: t("farmer.historyDesc") },
    { id: "alerts", label: t("alerts.title"), mobileLabel: t("alerts.mobileLabel"), eyebrow: t("alerts.eyebrow"), description: t("alerts.subtitle") },
  ];

  const fetchHistory = async () => {
    try {
      setHistoryLoading(true);
      const response = await api.get("/api/predictions");
      setPredictions(response.data.predictions || []);
    } catch (err) {
      const snapshot = await getFieldSnapshot(dashboardCacheKey).catch(() => null);
      if (snapshot?.data?.predictions) {
        setPredictions(snapshot.data.predictions);
        setHasOfflineSnapshot(true);
        if (!navigator.onLine) setError("");
      } else {
        setError(err.response?.data?.error || t("farmer.historyFailed"));
      }
    } finally {
      setHistoryLoading(false);
    }
  };

  const completeSoilTask = async (task) => {
    try {
      const response = await api.patch(`/api/soil-plan-tasks/${task.id}`, { status: "completed", notes: task.notes || "" });
      setSoilTasks((current) => current.map((item) => item.id === task.id ? response.data.task : item));
    } catch (err) {
      if (!err.response || !navigator.onLine) {
        await savePendingTaskNote(task.id, task.notes || "", "completed");
        setSoilTasks((current) => current.map((item) => item.id === task.id ? { ...item, status: "completed" } : item));
        return;
      }
      throw err;
    }
  };

  const openTimelineItem = (destination) => {
    if (destination === "crop") {
      setActiveTab("crop");
      return;
    }
    const targetId = destination === "pest" ? "pest-outbreak" : "soil-plan-workspace";
    document.getElementById(targetId)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  useEffect(() => {
    let active = true;
    getFieldSnapshot(dashboardCacheKey).then((snapshot) => {
      if (!active || !snapshot?.data) return;
      setHasOfflineSnapshot(true);
      if (!navigator.onLine) {
        const cached = snapshot.data;
        setForm(cached.form || { N: "", P: "", K: "", temperature: "", humidity: "", ph: "", rainfall: "" });
        setResult(cached.result || null);
        setAdvisory(cached.advisory || null);
        setPestForecast(cached.pestForecast || null);
        setPredictions(cached.predictions || []);
        setWeatherForecast(cached.weatherForecast || null);
        setSelectedState(cached.selectedState || "Maharashtra");
        setSelectedSeason(cached.selectedSeason || "Auto");
        setPlantingDate(cached.plantingDate || "");
      }
    }).finally(() => {
      if (active) setDashboardCacheLoaded(true);
    });
    const updateConnection = () => setIsOnline(navigator.onLine);
    window.addEventListener("online", updateConnection);
    window.addEventListener("offline", updateConnection);
    return () => {
      active = false;
      window.removeEventListener("online", updateConnection);
      window.removeEventListener("offline", updateConnection);
    };
  }, [dashboardCacheKey]);

  useEffect(() => {
    if (!dashboardCacheLoaded) return;
    saveFieldSnapshot(dashboardCacheKey, {
      form, result, advisory, pestForecast, predictions, weatherForecast,
      selectedState, selectedSeason, plantingDate,
    }).then(() => setHasOfflineSnapshot(true)).catch(() => {});
  }, [dashboardCacheKey, dashboardCacheLoaded, form, result, advisory, pestForecast, predictions, weatherForecast, selectedState, selectedSeason, plantingDate]);

  useEffect(() => {
    const syncReminders = () => {
      try {
        const stored = JSON.parse(localStorage.getItem("ankurai_field_reminders") || "{}");
        setSavedReminders(stored && typeof stored === "object" && !Array.isArray(stored) ? stored : {});
      } catch {
        setSavedReminders({});
      }
    };
    syncReminders();
    window.addEventListener("ankurai-reminders-change", syncReminders);
    window.addEventListener("storage", syncReminders);
    return () => {
      window.removeEventListener("ankurai-reminders-change", syncReminders);
      window.removeEventListener("storage", syncReminders);
    };
  }, []);

  const handleChange = (field, value) => {
    if (value === "" || /^-?\d*\.?\d*$/.test(value)) {
      setForm((prev) => ({ ...prev, [field]: value }));
    }
  };

  const applyPreset = (presetKey) => {
    const preset = CROP_PRESETS[presetKey];
    if (!preset) return;
    setForm(preset.values);
    setError("");
  };

  const applyWeatherValues = (weather) => {
    setForm((prev) => ({
      ...prev,
      temperature: String(weather.temperature),
      humidity: String(weather.humidity),
      rainfall: String(weather.rainfall),
    }));
    setLiveWeather(weather);
  };

  const fetchWeatherForLocation = async () => {
    setError("");
    if (!navigator.geolocation) {
      setError(t("farmer.geoUnsupported"));
      return;
    }

    setWeatherLoading(true);
    setWeatherForecast(null);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const { latitude, longitude } = position.coords;
          const response = await fetch(
            `https://api.open-meteo.com/v1/forecast?latitude=${latitude}&longitude=${longitude}&current=temperature_2m,relative_humidity_2m,rain&daily=precipitation_probability_max,precipitation_sum,temperature_2m_max&forecast_days=7&timezone=auto`
          );
          if (!response.ok) {
            throw new Error("Weather service unavailable");
          }
          const data = await response.json();
          const daily = data.daily || {};
          setWeatherForecast({
            source: "Open-Meteo",
            fetched_at: new Date().toISOString(),
            days: (daily.time || []).map((date, index) => ({
              date,
              precipitation_probability: daily.precipitation_probability_max?.[index],
              precipitation_mm: daily.precipitation_sum?.[index],
              temperature_max_c: daily.temperature_2m_max?.[index],
            })),
          });
          applyWeatherValues({
            temperature: Number(data.current?.temperature_2m || 0).toFixed(1),
            humidity: Number(data.current?.relative_humidity_2m || 0).toFixed(0),
            rainfall: Number(data.current?.rain || 0).toFixed(1),
            source: "Open-Meteo",
          });
        } catch (_err) {
          setError(t("farmer.weatherFailed"));
        } finally {
          setWeatherLoading(false);
        }
      },
      () => {
        setWeatherLoading(false);
        setError(t("farmer.locationDenied"));
      },
      { enableHighAccuracy: false, timeout: 10000 }
    );
  };

  const printAdvisory = () => {
    window.print();
  };

  const isComplete = FEATURE_FIELDS.every((field) => form[field] !== "");

  const handlePredict = async (event) => {
    event.preventDefault();
    setError("");

    if (!isComplete) {
      setError(t("farmer.fillFields"));
      return;
    }

    const payload = Object.fromEntries(FEATURE_FIELDS.map((field) => [field, Number(form[field])]));
    if (farmId) payload.farm_id = Number(farmId);
    if (fieldId) payload.field_id = Number(fieldId);

    try {
      setLoading(true);
      const [cropOutcome, irrigationResponse] = await Promise.all([
        api.post("/api/predict/crop", payload).catch((err) => {
          const legacyResult = err.response?.data;
          const topCrop = legacyResult?.top_crops?.[0];
          if (topCrop?.crop && Number.isFinite(Number(topCrop.confidence))) {
            return {
              data: {
                result: {
                  predicted_crop: topCrop.crop,
                  confidence: Number(topCrop.confidence),
                  confidence_threshold: legacyResult.confidence_threshold,
                  confidence_note: legacyResult.error || "Low-confidence recommendation. Review the top alternatives before making a decision.",
                  is_low_confidence: true,
                  top_crops: legacyResult.top_crops || [],
                },
              },
            };
          }
          throw err;
        }),
        api.post("/api/predict/irrigation", payload),
      ]);

      const nextResult = {
        crop: cropOutcome.data.result?.predicted_crop,
        confidence: cropOutcome.data.result?.confidence,
        confidenceThreshold: cropOutcome.data.result?.confidence_threshold,
        confidenceNote: cropOutcome.data.result?.confidence_note,
        isLowConfidence: Boolean(cropOutcome.data.result?.is_low_confidence),
        irrigation: irrigationResponse.data.result?.predicted_irrigation_requirement,
        topCrops: cropOutcome.data.result?.top_crops || [],
      };

      const advisoryResponse = await api.post("/api/advisory", {
        crop: nextResult.crop,
        confidence: nextResult.confidence,
        irrigation: nextResult.irrigation,
        inputs: payload,
        state: selectedState,
        season: selectedSeason,
        top_crops: nextResult.topCrops,
        planting_date: plantingDate || undefined,
      });

      const nextAdvisory = advisoryResponse.data.advisory || null;
      setResult(nextResult);
      setAdvisory(nextAdvisory);
      setPestForecast(null);
      setPestForecastStatus("idle");
      const pestCrop = String(nextResult.crop || "").toLowerCase();
      if (PEST_MODEL_CROPS.has(pestCrop)) {
        setPestLoading(true);
        setPestForecastStatus("loading");
        try {
          const rainfall7d = clampNumber(Number(form.rainfall), 0, 500);
          const humidity = clampNumber(Number(form.humidity), 0, 100);
          const pestResponse = await api.post("/api/predict/pest-outbreak", {
            crop: nextResult.crop,
            month: new Date().getMonth() + 1,
            days_after_sowing: daysAfterPlanting(plantingDate),
            temperature_c: Number(form.temperature),
            humidity_pct: humidity,
            rainfall_7d_mm: rainfall7d,
            rainfall_14d_mm: clampNumber(rainfall7d * 1.7, 0, 700),
            wind_speed_kmh: 8,
            soil_moisture_pct: clampNumber((humidity * 0.45) + (rainfall7d * 0.18), 10, 95),
            trap_count_7d: 0,
            previous_pest_count_7d: 0,
          });
          setPestForecast(pestResponse.data.result || null);
          setPestForecastStatus("ready");
        } catch (_pestErr) {
          const fallbackForecast = buildPestFallbackForecast(nextResult.crop, nextAdvisory);
          setPestForecast(fallbackForecast);
          setPestForecastStatus(fallbackForecast ? "fallback" : "error");
        } finally {
          setPestLoading(false);
        }
      } else {
        setPestLoading(false);
        const fallbackForecast = buildPestFallbackForecast(nextResult.crop, nextAdvisory);
        setPestForecast(fallbackForecast);
        setPestForecastStatus(fallbackForecast ? "fallback" : `unsupported:${nextResult.crop || "this crop"}`);
      }
      setActiveTab("crop");
      await fetchHistory();
    } catch (err) {
      setError(err.response?.data?.error || t("farmer.predictionFailed"));
    } finally {
      setLoading(false);
    }
  };

  const combinedPredictions = useMemo(() => mergePredictionHistory(predictions), [predictions]);
  const cropKey = String(result?.crop || "").toLowerCase();
  const cropImage = CROP_IMAGE_MAP[cropKey] || wheatImage;
  const latestCrop = result?.crop || combinedPredictions.find((item) => item.crop_prediction)?.crop_prediction || t("farmer.noPredictionYet");
  const latestCropDisplay = latestCrop === t("farmer.noPredictionYet") ? latestCrop : tv("crops", latestCrop);
  const marketCrop = result?.crop || combinedPredictions.find((item) => item.crop_prediction)?.crop_prediction || "wheat";
  const aiContext = useMemo(
    () => ({
      selectedState,
      selectedSeason,
      form,
      liveWeather,
      result,
      advisory,
      pestForecast,
      latestCrop: latestCrop === t("farmer.noPredictionYet") ? "" : latestCrop,
      recentPredictions: combinedPredictions.slice(0, 5),
    }),
    [advisory, combinedPredictions, form, latestCrop, liveWeather, pestForecast, result, selectedSeason, selectedState, t]
  );
  const dueReminders = Object.values(savedReminders).filter((reminder) => {
    if (!reminder || typeof reminder !== "object" || !reminder.due_date) return false;
    const due = new Date(`${reminder.due_date}T00:00:00`);
    if (Number.isNaN(due.getTime())) return false;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const soon = new Date(today);
    soon.setDate(soon.getDate() + 7);
    return due <= soon;
  });
  const formatReminderDate = (value) => {
    const date = new Date(`${value}T00:00:00`);
    const locale = language === "hi" ? "hi-IN" : language === "mr" ? "mr-IN" : "en-IN";
    return date.toLocaleDateString(locale, { day: "numeric", month: "short" });
  };

  return (
    <main className="farmer-dashboard mx-auto w-full max-w-7xl px-4 py-6 pb-24 sm:px-6 lg:px-8 lg:pb-6">
      <div className="farmer-dashboard__content grid min-w-0 grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[285px,minmax(0,1fr)]">
        <Sidebar role={user?.role} moduleItems={tabs} activeModule={activeTab} onModuleChange={setActiveTab} />
        <MobileBottomNav items={tabs} activeModule={activeTab} onModuleChange={setActiveTab} />

        <section className="min-w-0 space-y-6">
          {!isOnline ? <div className="border-l-2 border-warning-700 bg-warning-50 px-4 py-3 text-sm text-text-heading" role="status" aria-live="polite">
            <p className="font-semibold">{t(hasOfflineSnapshot ? "farmer.offlineCached" : "farmer.offlineNoCache")}</p>
            <p className="mt-1 text-xs text-text-muted">{t("farmer.offlineDetails")}</p>
          </div> : null}
          {dueReminders.length || farmDueCount ? (
            <div className="flex flex-col gap-3 border-l-2 border-accent-500 bg-accent-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between" role="status" aria-live="polite">
              <div>
                <p className="text-sm font-semibold text-text-heading">{t("alerts.dueCount", undefined, { count: Math.max(dueReminders.length, farmDueCount) })}</p>
                <ul className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-muted">
                  {dueReminders.map((reminder, index) => <li key={`${reminder.due_date}-${reminder.title}-${index}`}>{reminder.title} · {formatReminderDate(reminder.due_date)}</li>)}
                </ul>
              </div>
              <button type="button" className="theme-button-secondary min-h-10 px-3 py-2 text-xs" onClick={() => setActiveTab("alerts")}>{t("farmer.reviewReminders")}</button>
            </div>
          ) : null}
          <div className="border-b border-surface-border pb-5">
            <div className="grid gap-5">
              <div>
                <span className="section-badge">{t("farmer.heroBadge")}</span>
                <h1 className="mt-3 max-w-3xl text-2xl font-bold leading-tight text-text-heading sm:text-3xl">
                  {t("farmer.welcome")}, {user?.name}
                </h1>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-text-muted">{t("farmer.intro")}</p>
                <dl className="mt-4 flex flex-wrap gap-x-6 gap-y-2 border-l-2 border-accent-300 pl-3 text-sm">
                  <div><dt className="text-xs text-text-muted">{t("farmer.state")}</dt><dd className="mt-0.5 font-semibold text-text-heading">{tv("states", selectedState)}</dd></div>
                  <div><dt className="text-xs text-text-muted">{t("farmer.season")}</dt><dd className="mt-0.5 font-semibold text-text-heading">{tv("seasons", selectedSeason)}</dd></div>
                  <div><dt className="text-xs text-text-muted">{t("farmer.weatherReady")}</dt><dd className={`mt-0.5 font-semibold ${liveWeather ? "text-success-700" : "text-text-muted"}`}>{liveWeather ? t("farmer.yes") : t("farmer.no")}</dd></div>
                </dl>
              </div>

            </div>
          </div>

          <section className="dashboard-snapshot" aria-labelledby="dashboard-snapshot-title">
            <h2 id="dashboard-snapshot-title" className="text-sm font-semibold text-text-heading">{t("farmer.decisionSummary")}</h2>
            <div className="dashboard-snapshot__grid">
              <div className="dashboard-snapshot__item border-primary-300">
                <p className="text-xs text-text-muted">{t("farmIntelligence.fieldLabel")}</p>
                <p className="dashboard-snapshot__value mt-1 break-words">{selectedField?.name || t("farmIntelligence.selectField")}</p>
                <p className="mt-1 truncate text-xs text-text-subtle">{selectedField?.area_ha ? `${selectedField.area_ha} ha` : selectedField?.farmName || ""}</p>
              </div>
              <div className="dashboard-snapshot__item border-accent-400">
                <p className="text-xs text-text-muted">{t("farmer.latestCrop")}</p>
                <p className="dashboard-snapshot__value mt-1 break-words capitalize">{latestCropDisplay}</p>
                <p className="mt-1 text-xs text-text-subtle">{t("farmer.latestCropSubtitle")}</p>
              </div>
              <div className="dashboard-snapshot__item border-sky-600">
                <p className="text-xs text-text-muted">{t("farmer.weatherSnapshot")}</p>
                <p className="dashboard-snapshot__value mt-1 break-words">{form.temperature ? `${form.temperature} °C` : "-"}</p>
                <p className="mt-1 text-xs text-text-subtle">{liveWeather ? t("farmer.weatherReady") : `${form.humidity || "-"}% · ${form.rainfall || "-"} mm`}</p>
              </div>
              <div className="dashboard-snapshot__item border-warning-700">
                <p className="text-xs text-text-muted">{t("farmer.alerts", "Alerts")}</p>
                <p className="dashboard-snapshot__value mt-1 tabular-nums">{Math.max(dueReminders.length, farmDueCount)}</p>
                <p className="mt-1 text-xs leading-5 text-text-subtle">{farmDueCount || dueReminders.length ? t("alerts.dueCount", undefined, { count: Math.max(dueReminders.length, farmDueCount) }) : t("farmer.noAlerts", "No reminders due")}</p>
              </div>
            </div>
          </section>

          {activeTab === "crop" ? (
            <div className="tab-panel space-y-6">
              <FarmWorkspace
                crop={result?.crop || ""}
                fieldId={fieldId}
                userId={user?.id || user?.email}
                  onContextChange={(nextFarmId, nextFieldId, nextField) => {
                    setFarmId(nextFarmId || "");
                    setFieldId(nextFieldId || "");
                    setSelectedField(nextField || null);
                    setSoilTasks([]);
                }}
              />
              <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-6">
                <section className="surface-card min-w-0 p-4 sm:p-5">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                    <div>
                      <span className="section-badge">{t("farmer.workflow")}</span>
                      <h2 className="mt-3 text-xl font-semibold text-text-heading sm:text-2xl">{t("farmer.cropFormTitle")}</h2>
                      <p className="mt-2 max-w-2xl text-sm leading-6 text-text-muted">{t("farmer.cropFormSubtitle")}</p>
                    </div>
                    <button type="button" onClick={fetchWeatherForLocation} disabled={weatherLoading} className="theme-button-secondary w-full whitespace-nowrap px-5 py-3 sm:w-auto">
                      {weatherLoading ? t("farmer.fetchingWeather") : t("farmer.autofillWeather")}
                    </button>
                  </div>

                  <div className="mobile-swipe-row mt-5 grid gap-2 md:grid-cols-4">
                    {Object.entries(CROP_PRESETS).map(([key, preset]) => (
                      <button
                        key={key}
                        type="button"
                        onClick={() => applyPreset(key)}
                        className="mobile-swipe-card surface-card-soft interactive-lift p-2.5 text-left transition-all duration-200 hover:border-accent-300"
                      >
                        <span className="quick-action-icon">{key.slice(0, 2).toUpperCase()}</span>
                        <p className="text-sm font-semibold text-accent-700">{tv("crops", preset.labelKey)}</p>
                        <p className="mt-1 line-clamp-2 text-xs leading-4 text-text-muted">{t(preset.descriptionKey)}</p>
                      </button>
                    ))}
                  </div>

                  <form className="mt-5 space-y-5" onSubmit={handlePredict}>
                    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                      <label className="space-y-2">
                        <span className="text-sm font-medium text-text-heading">{t("farmer.state")}</span>
                        <ThemedSelect
                          value={selectedState}
                          onChange={setSelectedState}
                          options={STATE_OPTIONS.map((stateName) => ({ value: stateName, label: tv("states", stateName) }))}
                        />
                      </label>

                      <label className="space-y-2">
                        <span className="text-sm font-medium text-text-heading">{t("production.plantingDate", "Planting date")}</span>
                        <input type="date" value={plantingDate} onChange={(event) => setPlantingDate(event.target.value)} className="field-shell" />
                      </label>

                      <label className="space-y-2">
                        <span className="text-sm font-medium text-text-heading">{t("farmer.season")}</span>
                        <ThemedSelect
                          value={selectedSeason}
                          onChange={setSelectedSeason}
                          options={SEASON_OPTIONS.map((seasonName) => ({
                            value: seasonName,
                            label: tv("seasons", seasonName),
                          }))}
                        />
                      </label>
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                      {FEATURE_FIELDS.map((field) => {
                        const range = FIELD_RANGES[field];
                        const sliderValue = form[field] === "" ? range.fallback : form[field];

                        return (
                          <label key={field} className="space-y-2 border-b border-surface-border pb-3">
                            <div className="flex items-center justify-between gap-3">
                              <span className="text-sm font-medium text-text-heading">{tv("features", field)}</span>
                              <span className="rounded-full border border-accent-200 bg-accent-50 px-3 py-1 text-xs font-semibold text-accent-800">
                                {form[field] || "-"}
                              </span>
                            </div>
                            <input
                              type="text"
                              value={form[field]}
                              onChange={(event) => handleChange(field, event.target.value)}
                              placeholder={t("farmer.enterField", "Enter {{field}}", { field: tv("features", field) })}
                              className="field-shell"
                            />
                            <input
                              type="range"
                              min={range.min}
                              max={range.max}
                              step={range.step}
                              value={sliderValue}
                              onChange={(event) => handleChange(field, event.target.value)}
                              className="range-shell"
                            />
                            <div className="flex justify-between text-[11px] text-text-subtle">
                              <span>{range.min}</span>
                              <span>{range.max}</span>
                            </div>
                            <p className="text-[11px] leading-4 text-text-subtle">{t(`farmer.helpers.${field}`)}</p>
                          </label>
                        );
                      })}
                    </div>

                    <div className="flex flex-wrap items-center gap-3">
                      <button type="submit" disabled={loading} className="theme-button-primary w-full px-6 py-3 sm:w-auto">
                        {loading ? t("farmer.predicting") : t("farmer.quickPredict")}
                      </button>
                      {loading ? <LoadingSpinner label={t("farmer.runningModels")} /> : null}
                      {!loading && isComplete ? <p className="text-sm text-text-muted">{t("farmer.allInputsReady")}</p> : null}
                    </div>
                  </form>

                  {error ? <p className="mt-5 rounded-2xl border border-danger-100 bg-danger-50 px-4 py-3 text-sm text-danger-700">{error}</p> : null}
                </section>

              </div>

              {result ? (
                <section className="space-y-3">
                  <div className="surface-card p-4">
                    <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
                      <div>
                        <span className="section-badge">{t("farmer.generatedAdvisory")}</span>
                        <p className="mt-2 text-xs leading-5 text-text-muted">{t("farmer.advisorySubtitle")}</p>
                      </div>
                      <div className="flex flex-col gap-2 sm:flex-row">
                        <button type="button" onClick={printAdvisory} className="theme-button-secondary min-h-11 px-4 py-2.5">{t("farmer.printPdf")}</button>
                        <FarmReportButton
                          farmId={farmId}
                          fieldId={fieldId}
                          userId={user?.id || user?.email}
                          result={result}
                          advisory={advisory}
                          predictions={combinedPredictions}
                          tasks={soilTasks}
                          weatherForecast={weatherForecast}
                        />
                      </div>
                    </div>
                  </div>
                  <div className="mobile-sticky-crop-summary" aria-label={t("farmer.currentRecommendation")}>
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-text-subtle">{t("cropCard.recommended")}</p>
                      <p className="mt-1 text-base font-bold capitalize text-primary-800">{tv("crops", result.crop)}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs font-semibold text-accent-700">{Number(result.confidence <= 1 ? result.confidence * 100 : result.confidence).toFixed(1)}%</p>
                      <p className="text-[10px] text-text-subtle">{t("cropCard.confidence")}</p>
                    </div>
                  </div>
                  {result.isLowConfidence ? (
                    <section className="rounded-3xl border border-warning-100 bg-warning-50 p-5">
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div>
                          <span className="section-badge">{t("farmer.reviewRecommendation")}</span>
                          <h3 className="mt-3 text-xl font-semibold text-text-heading">{t("farmer.lowConfidenceTitle")}</h3>
                          <p className="mt-2 max-w-2xl text-sm leading-6 text-text-muted">
                            {result.confidenceNote || "The model still returned the best crop, but the score is below the configured confidence threshold. Compare the alternatives before making a field decision."}
                          </p>
                        </div>
                        <div className="rounded-2xl border border-warning-200 bg-white px-4 py-3 text-sm">
                          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-warning-700">{t("farmer.confidenceThreshold", "Threshold")}</p>
                          <p className="mt-1 font-semibold text-text-heading">
                            {Number((result.confidenceThreshold || 0) * 100).toFixed(0)}%
                          </p>
                        </div>
                      </div>
                      <div className="mt-4 grid gap-3 md:grid-cols-3">
                        {result.topCrops.slice(0, 3).map((item) => (
                          <div key={item.crop} className="surface-card-soft p-3">
                            <p className="text-sm font-semibold capitalize text-text-heading">{tv("crops", item.crop)}</p>
                            <p className="mt-1 text-lg font-bold text-accent-700">{Number(item.confidence * 100).toFixed(1)}%</p>
                          </div>
                        ))}
                      </div>
                    </section>
                  ) : null}
                  <CropCard crop={result.crop} confidence={result.confidence} irrigation={result.irrigation} imageSrc={cropImage} advisory={advisory} />
                </section>
              ) : (
                <section className="surface-card-highlight p-6">
                  <div className="grid gap-5 lg:grid-cols-[0.85fr,1.15fr] lg:items-center">
                    <div>
                      <span className="section-badge">{t("farmer.noAdvisory")}</span>
                      <h3 className="mt-4 text-2xl font-semibold text-text-heading">{t("farmer.firstReportTitle")}</h3>
                      <p className="mt-3 text-sm leading-7 text-text-muted">
                        {t("farmer.firstReportDesc")}
                      </p>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-3">
                      {[t("farmer.fillInputs"), t("farmer.runModel"), t("farmer.downloadReport")].map((step, index) => (
                        <div key={step} className="rounded-2xl border border-surface-border bg-surface-card p-4">
                          <p className="text-[11px] uppercase tracking-[0.2em] text-accent-700">{t("farmer.step")} {index + 1}</p>
                          <p className="mt-2 text-sm font-semibold text-text-heading">{step}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </section>
              )}
            </div>
          ) : null}

          {activeTab === "disease" ? <div className="tab-panel"><DiseaseDetector /></div> : null}
          {activeTab === "market" ? <div className="tab-panel"><MarketInsights stateName={selectedState} season={selectedSeason} crop={marketCrop} /></div> : null}
          {activeTab === "soil" ? (
            <div className="tab-panel space-y-6">
              <ProductionOutlookCard outlook={advisory?.production_outlook} />
              <WeatherSignals forecast={weatherForecast} />
              <PestOutbreakCard forecast={pestForecast} loading={pestLoading} status={pestForecastStatus} />
              <FieldTimeline
                irrigation={advisory?.irrigation}
                pestForecast={pestForecast}
                harvest={advisory?.production_outlook?.harvest_window}
                weatherForecast={weatherForecast}
                soilTasks={soilTasks}
                onCompleteTask={completeSoilTask}
                onOpenItem={openTimelineItem}
              />
              <SoilRestorationCard plan={advisory?.soil_restoration} onStart={() => setActiveTab("crop")} />
              <SoilPlanningWorkspace
                farmId={farmId}
                fieldId={fieldId}
                proposal={advisory?.soil_restoration}
                plantingDate={plantingDate}
                onOpenFarm={() => setActiveTab("crop")}
                tasks={soilTasks}
                predictions={combinedPredictions}
                onTasksChange={setSoilTasks}
              />
            </div>
          ) : null}
          {activeTab === "ai" ? <div className="tab-panel"><AskAiAssistant context={aiContext} /></div> : null}

          <div className={activeTab === "alerts" ? "tab-panel" : "hidden"}>
            <AlertsCenter farmId={farmId} userId={user?.id} onOpenModule={setActiveTab} onDueCountChange={setFarmDueCount} />
          </div>

          {activeTab === "history" ? (
            <section className="surface-card tab-panel min-w-0 p-4 sm:p-6">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <span className="section-badge">{t("farmer.historyEyebrow")}</span>
                  <h2 className="mt-2 text-xl font-semibold text-text-heading sm:text-2xl">{t("farmer.historyTitle")}</h2>
                </div>
                <p className="text-sm text-text-muted">{t("farmer.historySubtitle")}</p>
              </div>

              {!historyLoading ? <div className="mt-6 min-w-0"><PredictionComparison rows={combinedPredictions} /></div> : null}

              {historyLoading ? (
                <div className="mt-6">
                  <LoadingSkeleton cards={4} rows={2} label={t("farmer.recentPredictions")} className="lg:grid-cols-2" />
                </div>
              ) : (
                <div className="mt-6 grid gap-3 lg:grid-cols-2">
                  {combinedPredictions.slice(0, 8).map((row, index) => (
                    <div key={`${row.ids?.join("-") || row.id || index}`} className="surface-card-soft interactive-lift p-4 transition-all duration-200 hover:border-accent-200">
                      <p className="text-xs tabular-nums text-text-subtle">{formatHistoryDate(row.timestamp, language)}</p>
                      <div className="mt-4 grid gap-3 sm:grid-cols-2">
                        <div>
                          <p className="text-xs text-text-subtle">{t("farmer.crop")}</p>
                          <p className="mt-1 text-lg font-semibold capitalize text-accent-700">{row.crop_prediction ? tv("crops", row.crop_prediction) : "-"}</p>
                        </div>
                        <div>
                          <p className="text-xs text-text-subtle">{t("farmer.irrigation")}</p>
                          <p className="mt-1 text-lg font-semibold text-text-heading">
                            {row.irrigation_prediction !== null && row.irrigation_prediction !== undefined ? Number(row.irrigation_prediction).toFixed(4) : "-"}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                  {!combinedPredictions.length ? (
                    <div className="col-span-full">
                      <EmptyState
                        title={t("farmer.noPredictions")}
                        description={t("farmer.historyEmptyDesc")}
                        action={<button type="button" onClick={() => setActiveTab("crop")} className="theme-button-primary px-4 py-2.5">{t("farmer.startPrediction")}</button>}
                      />
                    </div>
                  ) : null}
                </div>
              )}
            </section>
          ) : null}
        </section>
      </div>
    </main>
  );
}

export default FarmerDashboard;
