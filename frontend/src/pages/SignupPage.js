import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useLanguage } from "../i18n/LanguageContext";
import ThemedSelect from "../components/ThemedSelect";

function SignupPage() {
  const { signup } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    role: "farmer",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (form.password.length < 6) {
      setError(t("signup.passwordShort"));
      return;
    }

    try {
      setLoading(true);
      await signup(form);
      setSuccess(t("signup.success"));
      setTimeout(() => navigate("/login"), 1200);
    } catch (err) {
      setError(err.response?.data?.error || t("signup.failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-[82vh] w-full max-w-7xl items-center px-4 py-10 sm:px-6 lg:px-8">
      <section className="grid w-full gap-6 lg:grid-cols-[0.9fr,1.1fr]">
        <div className="auth-intro surface-card-highlight p-5 sm:p-8 lg:p-10">
          <span className="section-badge">{t("signup.badge")}</span>
          <h1 className="mt-5 text-4xl font-bold leading-tight text-text-heading">{t("signup.title")}</h1>
          <p className="mt-4 max-w-xl text-base leading-8 text-text-muted">{t("signup.subtitle")}</p>

          <div className="mt-8 grid gap-4">
            <div className="surface-card-soft p-4">
              <p className="text-sm font-semibold text-accent-700">{t("signup.farmerAccess")}</p>
              <p className="mt-2 text-sm leading-6 text-text-muted">{t("signup.farmerAccessDesc")}</p>
            </div>
            <div className="surface-card-soft p-4">
              <p className="text-sm font-semibold text-accent-700">{t("signup.adminAccess")}</p>
              <p className="mt-2 text-sm leading-6 text-text-muted">{t("signup.adminAccessDesc")}</p>
            </div>
          </div>
        </div>

        <section className="surface-card p-5 sm:p-8 lg:p-10">
          <div className="max-w-xl">
            <span className="section-badge">{t("signup.formBadge")}</span>
            <h2 className="mt-5 text-3xl font-semibold text-text-heading">{t("signup.title")}</h2>
            <p className="mt-2 text-sm leading-6 text-text-muted">{t("signup.subtitle")}</p>
          </div>

          <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
            <label className="block space-y-2">
              <span className="text-sm font-medium text-text-muted">{t("signup.name")}</span>
              <input
                type="text"
                value={form.name}
                onChange={(e) => handleChange("name", e.target.value)}
                required
                className="field-shell"
                placeholder={t("signup.name")}
              />
            </label>

            <label className="block space-y-2">
              <span className="text-sm font-medium text-text-muted">{t("signup.email")}</span>
              <input
                type="email"
                value={form.email}
                onChange={(e) => handleChange("email", e.target.value)}
                required
                className="field-shell"
                placeholder={t("signup.emailPlaceholder")}
              />
            </label>

            <label className="block space-y-2">
              <span className="text-sm font-medium text-text-muted">{t("signup.password")}</span>
              <input
                type="password"
                value={form.password}
                onChange={(e) => handleChange("password", e.target.value)}
                required
                minLength={6}
                className="field-shell"
                placeholder={t("signup.password")}
              />
            </label>

            <label className="block space-y-2">
              <span className="text-sm font-medium text-text-muted">{t("signup.role")}</span>
              <ThemedSelect
                value={form.role}
                onChange={(nextRole) => handleChange("role", nextRole)}
                options={[
                  { value: "farmer", label: t("signup.farmer") },
                  { value: "admin", label: t("signup.admin") },
                ]}
              />
            </label>

            {error ? <p className="rounded-2xl border border-danger-100 bg-danger-50 px-4 py-3 text-sm text-danger-700">{error}</p> : null}
            {success ? <p className="rounded-2xl border border-accent-300 bg-success-50 px-4 py-3 text-sm text-accent-700">{success}</p> : null}

            <button type="submit" disabled={loading} className="theme-button-primary w-full px-4 py-3 disabled:opacity-70">
              {loading ? t("signup.loading") : t("signup.button")}
            </button>
          </form>

          <p className="mt-6 text-sm text-text-muted">
            {t("signup.already")}{" "}
            <Link to="/login" className="font-semibold text-accent-700 hover:text-accent-800">
              {t("nav.login")}
            </Link>
          </p>
        </section>
      </section>
    </main>
  );
}

export default SignupPage;
