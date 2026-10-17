import React from "react";
import { ArrowRight, BarChart3, ScanLine, Sprout, Store } from "lucide-react";
import { Link } from "react-router-dom";
import cottonField from "../assets/crops/cotton.jpg";
import { useLanguage } from "../i18n/LanguageContext";

function LandingPage() {
  const { t } = useLanguage();
  const featureHighlights = [
    { Icon: Sprout, title: t("landing.features.cropTitle"), description: t("landing.features.cropDesc") },
    { Icon: ScanLine, title: t("landing.features.diseaseTitle"), description: t("landing.features.diseaseDesc") },
    { Icon: BarChart3, title: t("landing.features.insightTitle"), description: t("landing.features.insightDesc") },
  ];

  return (
    <main className="w-full">
      <section className="landing-hero relative isolate flex min-h-[500px] flex-col justify-end overflow-hidden sm:min-h-[580px]">
        <img src={cottonField} alt="" aria-hidden="true" fetchPriority="high" className="absolute inset-0 h-full w-full object-cover object-[55%_center]" />
        <div aria-hidden="true" className="absolute inset-0 bg-[#17271c]/45" />
        <div className="relative z-10 mx-auto flex w-full max-w-7xl flex-1 flex-col justify-end px-5 pb-10 pt-14 text-white sm:px-8 sm:pb-14 lg:px-10">
          <div className="max-w-3xl">
            <span className="inline-flex items-center gap-2 text-sm font-semibold text-white/90">
              <Sprout size={18} aria-hidden="true" />
              {t("landing.badge")}
            </span>
            <h1 className="mt-4 max-w-2xl text-4xl font-bold leading-tight text-white sm:text-5xl lg:text-6xl">
              {t("landing.title")}
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-white/90 sm:text-lg sm:leading-8">
              {t("landing.subtitle")}
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link to="/signup" className="theme-button-primary bg-white px-5 py-3 text-primary-900 hover:bg-primary-50">
                {t("nav.getStarted")} <ArrowRight size={16} aria-hidden="true" />
              </Link>
              <Link to="/login" className="theme-button-secondary border-white/75 bg-white/10 px-5 py-3 text-white hover:bg-white/20">
                {t("nav.login")}
              </Link>
              <a href="#capabilities" className="theme-button-ghost border-white/40 bg-transparent px-5 py-3 text-white hover:bg-white/10">
                {t("landing.modules")}
              </a>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-8 sm:px-6 lg:grid-cols-[0.8fr,1.2fr] lg:items-start lg:px-8 lg:py-10">
        <div>
          <span className="section-badge">{t("landing.snapshot")}</span>
          <h2 className="mt-2 text-2xl font-semibold text-text-heading">{t("landing.snapshotTitle")}</h2>
          <p className="mt-3 max-w-xl text-sm leading-6 text-text-muted">{t("landing.snapshotDesc")}</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <article className="surface-card border-l-2 border-l-primary-700 p-4 sm:p-5">
            <p className="text-sm font-semibold text-text-heading">{t("signup.farmerAccess")}</p>
            <p className="mt-2 text-sm leading-6 text-text-muted">{t("signup.farmerAccessDesc")}</p>
            <Link to="/signup" className="mt-4 inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-primary-800 hover:text-primary-900">
              {t("nav.getStarted")} <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </article>
          <article className="surface-card border-l-2 border-l-accent-500 p-4 sm:p-5">
            <p className="text-sm font-semibold text-text-heading">{t("login.adminMonitoring")}</p>
            <p className="mt-2 text-sm leading-6 text-text-muted">{t("signup.adminAccessDesc")}</p>
            <Link to="/login" className="mt-4 inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-accent-800 hover:text-accent-900">
              {t("nav.login")} <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </article>
        </div>
      </section>

      <section id="capabilities" className="border-y border-surface-border bg-surface-muted/70">
        <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8 lg:py-10">
          <div className="mb-5 flex items-end justify-between gap-4">
            <div>
              <span className="section-badge">{t("landing.modules")}</span>
              <h2 className="mt-2 text-2xl font-semibold text-text-heading">{t("landing.snapshotTitle")}</h2>
            </div>
          </div>
          <div className="grid gap-0 md:grid-cols-3">
            {featureHighlights.map(({ Icon, title, description }, index) => (
              <article key={title} className={`min-w-0 border-t border-surface-border py-5 md:border-t-0 md:py-2 ${index ? "md:border-l md:pl-6" : "md:pr-6"}`}>
                <Icon size={21} strokeWidth={1.8} className="text-primary-700" aria-hidden="true" />
                <h3 className="mt-3 text-base font-semibold text-text-heading">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-text-muted">{description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

export default LandingPage;
