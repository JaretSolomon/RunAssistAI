// src/App.tsx 
import React, { useEffect, useState } from "react";
import { LoginForm } from "./components/LoginForm";
import { RegisterForm } from "./components/RegisterForm";
import { Dashboard } from "./components/Dashboard";
import { CoachDashboard } from "./components/CoachDashboard";
import {
  loginUser,
  registerUser,
  fetchDashboard,
  User,
  UserRole,
  DashboardResponse,
} from "./api";

type View = "login" | "register" | "dashboard";

export const App: React.FC = () => {
  const [view, setView] = useState<View>("login");
  const [user, setUser] = useState<User | null>(null);

  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [days, setDays] = useState(30);
  const [weeks, setWeeks] = useState(6);
  const [loadingDash, setLoadingDash] = useState(false);
  const [dashError, setDashError] = useState<string | null>(null);

  // Login: must be a registered user + selected role
  async function handleLogin(username: string, role: UserRole) {
    const u = await loginUser(username, role);
    setUser(u);
    setView("dashboard");
  }

  // Registration: after success, RegisterForm will switch back to login page
  async function handleRegister(username: string, role: UserRole) {
    await registerUser(username, role);
  }

  // Only runners need to load dashboard data
  useEffect(() => {
    if (!user || user.role !== "runner" || view !== "dashboard") return;
    setLoadingDash(true);
    setDashError(null);
    fetchDashboard(user.id, days, weeks)
      .then((data) => {
        setDashboard(data);
      })
      .catch((err) => {
        console.error(err);
        setDashError(err.message || "Failed to load dashboard");
      })
      .finally(() => setLoadingDash(false));
  }, [user, view, days, weeks]);

  if (!user && view === "dashboard") {
    setView("login");
  }

  // ---- Login Page ----
  if (view === "login") {
    return (
      <div className="auth-page">
        <LoginForm
          onLogin={handleLogin}
          switchToRegister={() => setView("register")}
        />
      </div>
    );
  }

  // ---- Register Page ----
  if (view === "register") {
    return (
      <div className="auth-page">
        <RegisterForm
          onRegister={handleRegister}
          switchToLogin={() => setView("login")}
        />
      </div>
    );
  }

  // ---- Dashboard ----
  if (!user) return null;

  // Coach view
  if (user.role === "coach") {
    return (
      <div className="app-root">
        <CoachDashboard coach={user} />
      </div>
    );
  }

  // Runner view
  return (
    <div className="app-root">
      {loadingDash && !dashboard && (
        <div className="dash-loading">Loading dashboard...</div>
      )}
      {dashError && (
        <div className="dash-error-banner">
          Failed to load dashboard: {dashError}
        </div>
      )}
      <Dashboard
        data={dashboard}
        username={user.name}
        userId={user.id}
        days={days}
        weeks={weeks}
        onChangeDays={setDays}
        onChangeWeeks={setWeeks}
        runnerCode={user.runner_code ?? null}
      />
    </div>
  );
};
