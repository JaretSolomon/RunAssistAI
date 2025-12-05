// src/components/LoginForm.tsx
import React, { useState } from "react";
import type { UserRole } from "../api";

interface LoginFormProps {
  onLogin: (username: string, password: string, role: UserRole) => Promise<void>;
  switchToRegister: () => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({
  onLogin,
  switchToRegister,
}) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("runner");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim() || !password) return;
    setLoading(true);
    setError(null);
    try {
      await onLogin(username.trim(), password, role);
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-layout">
      <div className="auth-hero">
        <div className="auth-hero-orbit" />
        <div className="auth-hero-glow" />
        <div className="auth-hero-content">
          <h1 className="auth-hero-title">RunAssistAI</h1>
          <p className="auth-hero-subtitle">
            Turn your daily runs into clear, beautiful data.
          </p>

          <div className="auth-hero-chips">
            <span className="auth-chip">Live run timer</span>
            <span className="auth-chip">Strava sync</span>
            <span className="auth-chip">AI training plan</span>
          </div>

          <div className="auth-hero-stats">
            <div className="auth-stat-card">
              <span className="auth-stat-label">Weekly distance</span>
              <span className="auth-stat-value">+42 km</span>
            </div>
            <div className="auth-stat-card">
              <span className="auth-stat-label">Consistency</span>
              <span className="auth-stat-value">5 / 7 days</span>
            </div>
          </div>
        </div>
      </div>

      <div className="auth-panel">
        <div className="auth-card-main">
          <div className="auth-header-row">
            <div>
              <h2 className="auth-title-main">Sign in</h2>
              <p className="auth-subtitle-main">
                Track, analyze, and plan your runs.
              </p>
            </div>
            <span className="auth-pill">Coach · Runner</span>
          </div>

          <form onSubmit={handleSubmit} className="auth-form-main">
            <label className="auth-label-main">
              Username
              <input
                className="auth-input-main"
                placeholder="Enter your username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </label>

            <label className="auth-label-main">
              Password
              <input
                type="password"
                className="auth-input-main"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>

            <div className="auth-label-main">
              <span>Login as</span>
              <div className="auth-role-toggle-main">
                <button
                  type="button"
                  className={
                    role === "runner"
                      ? "auth-role-chip-main auth-role-chip-main-active"
                      : "auth-role-chip-main"
                  }
                  onClick={() => setRole("runner")}
                >
                  Runner
                </button>
                <button
                  type="button"
                  className={
                    role === "coach"
                      ? "auth-role-chip-main auth-role-chip-main-active"
                      : "auth-role-chip-main"
                  }
                  onClick={() => setRole("coach")}
                >
                  Coach
                </button>
              </div>
            </div>

            {error && <div className="auth-error-main">{error}</div>}

            <button
              className="auth-button-main"
              type="submit"
              disabled={loading}
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>

          <div className="auth-footer-main">
            <span>Don&apos;t have an account?</span>
            <button
              type="button"
              className="auth-link-main"
              onClick={switchToRegister}
            >
              Create account
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
