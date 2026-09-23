import React from "react";

const moduleIcons = { crop: "CP", disease: "LD", market: "MS", ai: "AI", soil: "SR", history: "RP" };

function MobileBottomNav({ items = [], activeModule, onModuleChange }) {
  return (
    <nav className="mobile-bottom-nav" aria-label="Advisory modules" style={{ gridTemplateColumns: `repeat(${Math.max(1, items.length)}, minmax(0, 1fr))` }}>
      {items.map((item) => {
        const isActive = activeModule === item.id;
        return (
          <button key={item.id} type="button" aria-current={isActive ? "page" : undefined} onClick={() => onModuleChange?.(item.id)} className={`mobile-bottom-nav__item ${isActive ? "is-active" : ""}`}>
            <span className="mobile-bottom-nav__icon">{moduleIcons[item.id] || "MD"}</span>
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

export default MobileBottomNav;
