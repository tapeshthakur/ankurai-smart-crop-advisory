import React from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./auth/ProtectedRoute";
import { useAuth } from "./auth/AuthContext";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import FarmerDashboard from "./pages/FarmerDashboard";
import AdminDashboard from "./pages/AdminDashboard";
import { useLanguage } from "./i18n/LanguageContext";

function DashboardSwitch() {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (user.role === "admin") {
    return <AdminDashboard />;
  }

  return <FarmerDashboard />;
}

function App() {
  const location = useLocation();
  const { t } = useLanguage();

  return (
    <div className="app-background">
      <a className="skip-link" href="#main-content">{t("app.skipContent")}</a>
      <Navbar />
      <div id="main-content" tabIndex={-1} key={location.pathname} className="page-transition">
        <Routes location={location}>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute allowedRoles={["farmer", "admin"]}>
                <DashboardSwitch />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  );
}

export default App;
