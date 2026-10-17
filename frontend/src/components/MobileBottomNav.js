import React from "react";
import { Bell, ChartNoAxesCombined, History, Layers3, MessageCircle, ScanLine, Sprout, Store } from "lucide-react";
import { useLanguage } from "../i18n/LanguageContext";

const moduleIcons = { crop: Sprout, disease: ScanLine, market: Store, ai: MessageCircle, soil: Layers3, history: History, usage: ChartNoAxesCombined, alerts: Bell };

function MobileBottomNav({ items = [], activeModule, onModuleChange }) {
  const { t } = useLanguage();
  return (
    <nav className="mobile-bottom-nav" aria-label={t("sidebar.advisoryModules")}>
      {items.map((item) => {
        const isActive = activeModule === item.id;
        const Icon = moduleIcons[item.id] || Sprout;
        return (
        <button key={item.id} type="button" aria-label={item.label} aria-current={isActive ? "page" : undefined} onClick={() => onModuleChange?.(item.id)} className={`mobile-bottom-nav__item ${isActive ? "is-active" : ""}`}>
            <Icon className="mobile-bottom-nav__icon" size={19} strokeWidth={1.8} aria-hidden="true" />
            <span className="mobile-bottom-nav__label" aria-hidden="true">{item.mobileLabel || item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

export default MobileBottomNav;
