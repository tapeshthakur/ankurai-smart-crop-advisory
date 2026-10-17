import React from "react";
import { NavLink } from "react-router-dom";
import { Activity, Bell, ChartNoAxesCombined, History, Languages, Layers3, LayoutDashboard, MessageCircle, ScanLine, Sprout, Store } from "lucide-react";
import { useLanguage } from "../i18n/LanguageContext";

function Sidebar({ role, moduleItems = [], activeModule, onModuleChange }) {
  const { t } = useLanguage();
  const moduleIcons = {
    overview: LayoutDashboard,
    alerts: Bell,
    crop: Sprout,
    disease: ScanLine,
    market: Store,
    ai: MessageCircle,
    soil: Layers3,
    history: History,
    usage: ChartNoAxesCombined,
    translations: Languages,
  };
  const links =
    role === "admin"
      ? [{ to: "/dashboard", label: t("sidebar.adminDashboard"), hint: t("sidebar.adminHint") }]
      : [{ to: "/dashboard", label: t("sidebar.farmerDashboard"), hint: t("sidebar.farmerHint") }];
  const isAdmin = role === "admin";

  return (
    <aside className="mobile-sidebar h-fit lg:sticky lg:top-24">
      <div className="relative z-10">
        <span className="section-badge">{isAdmin ? t("sidebar.adminPanel") : t("sidebar.navigation")}</span>
        <h2 className="mt-3 text-xl font-semibold text-text-heading">
          {isAdmin ? t("sidebar.adminDashboard") : t("sidebar.advisoryModules")}
        </h2>

        {isAdmin && !moduleItems.length ? (
          <nav className="mt-5 space-y-1">
            {links.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  [
                    "block rounded-md border-l-2 px-3 py-3 transition-colors duration-150",
                    isActive
                      ? "border-l-primary-700 bg-primary-50"
                      : "border-l-transparent hover:bg-surface-muted",
                  ].join(" ")
                }
              >
                {({ isActive }) => (
                  <>
                    <span className="flex items-center gap-2 text-sm font-semibold text-text-heading"><Activity size={17} aria-hidden="true" />{item.label}</span>
                    <p className="mt-1 text-sm text-text-muted">{item.hint}</p>
                  </>
                )}
              </NavLink>
            ))}
          </nav>
        ) : null}

        {moduleItems.length ? (
          <div className="mt-4">
            <div className="-mx-2 mt-2 flex gap-1 overflow-x-auto px-2 pb-2 lg:mx-0 lg:block lg:space-y-1 lg:overflow-visible lg:px-0 lg:pb-0">
              {moduleItems.map((item) => {
                const isActive = activeModule === item.id;
                const Icon = moduleIcons[item.id] || LayoutDashboard;
                return (
                  <button
                    key={item.id}
                    type="button"
                    aria-current={isActive ? "page" : undefined}
                    aria-label={item.label}
                    onClick={() => onModuleChange?.(item.id)}
                    className={[
                      "block min-w-[180px] rounded-md border-l-2 px-3 py-3 text-left transition-colors duration-150 lg:w-full lg:min-w-0",
                      isActive
                        ? "border-l-primary-700 bg-primary-50"
                        : "border-l-transparent hover:bg-surface-muted",
                    ].join(" ")}
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className={[
                          "flex h-9 w-9 shrink-0 items-center justify-center rounded-md border transition-colors",
                          isActive
                            ? "border-primary-300 bg-primary-700 text-text-inverse"
                            : "border-surface-border bg-surface-muted text-primary-800",
                        ].join(" ")}
                      >
                        <Icon size={18} strokeWidth={1.8} aria-hidden="true" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <p className={`text-[10px] font-semibold uppercase tracking-[0.16em] ${isActive ? "text-primary-800" : "text-text-muted"}`}>
                          {item.eyebrow}
                        </p>
                        <p className="mt-1 break-words text-sm font-semibold text-text-heading">{item.label}</p>
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
