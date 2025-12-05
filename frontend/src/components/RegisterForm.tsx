// src/components/RegisterForm.tsx
import React, { useState } from "react";
import type { UserRole } from "../api";

interface RegisterFormProps {
  onRegister: (username: string, password: string, role: UserRole) => Promise<void>;
  switchToLogin: () => void;
}

export const RegisterForm: React.FC<RegisterFormProps> = ({
  onRegister,
  switchToLogin,
}) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("runner");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim() || !password) return;
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      await onRegister(username.trim(), password, role);
      setSuccess("Register success, please sign in.");
      setTimeout(() => {
        switchToLogin();
      }, 800);
    } catch (err: any) {
      setError(err.message || "Register failed");
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
            Start with one account, grow with every kilometer.
          </p>

          <div className="auth-hero-chips">
            <span className="auth-chip">Smart scheduler</span>
            <span className="auth-chip">Coach tools</span>
            <span className="auth-chip">Runner insights</span>
          </div>

          <div className="auth-hero-stats">
            <div className="auth-stat-card">
              <span className="auth-stat-label">AI plans created</span>
              <span className="auth-stat-value">+128</span>
            </div>
            <div className="auth-stat-card">
              <span className="auth-stat-label">Total mileage</span>
              <span className="auth-stat-value">+3,240 km</span>
            </div>
          </div>
        </div>
      </div>

      <div className="auth-panel">
        <div className="auth-card-main">
          <div className="auth-header-row">
            <div>
              <h2 className="auth-title-main">Create account</h2>
              <p className="auth-subtitle-main">
                Choose your role and get your first plan.
              </p>
            </div>
            <span className="auth-pill">Sign up</span>
          </div>

          <form onSubmit={handleSubmit} className="auth-form-main">
            <label className="auth-label-main">
              Username
              <input
                className="auth-input-main"
                placeholder="Pick a username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </label>

            <label className="auth-label-main">
              Password
              <input
                type="password"
                className="auth-input-main"
                placeholder="Create a password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>

            <div className="auth-label-main">
              <span>Account type</span>
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
            {success && <div className="auth-success-main">{success}</div>}

            <button
              className="auth-button-main"
              type="submit"
              disabled={loading}
            >
              {loading ? "Registering..." : "Register"}
            </button>
          </form>

          <div className="auth-footer-main">
            <span>Already have an account?</span>
            <button
              type="button"
              className="auth-link-main"
              onClick={switchToLogin}
            >
              Back to sign in
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
