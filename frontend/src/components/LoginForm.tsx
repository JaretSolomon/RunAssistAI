// src/components/LoginForm.tsx
import React, { useState } from "react";
import type { UserRole } from "../api";

interface LoginFormProps {
  onLogin: (username: string, role: UserRole) => Promise<void>;
  switchToRegister: () => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({
  onLogin,
  switchToRegister,
}) => {
  const [username, setUsername] = useState("");
  const [role, setRole] = useState<UserRole>("runner");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await onLogin(username.trim(), role);
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-card">
      <h1 className="auth-title">RunAssistAI</h1>
      <p className="auth-subtitle">Sign in to your account</p>
      <form onSubmit={handleSubmit} className="auth-form">
        <label className="auth-label">
          Username
          <input
            className="auth-input"
            placeholder="Enter your username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </label>

        <div className="auth-label">
          <span>Login as</span>
          <div className="auth-role-toggle">
            <label>
              <input
                type="radio"
                name="role"
                value="runner"
                checked={role === "runner"}
                onChange={() => setRole("runner")}
              />
              Runner
            </label>
            <label>
              <input
                type="radio"
                name="role"
                value="coach"
                checked={role === "coach"}
                onChange={() => setRole("coach")}
              />
              Coach
            </label>
          </div>
        </div>

        {error && <div className="auth-error">{error}</div>}
        <button className="auth-button" type="submit" disabled={loading}>
          {loading ? "Logging in..." : "Login"}
        </button>
      </form>
      <div className="auth-footer">
        <span>No account?</span>
        <button
          type="button"
          className="link-button"
          onClick={switchToRegister}
        >
          Register
        </button>
      </div>
    </div>
  );
};
