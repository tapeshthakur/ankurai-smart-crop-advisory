import React from "react";
import { NavLink } from "react-router-dom";
import { useLanguage } from "../i18n/LanguageContext";

function Sidebar({ role, moduleItems = [], activeModule, onModuleChange }) {
  const { t } = useLanguage();
  const moduleIcons = {
    overview: "AD",
    crop: "CP",
    disease: "LD",
    market: "MS",
    ai: "AI",
    soil: "SR",
    history: "RP",
  };
  const links =
    role === "admin"
      ? [{ to: "/dashboard", label: t("sidebar.adminDashboard"), hint: t("sidebar.adminHint") }]
      : [{ to: "/dashboard", label: t("sidebar.farmerDashboard"), hint: t("sidebar.farmerHint") }];
  const isAdmin = role === "admin";

  return (
    <aside className="mobile-sidebar app-shell ambient-grid h-fit lg:sticky lg:top-24">
      <div className="relative z-10">
        <span className="section-badge">{isAdmin ? t("sidebar.adminPanel") : t("sidebar.navigation")}</span>
        <h2 className="mt-4 text-2xl font-semibold text-text-heading">
          {isAdmin ? t("sidebar.adminDashboard") : t("sidebar.advisoryModules")}
        </h2>

        {isAdmin && !moduleItems.length ? (
          <nav className="mt-6 space-y-3">
            {links.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  [
                    "block rounded-[1.35rem] border px-4 py-4 transition-all duration-200",
                    isActive
                      ? "border-primary-300 bg-primary-50 shadow-card"
                      : "border-surface-border bg-surface-card hover:border-primary-300 hover:bg-primary-50",
                  ].join(" ")
                }
              >
                {({ isActive }) => (
                  <>
                    <p className={`text-sm font-semibold ${isActive ? "text-primary-800" : "text-text-heading"}`}>{item.label}</p>
                    <p className="mt-1 text-sm text-text-muted">{item.hint}</p>
                  </>
                )}
              </NavLink>
            ))}
          </nav>
        ) : null}

        {moduleItems.length ? (
          <div className="mt-5">
            <div className="-mx-2 mt-3 flex gap-2 overflow-x-auto px-2 pb-2 lg:mx-0 lg:block lg:space-y-2 lg:overflow-visible lg:px-0 lg:pb-0">
              {moduleItems.map((item) => {
                const isActive = activeModule === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => onModuleChange?.(item.id)}
                    className={[
                      "interactive-lift block min-w-[180px] rounded-2xl border px-3 py-3 text-left transition-all duration-200 lg:w-full lg:min-w-0",
                      isActive
                        ? "border-primary-300 bg-primary-50 shadow-card"
                        : "border-surface-border bg-surface-card hover:border-primary-300 hover:bg-primary-50",
                    ].join(" ")}
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className={[
                          "flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border text-[10px] font-bold",
                          isActive
                            ? "border-primary-300 bg-primary-700 text-text-inverse"
                            : "border-surface-border bg-surface-muted text-primary-800",
                        ].join(" ")}
                      >
                        {moduleIcons[item.id] || "MD"}
                      </span>
                      <span>
                        <p className={`text-[10px] font-semibold uppercase tracking-[0.16em] ${isActive ? "text-primary-800" : "text-text-muted"}`}>
                          {item.eyebrow}
                        </p>
                        <p className="mt-1 text-sm font-semibold text-text-heading">{item.label}</p>
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        ) : null}
      </div>
    </aside>
  );
}

export default Sidebar;
