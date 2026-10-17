import React, { useEffect, useMemo, useState } from "react";
import { BarElement, CategoryScale, Chart as ChartJS, LineElement, LinearScale, PointElement, Tooltip } from "chart.js";
import { Bar, Line } from "react-chartjs-2";
import { ExternalLink, MapPin, Search, TrendingUp } from "lucide-react";
import api from "../api/client";
import LoadingSpinner from "./LoadingSpinner";
import { useLanguage } from "../i18n/LanguageContext";

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Tooltip);

function MarketInsights({ stateName, season, crop }) {
  const { t, tv, language } = useLanguage();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retryCount, setRetryCount] = useState(0);
  const [district, setDistrict] = useState("all");
  const [market, setMarket] = useState("all");
  const [schemeCategory, setSchemeCategory] = useState("all");
  const [schemeSearch, setSchemeSearch] = useState("");
  const [mspChecks, setMspChecks] = useState({ procurement: false, registration: false, quality: false });
  const [mspVariant, setMspVariant] = useState("common");
  const [showTrend, setShowTrend] = useState(false);
  const [trend, setTrend] = useState([]);
  const [trendLoading, setTrendLoading] = useState(false);
  const [trendError, setTrendError] = useState("");
  const locale = language === "hi" ? "hi-IN" : language === "mr" ? "mr-IN" : "en-IN";

  useEffect(() => {
    const controller = new AbortController();
    const load = async () => {
      try {
        setLoading(true);
        setError("");
        const response = await api.get("/api/market/overview", {
          params: { state: stateName, season, crop }, timeout: 18000, signal: controller.signal,
        });
        if (!response.data?.mandi || !response.data?.msp) throw new Error("Market response is incomplete");
        setData(response.data);
      } catch (err) {
        if (!controller.signal.aborted) setError(err.response?.data?.error || t("market.failed"));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    };
    load();
    return () => controller.abort();
  }, [stateName, season, crop, retryCount, t]);

  useEffect(() => {
    setDistrict("all");
    setMarket("all");
    setMspChecks({ procurement: false, registration: false, quality: false });
    setMspVariant("common");
    setTrend([]);
  }, [stateName, season, crop]);

  useEffect(() => {
    const variants = data?.msp?.variants || [];
    if (variants.length && !variants.some((item) => item.id === mspVariant)) setMspVariant(variants[0].id);
  }, [data, mspVariant]);

  useEffect(() => {
    if (!showTrend) return undefined;
    const controller = new AbortController();
    const load = async () => {
      setTrendLoading(true);
      setTrendError("");
      try {
        const response = await api.get("/api/market/trends", {
          params: { state: stateName, crop, district: district === "all" ? "" : district, market: market === "all" ? "" : market },
          timeout: 16000, signal: controller.signal,
        });
        setTrend(response.data?.records || []);
        if (!response.data?.records?.length) setTrendError(response.data?.message || t("market.trendEmpty"));
      } catch (err) {
        if (!controller.signal.aborted) setTrendError(err.response?.data?.error || t("market.trendFailed"));
      } finally {
        if (!controller.signal.aborted) setTrendLoading(false);
      }
    };
    load();
    return () => controller.abort();
  }, [showTrend, stateName, crop, district, market, t]);

  const activeCrop = data?.crop || crop;
  const activeSeason = data?.season || season;
  const allRows = data?.mandi?.records || [];
  const districtOptions = [...new Set(allRows.map((row) => row.district).filter(Boolean))].sort((a, b) => a.localeCompare(b));
  const districtRows = district === "all" ? allRows : allRows.filter((row) => row.district === district);
  const marketOptions = [...new Set(districtRows.map((row) => row.market).filter(Boolean))].sort((a, b) => a.localeCompare(b));
  const selectedRows = market === "all" ? districtRows : districtRows.filter((row) => row.market === market);
  const marketPrices = [...selectedRows.reduce((result, row) => {
    const price = Number(row.modal_price);
    if (!Number.isFinite(price)) return result;
    const name = row.market || row.district || row.state || t("market.marketName");
    const current = result.get(name) || { total: 0, count: 0 };
    current.total += price;
    current.count += 1;
    result.set(name, current);
    return result;
  }, new Map())].map(([name, value]) => ({ name, price: value.total / value.count }))
    .sort((a, b) => b.price - a.price).slice(0, 8);
  const currentPrice = marketPrices.length ? marketPrices.reduce((sum, row) => sum + row.price, 0) / marketPrices.length : null;
  const marketIsLive = Boolean(data?.mandi?.is_live && selectedRows.length);
  const currentMsp = data?.msp?.variants?.find((item) => item.id === mspVariant)?.value ?? data?.msp?.value;
  const readyCount = Object.values(mspChecks).filter(Boolean).length;
  const rupee = String.fromCharCode(0x20b9);

  const comparisonData = useMemo(() => ({
    labels: marketPrices.map((item) => item.name),
    datasets: [{
      label: t("market.modalPrice", "Modal price"), data: marketPrices.map((item) => item.price),
      backgroundColor: marketPrices.map((_, index) => index === 0 ? "#2F5233" : "#86A58A"),
      borderRadius: 3, barThickness: 20,
    }],
  }), [marketPrices, t]);
  const trendData = useMemo(() => ({
    labels: trend.map((item) => new Date(`${item.date}T00:00:00`).toLocaleDateString(locale, { day: "numeric", month: "short" })),
    datasets: [{ label: t("market.modalPrice", "Modal price"), data: trend.map((item) => item.average_modal_price), borderColor: "#2F5233", backgroundColor: "rgba(47,82,51,.12)", borderWidth: 2.5, pointRadius: 3, pointHoverRadius: 5, tension: 0.25, spanGaps: false }],
  }), [trend, locale, t]);
  const chartOptions = useMemo(() => ({
    indexAxis: "y", maintainAspectRatio: false, responsive: true,
    plugins: { legend: { display: false }, tooltip: { callbacks: { label: (context) => `${rupee}${Number(context.raw).toLocaleString(locale)} / ${t("market.quintal")}` } } },
    scales: {
      x: { beginAtZero: true, grid: { color: "rgba(95,108,97,.12)" }, ticks: { color: "#5F6C61", callback: (value) => Number(value).toLocaleString(locale) } },
      y: { grid: { display: false }, ticks: { color: "#445248", font: { size: 11, weight: 600 } } },
    },
  }), [locale, t]);
  const trendOptions = useMemo(() => ({
    maintainAspectRatio: false, responsive: true,
    plugins: { legend: { display: false }, tooltip: { callbacks: { label: (context) => `${rupee}${Number(context.raw).toLocaleString(locale)} / ${t("market.quintal")}` } } },
    scales: { x: { grid: { display: false }, ticks: { color: "#5F6C61" } }, y: { beginAtZero: false, grid: { color: "rgba(95,108,97,.12)" }, ticks: { color: "#5F6C61", callback: (value) => Number(value).toLocaleString(locale) } } },
  }), [locale, t]);
  const schemes = (data?.schemes || []).filter((scheme) => {
    const matchesCategory = schemeCategory === "all" || scheme.category === schemeCategory;
    const query = schemeSearch.trim().toLowerCase();
    return matchesCategory && (!query || `${scheme.name} ${scheme.benefit} ${scheme.eligibility}`.toLowerCase().includes(query));
  });
  const formatDate = (value) => {
    if (!value) return "-";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(locale, { day: "numeric", month: "short", year: "numeric" });
  };
  const formatTimestamp = (value) => {
    if (!value) return "";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "" : date.toLocaleString(locale, { dateStyle: "medium", timeStyle: "short" });
  };

  return (
    <section className="surface-card min-w-0 space-y-6 p-4 sm:p-6" aria-labelledby="market-page-title">
      <header className="flex min-w-0 flex-col gap-4 border-b border-surface-border pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <span className="section-badge">{t("farmer.marketEyebrow")}</span>
          <h2 id="market-page-title" className="mt-2 text-xl font-semibold text-text-heading sm:text-2xl">{t("market.title")}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-text-muted">{t("market.subtitle")}</p>
        </div>
        <div className="grid grid-cols-2 gap-x-5 gap-y-2 text-sm text-text-muted lg:min-w-64">
          <span>{t("market.state")}</span><strong className="text-right text-text-heading">{tv("states", stateName)}</strong>
          <span>{t("market.season")}</span><strong className="text-right text-text-heading">{tv("seasons", activeSeason)}</strong>
          <span>{t("market.forCrop")}</span><strong className="text-right capitalize text-accent-700">{tv("crops", activeCrop)}</strong>
        </div>
      </header>

      {loading ? <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr),minmax(0,0.8fr)]" role="status" aria-label={t("market.loading")} aria-busy="true">
        <div className="skeleton-card"><div className="skeleton-block h-4 w-36"/><div className="skeleton-block mt-5 h-9 w-2/3"/><div className="skeleton-block mt-4 h-56 w-full"/></div>
        <div className="skeleton-card"><div className="skeleton-block h-4 w-32"/><div className="mt-5 space-y-4">{[1, 2, 3].map((row) => <div key={row} className="border-b border-surface-border pb-4"><div className="skeleton-block h-4 w-3/4"/><div className="skeleton-block mt-3 h-3 w-full"/></div>)}</div></div>
      </div> : null}
      {error ? <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-danger-100 bg-danger-50 px-4 py-3 text-sm text-danger-700"><span>{error}</span><button type="button" className="theme-button-secondary px-3 py-2" onClick={() => setRetryCount((count) => count + 1)}>{t("market.tryAgain")}</button></div> : null}

      {!loading && !error && data ? <>
        <section className="space-y-4" aria-labelledby="market-live-title">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div><span className="section-badge"><MapPin size={13} aria-hidden="true" /> {t("market.locationEyebrow")}</span><h3 id="market-live-title" className="mt-2 text-lg font-semibold text-text-heading">{t("market.livePrice")}</h3></div>
            <div className="market-data-note flex flex-wrap items-center gap-x-2 gap-y-1"><span className="font-semibold">{data.mandi?.source || "AGMARKNET"}</span><span aria-hidden="true">·</span><span>{data.mandi?.from_cache ? t("market.liveCached") : data.mandi?.is_live ? t("market.liveUpdated") : t("market.referenceFallback")}</span>{data.mandi?.fetched_at ? <><span aria-hidden="true">·</span><time dateTime={data.mandi.fetched_at}>{t("market.fetchedAt")}: {formatTimestamp(data.mandi.fetched_at)}</time></> : null}</div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-[minmax(160px,0.65fr),minmax(180px,0.8fr),minmax(0,2fr)]">
            <div className="surface-card-soft flex items-center justify-between gap-3 p-4"><span className="text-sm text-text-muted">{t("market.state")}</span><strong className="text-sm text-text-heading">{tv("states", stateName)}</strong></div>
            <label className="text-xs font-semibold text-text-muted">{t("market.district")}<select className="theme-select mt-1 w-full" value={district} onChange={(event) => { setDistrict(event.target.value); setMarket("all"); setTrend([]); }}><option value="all">{t("market.allDistricts")}</option>{districtOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
            <label className="text-xs font-semibold text-text-muted">{t("market.mandi")}<select className="theme-select mt-1 w-full" value={market} onChange={(event) => { setMarket(event.target.value); setTrend([]); }}><option value="all">{t("market.allMarkets")}</option>{marketOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          </div>

          <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,0.8fr),minmax(0,1.4fr)]">
              <div className="surface-card-highlight flex min-h-48 flex-col justify-between p-5">
              <div><p className="text-xs font-semibold uppercase text-accent-700">{marketIsLive ? t("market.livePrice") : t("market.referencePrice")}</p><p className="mt-3 break-words text-3xl font-bold tabular-nums text-text-heading">{marketIsLive && currentPrice !== null ? `₹${Math.round(currentPrice).toLocaleString(locale)}` : currentMsp == null ? t("market.notListed") : `₹${Number(currentMsp).toLocaleString(locale)}`}</p><p className="mt-1 text-sm text-text-muted">/ {t("market.quintal")}</p>{marketIsLive && currentMsp != null ? <p className="mt-2 text-xs text-text-muted">{currentPrice >= currentMsp ? t("market.aboveMsp") : t("market.belowMsp")}: ₹{Math.abs(Math.round(currentPrice - currentMsp)).toLocaleString(locale)} / {t("market.quintal")}</p> : null}</div>
              <div className="mt-4 grid grid-cols-2 gap-3 border-t border-surface-border pt-3 text-xs"><div><p className="text-text-subtle">{t("market.latestDate")}</p><p className="mt-1 font-semibold text-text-heading">{formatDate(selectedRows[0]?.arrival_date || data.mandi?.summary?.latest_arrival_date)}</p></div><div><p className="text-text-subtle">{t("market.markets")}</p><p className="mt-1 font-semibold text-text-heading">{marketPrices.length || 0}</p></div></div>
              {data.mandi?.source_url ? <a href={data.mandi.source_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-accent-700 underline underline-offset-2">{t("market.openMandi")}<ExternalLink size={14} aria-hidden="true" /></a> : null}
            </div>
            <div className="chart-shell min-w-0 p-4 sm:p-5">
              <div className="flex flex-wrap items-start justify-between gap-3"><div><h4 className="text-base font-semibold text-text-heading">{t("market.priceByMarket")}</h4><p className="mt-1 text-xs leading-5 text-text-muted">{t("market.priceComparisonNote")}</p></div><span className="status-chip status-info">{t("market.modalPrice", "Modal price")} · ₹/{t("market.quintal")}</span></div>
              {marketPrices.length ? <div className="relative mt-4 h-64 min-w-0"><Bar data={comparisonData} options={chartOptions} role="img" aria-label={`${t("market.priceByMarket")}: ${marketPrices.map((item) => `${item.name}, ₹${Math.round(item.price)}`).join("; ")}`} /></div> : <p className="mt-5 border-t border-surface-border pt-4 text-sm text-text-muted">{data.mandi?.message || t("market.noRecentRecords")}</p>}
            </div>
          </div>

          {data.mandi?.scope === "national" ? <p className="border-l-2 border-warning-500 bg-warning-50 px-4 py-3 text-sm leading-6 text-warning-700">{t("market.nationalResults")}</p> : null}
          {!data.mandi?.is_live ? <p className="border-l-2 border-warning-500 bg-warning-50 px-4 py-3 text-sm leading-6 text-warning-700">{data.mandi?.errors?.length ? t("market.liveUnavailable") : t("market.noRecentRecords")} <a href="https://agmarknet.gov.in/" target="_blank" rel="noreferrer" className="ml-1 font-semibold underline">{t("market.openMandi")}</a></p> : null}

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-surface-border pt-4">
            <div><p className="text-sm font-semibold text-text-heading">{t("market.trendTitle")}</p><p className="mt-1 text-xs text-text-muted">{t("market.trendDesc")}</p></div>
            <button type="button" onClick={() => { setShowTrend((open) => !open); setTrend([]); }} className="theme-button-secondary inline-flex min-h-11 items-center gap-2 px-4"><TrendingUp size={16} aria-hidden="true" />{showTrend ? t("market.hideTrend") : t("market.loadTrend")}</button>
          </div>
          {showTrend ? <div className="chart-shell min-w-0 p-4 sm:p-5">{trendLoading ? <LoadingSpinner label={t("market.trendLoading")} /> : trend.length ? <div className="relative h-56 min-w-0"><Line data={trendData} options={trendOptions} role="img" aria-label={t("market.trendTitle")} /></div> : <p className="text-sm text-text-muted" role={trendError ? "status" : undefined}>{trendError || t("market.trendEmpty")}</p>}</div> : null}

          <div className="overflow-hidden rounded-md border border-surface-border">
            <table className="market-records__table hidden w-full border-collapse text-left text-sm md:table">
              <caption className="border-b border-surface-border bg-surface-muted px-4 py-3 text-left font-semibold text-text-heading">{t("market.recentRecords")}</caption>
              <thead className="bg-surface-muted text-xs text-text-muted"><tr><th scope="col" className="px-4 py-3">{t("market.mandi")}</th><th scope="col" className="px-4 py-3">{t("market.district")}</th><th scope="col" className="px-4 py-3">{t("market.latestDate")}</th><th scope="col" className="px-4 py-3">{t("market.min")}</th><th scope="col" className="px-4 py-3">{t("market.modalPrice", "Modal price")}</th><th scope="col" className="px-4 py-3">{t("market.max")}</th></tr></thead>
              <tbody className="divide-y divide-surface-border">{selectedRows.slice(0, 10).map((row, index) => <tr key={`${row.market}-${row.arrival_date}-${index}`} className="bg-white"><th scope="row" className="px-4 py-3 font-semibold text-text-heading">{row.market || "-"}</th><td className="px-4 py-3 text-text-muted">{row.district || "-"}</td><td className="px-4 py-3 text-text-muted">{formatDate(row.arrival_date)}</td><td className="px-4 py-3 tabular-nums text-text-muted">{row.min_price == null ? "-" : `₹${Number(row.min_price).toLocaleString(locale)}`}</td><td className="px-4 py-3 font-semibold tabular-nums text-accent-700">{row.modal_price == null ? "-" : `₹${Number(row.modal_price).toLocaleString(locale)}`}</td><td className="px-4 py-3 tabular-nums text-text-muted">{row.max_price == null ? "-" : `₹${Number(row.max_price).toLocaleString(locale)}`}</td></tr>)}</tbody>
            </table>
            <div className="space-y-3 p-3 md:hidden">
              <h4 className="text-sm font-semibold text-text-heading">{t("market.recentRecords")}</h4>
              {selectedRows.slice(0, 10).map((row, index) => (
                <article className="market-record-card" key={`${row.market}-${row.arrival_date}-${index}`}>
                  <div className="flex min-w-0 items-start justify-between gap-3">
                    <div className="min-w-0"><h5 className="break-words text-sm font-semibold text-text-heading">{row.market || "-"}</h5><p className="mt-1 break-words text-xs text-text-muted">{row.district || "-"}</p></div>
                    <time className="shrink-0 text-right text-xs tabular-nums text-text-subtle">{formatDate(row.arrival_date)}</time>
                  </div>
                  <dl className="market-record-card__prices">
                    <div className="market-record-card__metric"><dt className="market-record-card__label">{t("market.min")}</dt><dd className="market-record-card__value">{row.min_price == null ? "-" : `${rupee}${Number(row.min_price).toLocaleString(locale)}`}</dd></div>
                    <div className="market-record-card__metric border-accent-400"><dt className="market-record-card__label">{t("market.modalPrice", "Modal price")}</dt><dd className="market-record-card__value text-accent-700">{row.modal_price == null ? "-" : `${rupee}${Number(row.modal_price).toLocaleString(locale)}`}</dd></div>
                    <div className="market-record-card__metric"><dt className="market-record-card__label">{t("market.max")}</dt><dd className="market-record-card__value">{row.max_price == null ? "-" : `${rupee}${Number(row.max_price).toLocaleString(locale)}`}</dd></div>
                  </dl>
                </article>
              ))}
              {!selectedRows.length ? <p className="py-2 text-sm text-text-muted">{t("market.noRecentRecords")}</p> : null}
            </div>
            {!selectedRows.length ? <p className="hidden px-4 py-4 text-sm text-text-muted md:block">{t("market.noRecentRecords")}</p> : null}
          </div>
        </section>

        <section className="grid gap-4 xl:grid-cols-[minmax(0,0.9fr),minmax(0,1.6fr)]" aria-label={t("market.mspAndSchemes")}>
          <div className="surface-card-soft min-w-0 p-5">
            <span className="section-badge">{t("market.mspEligibility")}</span>
            <h3 className="mt-2 text-lg font-semibold text-text-heading">{t("market.mspForCrop", undefined, { crop: tv("crops", activeCrop) })}</h3>
            {data.msp?.variants?.length ? <label className="mt-3 block max-w-sm text-xs font-semibold text-text-muted">{t("market.mspVariety")}<select className="theme-select mt-1 w-full" value={mspVariant} onChange={(event) => { setMspVariant(event.target.value); setMspChecks({ procurement: false, registration: false, quality: false }); }}>{data.msp.variants.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label> : null}
            <div className="mt-4 flex flex-wrap items-end justify-between gap-3 border-b border-surface-border pb-4"><p className="text-3xl font-bold tabular-nums text-text-heading">{currentMsp == null ? t("market.notListed") : `₹${Number(currentMsp).toLocaleString(locale)}`}</p><span className="text-sm text-text-muted">/ {t("market.quintal")}</span><span className="status-chip status-info">{data.msp?.marketing_season}</span></div>
            <p className="mt-3 text-sm leading-6 text-text-muted">{t("market.mspDisclaimer")}</p>
            <div className="mt-4 space-y-2">
              {[["procurement", t("market.checkProcurement")], ["registration", t("market.checkRegistration")], ["quality", t("market.checkQuality")]].map(([key, label]) => <label key={key} className="flex min-h-11 items-start gap-2 text-sm leading-5 text-text-heading"><input className="mt-1" type="checkbox" checked={mspChecks[key]} disabled={currentMsp == null} onChange={(event) => setMspChecks((current) => ({ ...current, [key]: event.target.checked }))} /><span>{label}</span></label>)}
            </div>
            <p className="mt-3 rounded-md border-l-2 border-accent-500 bg-white px-3 py-2 text-sm leading-5 text-text-muted" role="status">{currentMsp == null ? t("market.mspUnavailable") : readyCount === 3 ? t("market.mspAllChecked") : t("market.mspReadiness", undefined, { count: readyCount })}</p>
            {data.msp?.source_url ? <a href={data.msp.source_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-accent-700 underline underline-offset-2">{t("market.mspSource")}<ExternalLink size={14} aria-hidden="true" /></a> : null}
          </div>

          <div className="min-w-0 space-y-4">
            <div className="flex flex-col gap-3 border-b border-surface-border pb-4 sm:flex-row sm:items-end sm:justify-between">
              <div><span className="section-badge">{t("market.schemes")}</span><h3 className="mt-2 text-lg font-semibold text-text-heading">{t("market.findSchemes")}</h3><p className="mt-1 text-sm text-text-muted">{tv("states", stateName)} · {tv("seasons", activeSeason)} · {tv("crops", activeCrop)}</p></div>
              <label className="relative min-w-0 sm:w-64"><span className="sr-only">{t("market.searchSchemes")}</span><Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-subtle" aria-hidden="true" /><input className="field-shell w-full pl-9" value={schemeSearch} onChange={(event) => setSchemeSearch(event.target.value)} placeholder={t("market.searchSchemes")} /></label>
            </div>
            <div className="flex flex-wrap gap-2" role="group" aria-label={t("market.schemeCategory")}>
              {[["all", t("market.categoryAll")], ["income", t("market.categoryIncome")], ["insurance", t("market.categoryInsurance")], ["state", t("market.categoryState")]].map(([value, label]) => <button key={value} type="button" aria-pressed={schemeCategory === value} onClick={() => setSchemeCategory(value)} className={`min-h-10 rounded-md border px-3 py-2 text-sm font-semibold ${schemeCategory === value ? "border-primary-700 bg-primary-700 text-white" : "border-surface-border bg-white text-text-heading hover:bg-surface-muted"}`}>{label}</button>)}
            </div>
            <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-3">
              {schemes.map((scheme) => <article key={scheme.name} className="flex min-w-0 flex-col border-l-2 border-accent-400 bg-surface-muted p-4">
                <div className="flex flex-wrap items-start justify-between gap-2"><h4 className="min-w-0 break-words text-base font-semibold text-text-heading">{scheme.name}</h4><span className="status-chip status-info">{t(`market.category.${scheme.category}`, scheme.category)}</span></div>
                <p className="mt-2 text-sm leading-6 text-text-muted">{scheme.benefit}</p>
                <div className="mt-3 border-t border-surface-border pt-3"><p className="text-xs font-semibold text-text-heading">{t("market.schemeEligibility")}</p><p className="mt-1 text-sm leading-5 text-text-muted">{scheme.eligibility}</p></div>
                <div className="mt-3"><p className="text-xs font-semibold text-text-heading">{t("market.documentsMayBeNeeded")}</p><ul className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs leading-5 text-text-muted">{(scheme.documents || []).map((doc) => <li key={doc} className="before:mr-1 before:text-accent-700 before:content-['•']">{doc}</li>)}</ul></div>
                <a href={scheme.link} target="_blank" rel="noreferrer" className="mt-auto inline-flex min-h-10 items-center gap-2 pt-3 text-sm font-semibold text-accent-700 underline underline-offset-2">{t("market.checkOfficialDetails")}<ExternalLink size={14} aria-hidden="true" /></a>
              </article>)}
              {!schemes.length ? <p className="border-l-2 border-surface-border px-4 py-3 text-sm text-text-muted">{t("market.noMatchingSchemes")}</p> : null}
            </div>
            <p className="border-l-2 border-warning-500 bg-warning-50 px-4 py-3 text-xs leading-5 text-warning-700">{t("market.schemeDisclaimer")}</p>
          </div>
        </section>

        <section className="grid gap-4 border-t border-surface-border pt-5 md:grid-cols-2">
          <div className="border-l-2 border-accent-300 pl-4"><p className="text-xs font-semibold uppercase text-accent-700">{t("market.tip")}</p><p className="mt-2 text-sm leading-6 text-text-muted">{data.market_tip || ""}</p></div>
          <div className="border-l-2 border-surface-border pl-4"><p className="text-xs font-semibold uppercase text-accent-700">{t("market.kvk")}</p><p className="mt-2 text-sm font-semibold text-text-heading">{data.kvk?.name || t("market.localOffice")}</p><p className="mt-1 text-sm text-text-muted">{data.kvk?.contact || ""}</p></div>
        </section>
      </> : null}
    </section>
  );
}

export default MarketInsights;
