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

const USER_STORAGE_KEY = "runassist:user";

export const App: React.FC = () => {
  const [view, setView] = useState<View>("login");
  const [user, setUser] = useState<User | null>(null);

  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [days, setDays] = useState(30);
  const [weeks, setWeeks] = useState(6);
  const [loadingDash, setLoadingDash] = useState(false);
  const [dashError, setDashError] = useState<string | null>(null);

  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(USER_STORAGE_KEY);
    if (stored) {
      try {
        const parsed: User = JSON.parse(stored);
        if (parsed.id && parsed.role) {
          setUser(parsed);
          setView("dashboard");
        } else {
          localStorage.removeItem(USER_STORAGE_KEY);
        }
      } catch (e) {
        console.error("Failed to parse stored user", e);
        localStorage.removeItem(USER_STORAGE_KEY);
      }
    }
    setInitialized(true);
  }, []);

  useEffect(() => {
    if (user) {
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(USER_STORAGE_KEY);
    }
  }, [user]);

  useEffect(() => {
    if (!user && view === "dashboard") {
      setView("login");
    }
  }, [user, view]);

  async function handleLogin(
    username: string,
    password: string,
    role: UserRole
  ) {
    const u = await loginUser(username, password, role);
    setUser(u);             
    setView("dashboard");
  }

  async function handleRegister(
    username: string,
    password: string,
    role: UserRole
  ) {
    await registerUser(username, password, role);
  }

  useEffect(() => {
    if (!user || user.role !== "runner" || view !== "dashboard") return;
    setLoadingDash(true);
    setDashError(null);
    fetchDashboard(user.id, days, weeks)
      .then((data) => setDashboard(data))
      .catch((err) => {
        console.error(err);
        setDashError(err.message || "Failed to load dashboard");
      })
      .finally(() => setLoadingDash(false));
  }, [user, view, days, weeks]);

  if (!initialized) {
    return <div>Loading…</div>;
  }

  if (view === "login") {
    return (
      <LoginForm
        onLogin={handleLogin}
        switchToRegister={() => setView("register")}
      />
    );
  }

  if (view === "register") {
    return (
      <RegisterForm
        onRegister={handleRegister}
        switchToLogin={() => setView("login")}
      />
    );
  }

  // Dashboard
  if (!user) return null;

  if (user.role === "coach") {
    return (
      <div className="app-root">
        <CoachDashboard coach={user} />
      </div>
    );
  }

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
