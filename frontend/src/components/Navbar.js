import React, { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useLanguage } from "../i18n/LanguageContext";
import Button from "./Button";
import ThemedSelect from "./ThemedSelect";
import InstallAppButton from "./InstallAppButton";
import logo from "../assets/ankurai-navbar.png";

function Navbar() {
  const { isAuthenticated, user, logout } = useAuth();
  const { language, setLanguage, languageOptions, t } = useLanguage();
  const navigate = useNavigate();
  const [accountOpen, setAccountOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="sticky top-0 z-40 border-b border-surface-border bg-background/92 backdrop-blur-xl">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-2 px-3 py-2 sm:gap-4 sm:px-6 sm:py-3 lg:px-8">
        <Link to="/" className="group flex shrink-0 items-center" aria-label="AnkurAI home">
          <img src={logo} alt="AnkurAI" className="h-14 w-32 object-contain sm:h-16 sm:w-40" />
        </Link>

        <div className="flex min-w-0 items-center gap-1.5 sm:gap-3">
          <div className="hidden items-center gap-3 rounded-2xl border border-surface-border bg-surface-card px-3 py-2 shadow-card md:flex">
            <label className="text-[11px] font-semibold uppercase tracking-[0.18em] text-text-muted">{t("nav.language")}</label>
            <ThemedSelect value={language} onChange={setLanguage} options={languageOptions} className="min-w-[138px]" />
          </div>

          <div className="md:hidden">
            <ThemedSelect value={language} onChange={setLanguage} options={languageOptions} className="min-w-[118px]" />
          </div>

          <InstallAppButton />

          {!isAuthenticated ? (
            <div className="flex items-center gap-2">
              <Button as={NavLink} to="/login" variant="ghost" className="touch-target px-2 py-2 text-xs sm:px-4 sm:text-sm">
                {t("nav.login")}
              </Button>
              <Button as={NavLink} to="/signup" className="mobile-signup-button touch-target px-2 py-2 text-xs sm:px-4 sm:text-sm">
                {t("nav.getStarted")}
              </Button>
            </div>
          ) : (
            <div className="hidden items-center gap-3 sm:flex">
              <div className="hidden rounded-2xl border border-surface-border bg-surface-card px-4 py-2 shadow-card sm:block">
                <p className="text-[11px] uppercase tracking-[0.16em] text-text-muted">{t("nav.signedIn")}</p>
                <p className="mt-1 text-sm font-medium text-text-heading">
                  {user?.name} <span className="text-text-muted">({t(`signup.${user?.role}`, user?.role)})</span>
                </p>
              </div>
              <Button as={NavLink} to="/dashboard" variant="ghost" className="px-4 py-2">
                {t("nav.dashboard")}
              </Button>
              <Button
                type="button"
                onClick={handleLogout}
                className="px-4 py-2"
              >
                {t("nav.logout")}
              </Button>
            </div>
          )}

          {isAuthenticated ? (
            <div className="relative sm:hidden">
              <button type="button" onClick={() => setAccountOpen((open) => !open)} className="theme-button-ghost touch-target px-3 py-2 text-xs" aria-expanded={accountOpen}>
                Account
              </button>
              {accountOpen ? (
                <div className="absolute right-0 top-[calc(100%+0.5rem)] z-50 w-44 rounded-2xl border border-surface-border bg-white p-2 shadow-lift">
                  <NavLink to="/dashboard" onClick={() => setAccountOpen(false)} className="block rounded-xl px-3 py-3 text-sm font-semibold text-text-heading hover:bg-primary-50">
                    {t("nav.dashboard")}
                  </NavLink>
                  <button type="button" onClick={handleLogout} className="mt-1 block w-full rounded-xl px-3 py-3 text-left text-sm font-semibold text-danger-700 hover:bg-danger-50">
                    {t("nav.logout")}
                  </button>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}

export default Navbar;
