import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useLanguage } from "../i18n/LanguageContext";

function LoginPage() {
  const { login } = useAuth();
  const { t } = useLanguage();
  const [form, setForm] = useState({ email: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || "/dashboard";

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    try {
      setLoading(true);
      const user = await login(form);
      navigate(from === "/login" ? "/dashboard" : from, { replace: true, state: { role: user.role } });
    } catch (err) {
      setError(err.response?.data?.error || t("login.failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-[82vh] w-full max-w-7xl items-center px-4 py-10 sm:px-6 lg:px-8">
      <section className="grid w-full gap-6 lg:grid-cols-[0.95fr,1.05fr]">
        <div className="auth-intro surface-card-highlight p-5 sm:p-8 lg:p-10">
          <span className="section-badge">{t("login.badge")}</span>
          <h1 className="mt-5 text-4xl font-bold leading-tight text-text-heading">{t("login.title")}</h1>
          <p className="mt-4 max-w-xl text-base leading-8 text-text-muted">{t("login.subtitle")}</p>

          <div className="mt-8 grid gap-4">
            <div className="surface-card-soft p-4">
              <p className="text-sm font-semibold text-accent-700">{t("login.farmerDashboard")}</p>
              <p className="mt-2 text-sm leading-6 text-text-muted">{t("login.farmerDashboardDesc")}</p>
            </div>
            <div className="surface-card-soft p-4">
              <p className="text-sm font-semibold text-accent-700">{t("login.adminMonitoring")}</p>
              <p className="mt-2 text-sm leading-6 text-text-muted">{t("login.adminMonitoringDesc")}</p>
            </div>
          </div>
        </div>

        <section className="surface-card p-5 sm:p-8 lg:p-10">
          <div className="max-w-xl">
            <span className="section-badge">{t("login.formBadge")}</span>
            <h2 className="mt-5 text-3xl font-semibold text-text-heading">{t("login.title")}</h2>
            <p className="mt-2 text-sm leading-6 text-text-muted">{t("login.subtitle")}</p>
          </div>

          <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
            <label className="block space-y-2">
              <span className="text-sm font-medium text-text-muted">{t("login.email")}</span>
              <input
                type="email"
                value={form.email}
                onChange={(e) => handleChange("email", e.target.value)}
                required
                className="field-shell"
                placeholder={t("login.emailPlaceholder")}
              />
            </label>

            <label className="block space-y-2">
              <span className="text-sm font-medium text-text-muted">{t("login.password")}</span>
              <input
                type="password"
                value={form.password}
                onChange={(e) => handleChange("password", e.target.value)}
                required
                className="field-shell"
                placeholder={t("login.password")}
              />
            </label>

            {error ? <p className="rounded-2xl border border-danger-100 bg-danger-50 px-4 py-3 text-sm text-danger-700">{error}</p> : null}

            <button
              type="submit"
              disabled={loading}
              className="theme-button-primary w-full px-4 py-3 disabled:opacity-70"
            >
              {loading ? t("login.loading") : t("login.button")}
            </button>
          </form>

          <p className="mt-6 text-sm text-text-muted">
            {t("login.newUser")}{" "}
            <Link to="/signup" className="font-semibold text-accent-700 hover:text-accent-800">
              {t("login.createAccount")}
            </Link>
          </p>
        </section>
      </section>
    </main>
  );
}

export default LoginPage;
