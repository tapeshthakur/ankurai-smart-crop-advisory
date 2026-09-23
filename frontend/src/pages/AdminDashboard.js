import React, { useEffect, useMemo, useState } from "react";
import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Tooltip,
} from "chart.js";
import { Bar, Doughnut } from "react-chartjs-2";
import api from "../api/client";
import { useAuth } from "../auth/AuthContext";
import LoadingSkeleton from "../components/LoadingSkeleton";
import LoadingSpinner from "../components/LoadingSpinner";
import MetricCard from "../components/MetricCard";
import Sidebar from "../components/Sidebar";
import { useLanguage } from "../i18n/LanguageContext";

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend);

function pickMetric(source, keys) {
  for (const key of keys) {
    if (typeof source?.[key] === "number") {
      return source[key];
    }
  }
  return 0;
}

function formatImportance(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

function formatPercent(value) {
  return `${(Number(value || 0) * 100).toFixed(2)}%`;
}

function formatDiseaseClassName(name) {
  return String(name || "")
    .replaceAll("___", " - ")
    .replaceAll("__", " ")
    .replaceAll("_", " ")
    .trim();
}

const HISTORY_PAIR_WINDOW_MS = 10000;

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
    const userKey = row.user_id ?? "unknown";
    const match = groups.find((group) => {
      if (group.inputKey !== inputKey || group.userKey !== userKey) return false;
      if (!Number.isFinite(timestampMs) || !Number.isFinite(group.timestampMs)) return false;
      return Math.abs(group.timestampMs - timestampMs) <= HISTORY_PAIR_WINDOW_MS;
    });

    if (match) {
      match.crop_prediction = match.crop_prediction || row.crop_prediction;
      match.irrigation_prediction = match.irrigation_prediction ?? row.irrigation_prediction;
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

function AdminDashboard() {
  const { user } = useAuth();
  const { language, t, tv } = useLanguage();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [stats, setStats] = useState({ total_predictions: 0, user_count: 0 });
  const [modelInfo, setModelInfo] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [activeAdminTab, setActiveAdminTab] = useState("crop");

  useEffect(() => {
    const fetchAdminData = async () => {
      try {
        setLoading(true);
        setError("");

        const [statsRes, modelRes, predictionsRes] = await Promise.all([
          api.get("/api/admin/stats"),
          api.get("/api/model-info"),
          api.get("/api/predictions"),
        ]);

        setStats(statsRes.data || { total_predictions: 0, user_count: 0 });
        setModelInfo(modelRes.data || null);
        setPredictions(predictionsRes.data.predictions || []);
      } catch (err) {
        setError(err.response?.data?.error || t("admin.failed"));
      } finally {
        setLoading(false);
      }
    };

    fetchAdminData();
  }, []);

  const classifier = modelInfo?.classifier_metrics || {};
  const regressor = modelInfo?.regressor_metrics || {};
  const disease = modelInfo?.disease_metrics || {};
  const classifierImportance = modelInfo?.classifier_feature_importance || [];
  const regressorImportance = modelInfo?.regressor_feature_importance || [];
  const artifacts = modelInfo?.artifacts || {};
  const combinedPredictions = useMemo(() => mergePredictionHistory(predictions), [predictions]);
  const adminTabs = useMemo(
    () => [
      { id: "crop", eyebrow: "Crop", label: "Crop Advisory" },
      { id: "disease", eyebrow: "Leaf", label: "Leaf Detection" },
    ],
    []
  );

  const metricData = useMemo(() => {
    const accuracy = pickMetric(classifier, ["test_accuracy", "cv_accuracy_mean"]);
    const f1 = pickMetric(classifier, ["test_f1_weighted", "cv_f1_weighted_mean", "test_f1"]);
    const mae = pickMetric(regressor, ["test_mae", "cv_mae_mean"]);
    const r2 = pickMetric(regressor, ["test_r2", "cv_r2_mean"]);

    return { accuracy, f1, mae, r2 };
  }, [classifier, regressor]);

  const diseaseSummary = useMemo(() => {
    const classDistribution = disease.class_distribution || {};
    const weakClasses = Object.entries(disease.weak_classes_below_0_75 || {}).sort((a, b) => a[1] - b[1]);
    const perClassAccuracy = Object.entries(disease.per_class_validation_accuracy || {})
      .map(([name, score]) => ({
        name,
        label: formatDiseaseClassName(name),
        score: Number(score || 0),
        samples: Number(classDistribution[name] || 0),
      }))
      .sort((a, b) => a.score - b.score);
    const strongestClasses = [...perClassAccuracy].sort((a, b) => b.score - a.score).slice(0, 3);

    return {
      accuracy: Number(disease.validation_accuracy || 0),
      macroF1: Number(disease.macro_avg_f1 || 0),
      weightedF1: Number(disease.weighted_avg_f1 || 0),
      classes: Number(disease.classes || Object.keys(classDistribution).length || 0),
      imageCount: Object.values(classDistribution).reduce((sum, count) => sum + Number(count || 0), 0),
      weakClasses,
      perClassAccuracy,
      weakestClasses: perClassAccuracy.slice(0, 3),
      strongestClasses,
      trainedAt: disease.trained_at || "",
    };
  }, [disease]);

  const cropSummary = useMemo(() => {
    const counters = {};
    combinedPredictions.forEach((item) => {
      const key = item.crop_prediction?.trim();
      if (!key) return;
      counters[key] = (counters[key] || 0) + 1;
    });

    const ordered = Object.entries(counters).sort((a, b) => b[1] - a[1]);

    return {
      labels: ordered.map(([label]) => label),
      values: ordered.map(([, value]) => value),
      topCrop: ordered[0]?.[0] || t("admin.noCropData"),
      topCount: ordered[0]?.[1] || 0,
    };
  }, [combinedPredictions, t]);

  const recentPredictions = useMemo(
    () => combinedPredictions.filter((item) => item.crop_prediction || item.irrigation_prediction !== null).slice(0, 6),
    [combinedPredictions]
  );

  const metricInsights = useMemo(() => {
    const formatted = [
      { key: "accuracy", label: t("admin.accuracy"), value: metricData.accuracy, better: "higher" },
      { key: "f1", label: t("admin.f1"), value: metricData.f1, better: "higher" },
      { key: "mae", label: t("admin.mae"), value: metricData.mae, better: "lower" },
      { key: "r2", label: t("admin.r2"), value: metricData.r2, better: "higher" },
    ];
    const higherMetrics = formatted.filter((item) => item.better === "higher");
    const bestMetric = [...higherMetrics].sort((a, b) => b.value - a.value)[0] || formatted[0];
    const reviewMetric = [...formatted].sort((a, b) => {
      const left = a.better === "lower" ? a.value : 1 - a.value;
      const right = b.better === "lower" ? b.value : 1 - b.value;
      return right - left;
    })[0] || formatted[0];

    return { formatted, bestMetric, reviewMetric };
  }, [metricData, t]);

  const barData = {
    labels: [t("admin.accuracy"), t("admin.f1"), t("admin.mae"), t("admin.r2")],
    datasets: [
      {
        label: t("admin.modelMetrics"),
        data: [metricData.accuracy, metricData.f1, metricData.mae, metricData.r2],
        backgroundColor: ["#2F5233", "#6F9172", "#C89B3C", "#E0B96D"],
        borderRadius: 14,
        borderSkipped: false,
        maxBarThickness: 48,
      },
    ],
  };

  const doughnutData = {
    labels: cropSummary.labels.map((label) => tv("crops", label)),
    datasets: [
      {
        data: cropSummary.values,
        backgroundColor: ["#2F5233", "#4F704F", "#91B394", "#C89B3C", "#E0B96D", "#8F6E24"],
        borderColor: "#FFFDF8",
        borderWidth: 3,
        hoverOffset: 8,
      },
    ],
  };

  const artifactRows = [
    { key: "classifier_model", label: t("admin.classifierModel"), value: artifacts.classifier_model },
    { key: "regressor_model", label: t("admin.regressorModel"), value: artifacts.regressor_model },
    { key: "classifier_metrics", label: t("admin.classifierMetrics"), value: artifacts.classifier_metrics },
    { key: "regressor_metrics", label: t("admin.regressorMetrics"), value: artifacts.regressor_metrics },
    { key: "disease_model", label: "Disease CNN model", value: artifacts.disease_model },
    { key: "disease_training_report", label: "Disease training report", value: artifacts.disease_training_report },
  ].filter((item) => item.value?.file);

  const dateLocale = language === "mr" ? "mr-IN" : language === "hi" ? "hi-IN" : "en-IN";

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        labels: {
          color: "#2A2A26",
          boxWidth: 14,
          usePointStyle: true,
          pointStyle: "circle",
          padding: 18,
        },
      },
      tooltip: {
        backgroundColor: "#1F3A22",
        borderColor: "rgba(200, 155, 60, 0.35)",
        borderWidth: 1,
        titleColor: "#FAF7F0",
        bodyColor: "#F5F1E8",
      },
    },
    scales: {
      x: {
        ticks: { color: "#6B665C" },
        grid: { display: false },
      },
      y: {
        ticks: { color: "#6B665C" },
        grid: { display: false },
      },
    },
  };

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="grid gap-6 lg:grid-cols-[285px,1fr]">
        <Sidebar role={user?.role} moduleItems={adminTabs} activeModule={activeAdminTab} onModuleChange={setActiveAdminTab} />

        <section className="space-y-6">
          <div className="app-shell ambient-grid">
            <div className="relative z-10 grid gap-6 xl:grid-cols-[1.2fr,0.8fr] xl:items-end">
              <div>
                <span className="section-badge">{t("admin.heroBadge")}</span>
                <h1 className="mt-4 text-4xl font-bold leading-tight text-text-heading sm:text-5xl">{t("admin.title")}</h1>
                <p className="mt-4 max-w-2xl text-base leading-7 text-text-muted">{t("admin.subtitle")}</p>
                <div className="mt-6 flex flex-wrap gap-3 text-sm">
                  <span className="rounded-full border border-surface-border bg-surface-card px-4 py-2 text-text-muted">{t("admin.currentUser")}: {user?.name}</span>
                  <span className="rounded-full border border-accent-300 bg-accent-50 px-4 py-2 text-accent-700">{t("admin.topCropTracked")}: {tv("crops", cropSummary.topCrop)}</span>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <MetricCard title={t("admin.totalPredictions")} value={stats.total_predictions || 0} subtitle={t("admin.totalPredictionsSubtitle")} accent="primary" />
                <MetricCard title={t("admin.userCount")} value={stats.user_count || 0} subtitle={t("admin.userCountSubtitle")} accent="success" />
                <MetricCard title={t("admin.accuracy")} value={metricData.accuracy.toFixed(4)} subtitle={t("admin.accuracySubtitle")} accent="accent" />
                <MetricCard title={t("admin.f1")} value={metricData.f1.toFixed(4)} subtitle={t("admin.f1Subtitle")} accent="primary" />
              </div>
            </div>
          </div>

          {loading ? (
            <div className="space-y-6">
              <LoadingSpinner label={t("admin.loading")} />
              <LoadingSkeleton cards={4} rows={2} className="sm:grid-cols-2 lg:grid-cols-4" />
              <LoadingSkeleton cards={2} rows={4} className="xl:grid-cols-2" />
            </div>
          ) : null}
          {error ? <p className="rounded-2xl border border-danger-100 bg-danger-50 px-4 py-3 text-sm text-danger-700">{error}</p> : null}

          {!loading && !error ? (
            <>
              {activeAdminTab === "crop" ? (
                <div className="grid gap-4 lg:grid-cols-3">
                  <MetricCard title={t("admin.topPredictedCrop")} value={tv("crops", cropSummary.topCrop)} subtitle={t("admin.savedPredictions", undefined, { count: cropSummary.topCount })} accent="primary" />
                  <MetricCard title={t("admin.regressionMae")} value={metricData.mae.toFixed(4)} subtitle={t("admin.regressionMaeSubtitle")} accent="accent" />
                  <MetricCard title={t("admin.regressionR2")} value={metricData.r2.toFixed(4)} subtitle={t("admin.regressionR2Subtitle")} accent="success" />
                </div>
              ) : null}

              {activeAdminTab === "disease" && diseaseSummary.accuracy ? (
                <div className="chart-shell">
                  <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                    <div>
                      <span className="section-badge">Disease CNN</span>
                      <h2 className="mt-4 text-2xl font-semibold text-text-heading">Leaf disease model performance</h2>
                    </div>
                    <p className="text-sm text-text-muted">
                      MobileNetV2 validation results from the latest training report.
                    </p>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    <MetricCard title="Disease accuracy" value={formatPercent(diseaseSummary.accuracy)} subtitle="Validation accuracy" accent="primary" />
                    <MetricCard title="Macro F1" value={formatPercent(diseaseSummary.macroF1)} subtitle="Class-balanced score" accent="success" />
                    <MetricCard title="Dataset images" value={diseaseSummary.imageCount.toLocaleString("en-IN")} subtitle={`${diseaseSummary.classes} disease classes`} accent="accent" />
                    <MetricCard title="Weighted F1" value={formatPercent(diseaseSummary.weightedF1)} subtitle="Weighted by class support" accent="primary" />
                  </div>

                  <div className="mt-5 rounded-[1.5rem] border border-surface-border bg-surface-card p-4">
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                      <div>
                        <p className="text-[11px] uppercase tracking-[0.2em] text-accent-700">Review focus</p>
                        <p className="mt-2 text-sm leading-6 text-text-muted">
                          {diseaseSummary.weakClasses.length
                            ? "Classes below 75% validation accuracy are highlighted for future retraining."
                            : "No disease class is below the 75% validation accuracy threshold."}
                        </p>
                      </div>
                      {diseaseSummary.trainedAt ? (
                        <p className="text-xs text-text-subtle">Trained: {new Date(diseaseSummary.trainedAt).toLocaleString(dateLocale)}</p>
                      ) : null}
                    </div>

                    {diseaseSummary.weakClasses.length ? (
                      <div className="mt-4 grid gap-3 md:grid-cols-2">
                        {diseaseSummary.weakClasses.map(([className, score]) => (
                          <div key={className} className="rounded-2xl border border-accent-200 bg-warning-50 p-3">
                            <p className="break-words text-sm font-semibold text-warning-700">{formatDiseaseClassName(className)}</p>
                            <p className="mt-1 text-xs text-text-muted">{formatPercent(score)} validation accuracy</p>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </div>
              ) : null}

              {activeAdminTab === "disease" && diseaseSummary.perClassAccuracy.length ? (
                <div className="chart-shell">
                  <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                    <div>
                      <span className="section-badge">Leaf Detection</span>
                      <h2 className="mt-4 text-2xl font-semibold text-text-heading">Leaf detection analytics</h2>
                    </div>
                    <p className="max-w-xl text-sm leading-6 text-text-muted">
                      Class-wise validation view for the uploaded leaf image detector.
                    </p>
                  </div>

                  <div className="grid gap-6 xl:grid-cols-[1.15fr,0.85fr]">
                    <div className="rounded-[1.5rem] border border-surface-border bg-surface-card p-4">
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <p className="text-[11px] uppercase tracking-[0.2em] text-accent-700">Disease classes</p>
                          <h3 className="mt-2 text-lg font-semibold text-text-heading">Accuracy ranking</h3>
                        </div>
                        <p className="text-xs text-text-subtle">{diseaseSummary.classes} classes tracked</p>
                      </div>

                      <div className="mt-5 space-y-3">
                        {diseaseSummary.perClassAccuracy.map((item) => {
                          const percent = Math.max(0, Math.min(100, item.score * 100));
                          const barColor = item.score < 0.75 ? "bg-accent-300" : item.score < 0.9 ? "bg-accent-500" : "bg-primary-400";

                          return (
                            <div key={item.name} className="space-y-2">
                              <div className="flex items-start justify-between gap-3 text-sm">
                                <div className="min-w-0">
                                  <p className="break-words font-medium text-text-heading">{item.label}</p>
                                  <p className="mt-1 text-xs text-text-subtle">{item.samples.toLocaleString("en-IN")} training images</p>
                                </div>
                                <span className="shrink-0 font-semibold text-accent-800">{formatPercent(item.score)}</span>
                              </div>
                              <div className="h-2.5 overflow-hidden rounded-full bg-primary-100">
                                <div
                                  className={`h-full rounded-full ${barColor}`}
                                  style={{ width: `${Math.max(3, percent)}%` }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div className="rounded-[1.5rem] border border-accent-200 bg-accent-50 p-4">
                        <p className="text-[11px] uppercase tracking-[0.2em] text-accent-700">Detection readiness</p>
                        <div className="mt-4 grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
                          <div>
                            <p className="text-xs text-text-subtle">Overall accuracy</p>
                            <p className="mt-1 text-2xl font-semibold text-text-heading">{formatPercent(diseaseSummary.accuracy)}</p>
                          </div>
                          <div>
                            <p className="text-xs text-text-subtle">Dataset coverage</p>
                            <p className="mt-1 text-2xl font-semibold text-text-heading">{diseaseSummary.imageCount.toLocaleString("en-IN")}</p>
                          </div>
                          <div>
                            <p className="text-xs text-text-subtle">Below 75%</p>
                            <p className="mt-1 text-2xl font-semibold text-text-heading">{diseaseSummary.weakClasses.length}</p>
                          </div>
                        </div>
                      </div>

                      <div className="rounded-[1.5rem] border border-accent-200 bg-warning-50 p-4">
                        <p className="text-[11px] uppercase tracking-[0.2em] text-accent-700">Needs attention</p>
                        <div className="mt-4 space-y-3">
                          {diseaseSummary.weakestClasses.map((item) => (
                            <div key={`weak-${item.name}`} className="flex items-start justify-between gap-3">
                              <p className="min-w-0 break-words text-sm font-medium text-amber-50">{item.label}</p>
                              <span className="shrink-0 text-sm font-semibold text-warning-700">{formatPercent(item.score)}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="rounded-[1.5rem] border border-surface-border bg-surface-card p-4">
                        <p className="text-[11px] uppercase tracking-[0.2em] text-text-muted">Best detected</p>
                        <div className="mt-4 space-y-3">
                          {diseaseSummary.strongestClasses.map((item) => (
                            <div key={`strong-${item.name}`} className="flex items-start justify-between gap-3">
                              <p className="min-w-0 break-words text-sm font-medium text-text-heading">{item.label}</p>
                              <span className="shrink-0 text-sm font-semibold text-accent-800">{formatPercent(item.score)}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="rounded-[1.5rem] border border-surface-border bg-surface-muted p-4">
                        <p className="text-[11px] uppercase tracking-[0.2em] text-text-muted">Next training cue</p>
                        <p className="mt-3 text-sm leading-6 text-text-muted">
                          Add more clean, well-lit samples for weak classes before the next retraining cycle.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}

              {activeAdminTab === "disease" && !diseaseSummary.accuracy && !diseaseSummary.perClassAccuracy.length ? (
                <div className="chart-shell">
                  <span className="section-badge">Leaf Detection</span>
                  <h2 className="mt-4 text-2xl font-semibold text-text-heading">Leaf disease model not found</h2>
                  <p className="mt-3 text-sm leading-6 text-text-muted">
                    Train the leaf disease model once and the Disease CNN metrics will appear here.
                  </p>
                </div>
              ) : null}

              {activeAdminTab === "crop" ? (
              <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
                <div className="chart-shell">
                  <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                    <div>
                      <span className="section-badge">{t("admin.modelMetrics")}</span>
                      <h2 className="mt-4 text-2xl font-semibold text-text-heading">{t("admin.modelOverview")}</h2>
                    </div>
                    <p className="text-sm text-text-muted">{t("admin.modelOverviewDesc")}</p>
                  </div>
                  <Bar data={barData} options={chartOptions} />
                  <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    {metricInsights.formatted.map((metric) => (
                      <div key={metric.key} className="chart-legend-card">
                        <p className="text-[11px] uppercase tracking-[0.2em] text-text-subtle">{metric.label}</p>
                        <p className="mt-2 text-xl font-semibold text-text-heading">{metric.value.toFixed(4)}</p>
                        <p className="mt-1 text-xs text-text-subtle">{metric.better === "lower" ? t("admin.lowerBetter") : t("admin.higherBetter")}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="chart-shell">
                  <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                    <div>
                      <span className="section-badge">{t("admin.cropDistribution")}</span>
                      <h2 className="mt-4 text-2xl font-semibold text-text-heading">{t("admin.cropShare")}</h2>
                    </div>
                    <p className="text-sm text-text-muted">{t("admin.irrigationExcluded")}</p>
                  </div>

                  {cropSummary.labels.length ? (
                    <>
                      <div className="mx-auto max-w-[360px]">
                        <Doughnut
                          data={doughnutData}
                          options={{
                            cutout: "62%",
                            plugins: {
                              legend: {
                                labels: {
                                  color: "#2A2A26",
                                  boxWidth: 14,
                                  usePointStyle: true,
                                  pointStyle: "circle",
                                  padding: 16,
                                },
                              },
                            },
                          }}
                        />
                      </div>
                      <div className="mt-5 rounded-[1.5rem] border border-accent-200 bg-accent-50 p-4">
                        <p className="text-[11px] uppercase tracking-[0.22em] text-accent-700">{t("admin.topRecommendation")}</p>
                        <p className="mt-2 text-xl font-semibold capitalize text-text-heading">{tv("crops", cropSummary.topCrop)}</p>
                        <p className="mt-2 text-sm text-text-muted">{t("admin.distributionLead", undefined, { count: cropSummary.topCount })}</p>
                      </div>
                      <div className="mt-3 grid gap-3 sm:grid-cols-2">
                        <div className="chart-legend-card">
                          <p className="text-[11px] uppercase tracking-[0.2em] text-accent-700">{t("admin.strongestMetric")}</p>
                          <p className="mt-2 text-lg font-semibold text-text-heading">{metricInsights.bestMetric.label}</p>
                          <p className="mt-1 text-sm text-text-muted">{metricInsights.bestMetric.value.toFixed(4)}</p>
                        </div>
                        <div className="chart-legend-card">
                          <p className="text-[11px] uppercase tracking-[0.2em] text-accent-700">{t("admin.reviewMetric")}</p>
                          <p className="mt-2 text-lg font-semibold text-text-heading">{metricInsights.reviewMetric.label}</p>
                          <p className="mt-1 text-sm text-text-muted">{t("admin.improvementScope")}</p>
                        </div>
                      </div>
                    </>
                  ) : (
                    <p className="text-sm text-text-muted">{t("admin.noPredictionData")}</p>
                  )}
                </div>
              </div>
              ) : null}

              {activeAdminTab === "crop" ? (
              <>
              <div className="chart-shell">
                <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <span className="section-badge">{t("admin.featureImportance")}</span>
                    <h2 className="mt-4 text-2xl font-semibold text-text-heading">{t("admin.explainability")}</h2>
                  </div>
                  <p className="max-w-xl text-sm text-text-muted">{t("admin.featureImportanceDesc")}</p>
                </div>

                <div className="grid gap-5 lg:grid-cols-2">
                  {[
                    { title: t("admin.classifierDrivers"), data: classifierImportance },
                    { title: t("admin.regressorDrivers"), data: regressorImportance },
                  ].map((group) => (
                    <div key={group.title} className="rounded-[1.5rem] border border-surface-border bg-surface-card p-4">
                      <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-accent-700">{group.title}</h3>
                      <div className="mt-4 space-y-3">
                        {group.data.length ? (
                          group.data.map((item) => (
                            <div key={`${group.title}-${item.feature}`} className="space-y-2">
                              <div className="flex items-center justify-between gap-3 text-sm">
                                <span className="font-medium text-text-heading">{tv("features", item.feature)}</span>
                                <span className="text-text-muted">{formatImportance(item.importance)}</span>
                              </div>
                              <div className="h-2 overflow-hidden rounded-full bg-primary-100">
                                <div
                                  className="h-full rounded-full bg-accent-500"
                                  style={{ width: `${Math.min(100, Number(item.importance || 0) * 100)}%` }}
                                />
                              </div>
                            </div>
                          ))
                        ) : (
                          <p className="text-sm text-text-muted">{t("admin.noArtifactData")}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-5 rounded-[1.5rem] border border-accent-200 bg-accent-50 p-4">
                  <p className="text-[11px] uppercase tracking-[0.22em] text-accent-700">{t("admin.modelArtifacts")}</p>
                  <h3 className="mt-2 text-lg font-semibold text-text-heading">{t("admin.activeModels")}</h3>
                  <div className="mt-4 grid gap-3 lg:grid-cols-2">
                    {artifactRows.length ? (
                      artifactRows.map((item) => (
                        <div key={item.key} className="rounded-2xl border border-surface-border bg-surface-card p-3">
                          <p className="text-xs text-text-subtle">{item.label}</p>
                          <p className="mt-1 break-all text-sm font-semibold text-text-heading">{item.value.file}</p>
                          <p className="mt-2 text-xs text-text-subtle">
                            {t("admin.artifactUpdated")}:{" "}
                            {item.value.updated_at ? new Date(item.value.updated_at * 1000).toLocaleString(dateLocale) : "-"} |{" "}
                            {t("admin.artifactSize")}: {item.value.size_kb} KB
                          </p>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-text-muted">{t("admin.noArtifactData")}</p>
                    )}
                  </div>
                </div>
              </div>

              <div className="chart-shell">
                <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <span className="section-badge">{t("admin.recentActivity")}</span>
                    <h2 className="mt-4 text-2xl font-semibold text-text-heading">{t("admin.latestPredictions")}</h2>
                  </div>
                  <p className="text-sm text-text-muted">{t("admin.activitySubtitle")}</p>
                </div>

                <div className="overflow-x-auto rounded-[1.4rem] border border-surface-border bg-surface-card">
                  <div className="min-w-[540px]">
                  <div className="grid grid-cols-[1.2fr,0.9fr,0.8fr] gap-3 border-b border-surface-border px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-subtle">
                    <span>{t("admin.recentEntry")}</span>
                    <span>{t("admin.crop")}</span>
                    <span className="text-right">{t("admin.irrigation")}</span>
                  </div>
                  {recentPredictions.map((item, index) => (
                    <div
                      key={`${item.ids?.join("-") || item.id || index}`}
                      className="grid grid-cols-[1.2fr,0.9fr,0.8fr] items-center gap-3 border-b border-surface-border px-4 py-3 last:border-b-0"
                    >
                      <p className="min-w-0 truncate text-xs text-text-muted" title={item.timestamp || ""}>
                        {item.timestamp || t("admin.recentEntry")}
                      </p>
                      <p className="min-w-0 truncate text-sm font-semibold capitalize text-accent-700">
                        {item.crop_prediction ? tv("crops", item.crop_prediction) : "-"}
                      </p>
                      <p className="text-right text-sm font-semibold text-text-heading">
                        {item.irrigation_prediction !== null && item.irrigation_prediction !== undefined
                          ? Number(item.irrigation_prediction).toFixed(4)
                          : "-"}
                      </p>
                    </div>
                  ))}
                  {!recentPredictions.length ? <p className="px-4 py-4 text-sm text-text-muted">{t("admin.noPredictionData")}</p> : null}
                  </div>
                </div>
              </div>
              </>
              ) : null}
            </>
          ) : null}
        </section>
      </div>
    </main>
  );
}

export default AdminDashboard;
