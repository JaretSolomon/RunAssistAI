// src/components/RegisterForm.tsx
import React, { useState } from "react";
import type { UserRole } from "../api";

interface RegisterFormProps {
  onRegister: (username: string, role: UserRole) => Promise<void>;
  switchToLogin: () => void;
}

export const RegisterForm: React.FC<RegisterFormProps> = ({
  onRegister,
  switchToLogin,
}) => {
  const [username, setUsername] = useState("");
  const [role, setRole] = useState<UserRole>("runner");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim()) return;
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      await onRegister(username.trim(), role);
      setSuccess("Register success, please login.");
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
    <div className="auth-card">
      <h1 className="auth-title">RunAssistAI register</h1>
      <p className="auth-subtitle">Create your account</p>
      <form onSubmit={handleSubmit} className="auth-form">
        <label className="auth-label">
          Username
          <input
            className="auth-input"
            placeholder="Pick a username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </label>

        <div className="auth-label">
          <span>Account type</span>
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
        {success && <div className="auth-success">{success}</div>}
        <button className="auth-button" type="submit" disabled={loading}>
          {loading ? "Registering..." : "Register"}
        </button>
      </form>
      <div className="auth-footer">
        <span>Already have an account?</span>
        <button
          type="button"
          className="link-button"
          onClick={switchToLogin}
        >
          Back to login
        </button>
      </div>
    </div>
  );
};
