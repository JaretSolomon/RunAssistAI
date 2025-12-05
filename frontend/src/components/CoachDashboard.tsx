// src/components/CoachDashboard.tsx
import React, { useEffect, useState } from "react";
import {
  User,
  BoundRunner,
  fetchCoachRunners,
  bindRunnerByCode,
  fetchDashboard,
  DashboardResponse,
} from "../api";
import { Card } from "./Card";
import { RunningPlan } from "./RunningPlan";
import { Dashboard } from "./Dashboard";

interface CoachDashboardProps {
  coach: User;
}

/**
 * Format seconds to HH:MM:SS.
 */
function formatDuration(sec: number): string {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${pad(h)}:${pad(m)}:${pad(s)}`;
}

interface RunnerSummaryBlockProps {
  runner: BoundRunner;
  dashboard: DashboardResponse | null;
  loading: boolean;
  error: string | null;
}

/**
 * Compact overview block for the currently selected runner:
 * total sessions, duration, distance, calories.
 * The old "Recent distance trend" chart has been removed.
 */
const RunnerSummaryBlock: React.FC<RunnerSummaryBlockProps> = ({
  runner,
  dashboard,
  loading,
  error,
}) => {
  if (loading && !dashboard) {
    return <div>Loading current runner summary...</div>;
  }
  if (error) {
    return <div className="error-text">{error}</div>;
  }
  if (!dashboard) return null;

  const overview = dashboard.overview;

  return (
    <div className="coach-runner-summary">
      <div className="coach-runner-summary-title">
        Current runner summary {runner.name} (#{runner.runner_code})
      </div>

      <div className="overview-grid coach-overview-grid">
        <div className="overview-item">
          <div className="overview-label">Total sessions</div>
          <div className="overview-value">{overview.total_sessions}</div>
        </div>
        <div className="overview-item">
          <div className="overview-label">Total duration</div>
          <div className="overview-value">
            {formatDuration(overview.total_duration_seconds)}
          </div>
        </div>
        <div className="overview-item">
          <div className="overview-label">Total distance</div>
          <div className="overview-value">
            {overview.total_distance_km.toFixed(1)} km
          </div>
        </div>
        <div className="overview-item">
          <div className="overview-label">Estimated calories</div>
          <div className="overview-value">
            {overview.estimated_calories.toFixed(0)} kcal
          </div>
        </div>
      </div>
    </div>
  );
};

// ----------------- main component -----------------

export const CoachDashboard: React.FC<CoachDashboardProps> = ({ coach }) => {
  // Runner list and selection
  const [runners, setRunners] = useState<BoundRunner[]>([]);
  const [selectedRunnerId, setSelectedRunnerId] = useState<string | null>(null);
  const [bindCodeInput, setBindCodeInput] = useState<string>("");

  const [loadingRunners, setLoadingRunners] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [bindError, setBindError] = useState<string | null>(null);

  // Dashboard overview for selected runner
  const [runnerDashboard, setRunnerDashboard] =
    useState<DashboardResponse | null>(null);
  const [runnerDashLoading, setRunnerDashLoading] = useState(false);
  const [runnerDashError, setRunnerDashError] = useState<string | null>(null);

  // Range configuration for the embedded Activity Dashboard
  const [days, setDays] = useState(30);
  const [weeks, setWeeks] = useState(6);

  // ---------- Load runners list for coach ----------

  useEffect(() => {
    async function loadRunners() {
      setLoadingRunners(true);
      setGlobalError(null);
      try {
        const list = await fetchCoachRunners(coach.id);
        setRunners(list);
        if (list.length > 0) {
          setSelectedRunnerId(list[0].id);
        } else {
          setSelectedRunnerId(null);
        }
      } catch (e: any) {
        console.error(e);
        setGlobalError(e.message || "Failed to fetch coach runners");
      } finally {
        setLoadingRunners(false);
      }
    }
    loadRunners();
  }, [coach.id]);

  // ---------- Load dashboard for selected runner ----------

  useEffect(() => {
    async function loadDash() {
      if (!selectedRunnerId) {
        setRunnerDashboard(null);
        return;
      }
      setRunnerDashLoading(true);
      setRunnerDashError(null);
      try {
        const data = await fetchDashboard(selectedRunnerId, days, weeks);
        setRunnerDashboard(data);
      } catch (e: any) {
        console.error(e);
        setRunnerDashError(e.message || "Failed to load runner dashboard");
      } finally {
        setRunnerDashLoading(false);
      }
    }
    loadDash();
  }, [selectedRunnerId, days, weeks]);

  // ---------- Bind runner by code ----------

  async function handleBind() {
    setBindError(null);
    const code = Number(bindCodeInput);
    if (!code || Number.isNaN(code)) {
      setBindError("Please input a valid runner code (1–10000).");
      return;
    }

    try {
      const runner = await bindRunnerByCode(coach.id, code);
      const newList = await fetchCoachRunners(coach.id);
      setRunners(newList);
      setSelectedRunnerId(runner.id);
      setBindCodeInput("");
    } catch (e: any) {
      console.error(e);
      setBindError(e.message || "Failed to bind runner");
    }
  }

  const selectedRunner =
    selectedRunnerId && runners.find((r) => r.id === selectedRunnerId);

  function handleLogout() {
    localStorage.clear();
    sessionStorage.clear();
    window.location.href = "/"; // adjust if your login route is different
  }

  return (
    <div className="layout-root">
      {/* Sidebar – shared with runner dashboard style */}
      <aside className="sidebar">
        <div className="sidebar-logo-row">
          <div className="sidebar-logo">R</div>
        </div>

        <nav className="sidebar-nav">
          <div className="sidebar-item sidebar-item-active">
            Coach dashboard
          </div>
        </nav>

        {/* Footer area pinned to bottom: logout + user label */}
        <div className="sidebar-footer">
          <button className="sidebar-logout" onClick={handleLogout}>
            Logout
          </button>
          <div className="sidebar-bottom">Logged in as {coach.name}</div>
        </div>
      </aside>

      {/* Main body uses terminal-mode theme to match runner dashboard */}
      <main className="main terminal-mode">
        <header className="main-header">
          <div className="main-title">Coach dashboard</div>
        </header>

        {globalError && (
          <div className="dash-error-banner">{globalError}</div>
        )}

        {/* Runner selection & binding */}
        <section className="grid grid-1">
          <Card title="Runner selection & binding">
            {loadingRunners && <div>Loading runners...</div>}

            {!loadingRunners && (
              <>
                <div className="coach-runner-select-row">
                  <label className="coach-inline-label">Runner:</label>
                  <select
                    value={selectedRunnerId ?? ""}
                    onChange={(e) =>
                      setSelectedRunnerId(e.target.value || null)
                    }
                  >
                    {runners.length === 0 && (
                      <option value="">No runners bound</option>
                    )}
                    {runners.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name} (#{r.runner_code})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="coach-runner-bind-row">
                  <label className="coach-inline-label">
                    Bind runner code:
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={10000}
                    value={bindCodeInput}
                    onChange={(e) => setBindCodeInput(e.target.value)}
                    className="coach-bind-input"
                  />
                  <button onClick={handleBind}>Bind</button>
                </div>
                {bindError && (
                  <div className="error-text" style={{ marginTop: 4 }}>
                    {bindError}
                  </div>
                )}

                {selectedRunner && (
                  <RunnerSummaryBlock
                    runner={selectedRunner}
                    dashboard={runnerDashboard}
                    loading={runnerDashLoading}
                    error={runnerDashError}
                  />
                )}

                {!selectedRunner && runners.length === 0 && (
                  <p style={{ marginTop: "1rem" }}>
                    No runners yet. Bind a runner by code to start.
                  </p>
                )}
              </>
            )}
          </Card>
        </section>

        {/* ❌ Removed: separate "Runner today record" ring section */}

        {/* Embedded runner Activity Dashboard – reuse full runner dashboard UI */}
        {selectedRunner && (
          <section className="grid grid-1">
            <Card title="Runner activity dashboard">
              {runnerDashLoading && !runnerDashboard && (
                <div className="dash-loading">
                  Loading runner dashboard...
                </div>
              )}
              {runnerDashError && (
                <div className="dash-error-banner">
                  Failed to load runner dashboard: {runnerDashError}
                </div>
              )}
              <Dashboard
                embedded
                data={runnerDashboard}
                username={selectedRunner.name}
                userId={selectedRunner.id}
                days={days}
                weeks={weeks}
                onChangeDays={setDays}
                onChangeWeeks={setWeeks}
                runnerCode={selectedRunner.runner_code}
              />
            </Card>
          </section>
        )}

        {/* Runner plan – reuse RunningPlan with coachId to enable coach notes */}
        <section className="grid grid-1">
          <Card title="Runner plan">
            {!selectedRunner && (
              <p>Bind and select a runner to view their plan and notes.</p>
            )}

            {selectedRunner && (
              <>
                <p className="coach-plan-intro">
                  Viewing plan for <strong>{selectedRunner.name}</strong> (
                  #{selectedRunner.runner_code})
                </p>
                <RunningPlan userId={selectedRunner.id} coachId={coach.id} />
              </>
            )}
          </Card>
        </section>
      </main>
    </div>
  );
};
