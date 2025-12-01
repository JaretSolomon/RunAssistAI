// src/components/CoachDashboard.tsx
import React, { useEffect, useState, useMemo } from "react";
import {
  User,
  BoundRunner,
  fetchCoachRunners,
  bindRunnerByCode,
  fetchDashboard,
  DashboardResponse,
  fetchTodayRunRecord,
  TodayRunRecordResponse,
  fetchRunningPlanCalendarApi,
  RunningPlanCalendarResponse,
} from "../api";
import { Card } from "./Card";
import { RunningPlan } from "./RunningPlan";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

// Keep consistent with API_BASE in api.ts: backend URL
const API_BASE = "http://localhost:8000";

interface CoachDashboardProps {
  coach: User;
}

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
  const daily = dashboard.daily.daily;

  return (
    <div style={{ marginTop: "1.5rem" }}>
      <div style={{ fontWeight: 600, marginBottom: 10, fontSize: 16 }}>
        Current runner summary {runner.name} (#{runner.runner_code}) · last{" "}
        {dashboard.daily.range_days} days
      </div>

      <div className="overview-grid" style={{ marginBottom: 16 }}>
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

      <div style={{ marginTop: 8 }}>
        <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 14 }}>
          Recent distance trend
        </div>
        <div className="chart-wrapper">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={daily}>
              <XAxis dataKey="date" tick={{ fontSize: 10 }} />
              <YAxis />
              <Tooltip />
              <Bar dataKey="distance_km" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

// ---- Coach notes types ----
interface CoachNote {
  id: string;
  runner_id: string;
  coach_id: string;
  coach_name?: string | null;
  content: string;
  created_at: string;
}

// ----------------- main component -----------------

export const CoachDashboard: React.FC<CoachDashboardProps> = ({ coach }) => {
  const [runners, setRunners] = useState<BoundRunner[]>([]);
  const [selectedRunnerId, setSelectedRunnerId] = useState<string | null>(null);
  const [bindCodeInput, setBindCodeInput] = useState<string>("");

  const [loadingRunners, setLoadingRunners] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [bindError, setBindError] = useState<string | null>(null);

  const [runnerDashboard, setRunnerDashboard] =
    useState<DashboardResponse | null>(null);
  const [runnerDashLoading, setRunnerDashLoading] = useState(false);
  const [runnerDashError, setRunnerDashError] = useState<string | null>(null);

  // Today record (runner perspective, read-only on coach page)
  const [todayRecord, setTodayRecord] =
    useState<TodayRunRecordResponse | null>(null);
  const [todayLoading, setTodayLoading] = useState(false);
  const [todayError, setTodayError] = useState<string | null>(null);

  // Today's planned total duration (minutes), used for goal
  const [todayGoalMinutes, setTodayGoalMinutes] = useState<number>(60);

  // Global timer so coach view can see time progressing when the runner is currently running
  const [nowTs, setNowTs] = useState<number>(Date.now());

  // notes
  const [notes, setNotes] = useState<CoachNote[]>([]);
  const [notesLoading, setNotesLoading] = useState(false);
  const [notesError, setNotesError] = useState<string | null>(null);

  const [newNote, setNewNote] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  // ---------- Global timer ----------
  useEffect(() => {
    const id = window.setInterval(() => {
      setNowTs(Date.now());
    }, 1000);
    return () => window.clearInterval(id);
  }, []);

  // ---------- load runners ----------
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

  // ---------- load dashboard ----------
  useEffect(() => {
    async function loadDash() {
      if (!selectedRunnerId) {
        setRunnerDashboard(null);
        return;
      }
      setRunnerDashLoading(true);
      setRunnerDashError(null);
      try {
        const data = await fetchDashboard(selectedRunnerId, 30, 6);
        setRunnerDashboard(data);
      } catch (e: any) {
        console.error(e);
        setRunnerDashError(e.message || "Failed to load runner dashboard");
      } finally {
        setRunnerDashLoading(false);
      }
    }
    loadDash();
  }, [selectedRunnerId]);

  // ---------- load today record ----------
  useEffect(() => {
    async function loadToday() {
      if (!selectedRunnerId) {
        setTodayRecord(null);
        return;
      }
      setTodayLoading(true);
      setTodayError(null);
      try {
        const rec = await fetchTodayRunRecord(selectedRunnerId);
        setTodayRecord(rec);
      } catch (e: any) {
        console.error(e);
        setTodayError(e.message || "Failed to load today record");
      } finally {
        setTodayLoading(false);
      }
    }
    loadToday();
  }, [selectedRunnerId]);

  // ---------- Compute today's goal (based on running plan) ----------
  useEffect(() => {
    async function loadGoal() {
      if (!selectedRunnerId) {
        setTodayGoalMinutes(60);
        return;
      }
      try {
        const now = new Date();
        const year = now.getFullYear();
        const month = now.getMonth() + 1;
        const todayStr = now.toISOString().slice(0, 10);

        const cal: RunningPlanCalendarResponse =
          await fetchRunningPlanCalendarApi(selectedRunnerId, year, month);

        const day = cal.days.find((d) => d.date === todayStr);
        if (day && day.plans.length > 0) {
          const totalMin = day.plans.reduce(
            (acc, p) => acc + p.duration_minutes,
            0
          );
          setTodayGoalMinutes(totalMin);
        } else {
          setTodayGoalMinutes(60);
        }
      } catch (e) {
        console.error(e);
        setTodayGoalMinutes(60);
      }
    }
    loadGoal();
  }, [selectedRunnerId]);

  // ---------- load notes ----------
  useEffect(() => {
    async function loadNotes() {
      if (!selectedRunnerId) {
        setNotes([]);
        return;
      }
      setNotesLoading(true);
      setNotesError(null);
      try {
        const res = await fetch(
          `${API_BASE}/api/runner/${selectedRunnerId}/notes`
        );
        if (!res.ok) {
          const text = await res.text();
          throw new Error(text || `Failed to fetch notes (HTTP ${res.status})`);
        }
        const data: CoachNote[] = await res.json();
        setNotes(data);
      } catch (e: any) {
        console.error(e);
        setNotes([]);
        setNotesError(e.message || "Failed to load notes");
      } finally {
        setNotesLoading(false);
      }
    }
    loadNotes();
  }, [selectedRunnerId]);

  // ---------- bind runner ----------
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

  // ---------- create note ----------
  async function handleSaveNote(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedRunnerId) return;

    const trimmed = newNote.trim();
    if (!trimmed) {
      setSaveError("Note content must not be empty.");
      return;
    }

    setSaveError(null);
    setSaveSuccess(null);
    setSavingNote(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/coach/${coach.id}/runner/${selectedRunnerId}/notes`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content: trimmed }),
        }
      );

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Failed to create note (HTTP ${res.status})`);
      }

      const created: CoachNote = await res.json();
      setNotes((prev) => [created, ...prev]);
      setNewNote("");
      setSaveSuccess("Note saved.");
    } catch (e: any) {
      console.error(e);
      setSaveError(e.message || "Failed to create note");
    } finally {
      setSavingNote(false);
    }
  }

  const selectedRunner =
    selectedRunnerId && runners.find((r) => r.id === selectedRunnerId);

  // ---------- Compute coach-side "today total duration" and finished status ----------
  const { totalDurationWithActive, totalDistanceKm, totalCalories, sessionsCount } =
    useMemo(() => {
      if (!todayRecord) {
        return {
          totalDurationWithActive: 0,
          totalDistanceKm: 0,
          totalCalories: 0,
          sessionsCount: 0,
        };
      }

      const baseDuration = todayRecord.today_summary.total_duration_seconds;
      const baseDistance = todayRecord.today_summary.total_distance_km;
      const baseCalories = todayRecord.today_summary.total_calories;
      const count = todayRecord.today_summary.sessions.length;

      const active = todayRecord.active_session;
      let activeElapsed = 0;

      if (active) {
        const base = active.elapsed_seconds ?? 0;
        if (active.is_paused) {
          activeElapsed = base;
        } else {
          const started = new Date(active.started_at).getTime();
          const extra = Math.max(0, Math.floor((nowTs - started) / 1000));
          activeElapsed = base + extra;
        }
      }

      return {
        totalDurationWithActive: baseDuration + activeElapsed,
        totalDistanceKm: baseDistance,
        totalCalories: baseCalories,
        sessionsCount: count,
      };
    }, [todayRecord, nowTs]);

  const goalSeconds = (todayGoalMinutes || 60) * 60;
  const progress = Math.max(
    0,
    Math.min(1, totalDurationWithActive / goalSeconds)
  );
  const finishedDash = progress >= 1;

  const radius = 90;
  const circumference = 2 * Math.PI * radius;
  const offsetDash = circumference * (1 - progress);

  return (
    <div className="layout-root">
      <aside className="sidebar">
        <div className="sidebar-logo-row">
          <div className="sidebar-logo">K</div>
        </div>
        <nav className="sidebar-nav">
          <div className="sidebar-item sidebar-item-active">
            Coach dashboard
          </div>
        </nav>
        <div className="sidebar-bottom">Logged in as {coach.name}</div>
      </aside>

      <main className="main">
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
                <div style={{ marginBottom: "1rem" }}>
                  <label style={{ marginRight: 8 }}>Runner:</label>
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

                <div style={{ marginBottom: "0.5rem" }}>
                  <label style={{ marginRight: 8 }}>Bind runner code:</label>
                  <input
                    type="number"
                    min={1}
                    max={10000}
                    value={bindCodeInput}
                    onChange={(e) => setBindCodeInput(e.target.value)}
                    style={{ width: 120, marginRight: 8 }}
                  />
                  <button onClick={handleBind}>Bind</button>
                </div>
                {bindError && (
                  <div style={{ color: "red", marginTop: 4 }}>{bindError}</div>
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

        {/* Runner today record */}
        <section className="grid grid-1">
          <Card title="Runner today record">
            {!selectedRunner && (
              <p>Bind and select a runner to see today&apos;s record.</p>
            )}

            {selectedRunner && (
              <>
                {todayLoading && <div>Loading today record...</div>}
                {todayError && (
                  <div className="error-text">{todayError}</div>
                )}

                {todayRecord && (
                  <div className="today-ring-layout">
                    <div className="today-ring-visual">
                      <div className="ring-svg-wrapper">
                        <svg className="ring-svg" viewBox="0 0 220 220">
                          <circle
                            className="ring-circle-bg"
                            cx="110"
                            cy="110"
                            r={radius}
                          />
                          <circle
                            className={
                              finishedDash
                                ? "ring-circle-progress ring-finished"
                                : "ring-circle-progress"
                            }
                            cx="110"
                            cy="110"
                            r={radius}
                            strokeDasharray={circumference}
                            strokeDashoffset={offsetDash}
                          />
                        </svg>
                        <div className="ring-center-text">
                          <div className="ring-main-value">
                            {formatDuration(totalDurationWithActive)}
                          </div>
                          <div className="ring-sub-label">
                            Today duration · goal {todayGoalMinutes} min
                          </div>
                          <div
                            style={{
                              marginTop: 4,
                              fontSize: 14,
                              fontWeight: 600,
                              color: finishedDash ? "#22c55e" : "#6b7280",
                            }}
                          >
                            {finishedDash ? "Finished" : "Unfinished"}
                          </div>
                        </div>
                      </div>

                      <div className="today-ring-stats">
                        <div className="stat-block">
                          <span className="stat-label">DATE</span>
                          <span className="stat-value">
                            {todayRecord.date}
                          </span>
                        </div>
                        <div className="stat-block">
                          <span className="stat-label">DISTANCE</span>
                          <span className="stat-value">
                            {totalDistanceKm.toFixed(2)} km
                          </span>
                        </div>
                        <div className="stat-block">
                          <span className="stat-label">CALORIES</span>
                          <span className="stat-value">
                            {totalCalories.toFixed(1)} kcal
                          </span>
                        </div>
                        <div className="stat-block">
                          <span className="stat-label">SESSIONS</span>
                          <span className="stat-value">{sessionsCount}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </Card>
        </section>

        {/* Runner plan + notes */}
        <section className="grid grid-1">
          <Card title="Runner plan">
            {selectedRunner ? (
              <>
                <p style={{ marginBottom: "1rem" }}>
                  Viewing plan for <strong>{selectedRunner.name}</strong> (
                  #{selectedRunner.runner_code})
                </p>

                <RunningPlan userId={selectedRunner.id} />

                {/* Coach -> Runner notes */}
                <div
                  style={{
                    marginTop: "2rem",
                    paddingTop: "1rem",
                    borderTop: "1px solid #eee",
                  }}
                >
                  <h3 style={{ marginBottom: "0.5rem", fontSize: 16 }}>
                    Runner notes
                  </h3>
                  <p
                    style={{
                      marginBottom: "0.5rem",
                      fontSize: 13,
                      color: "#666",
                    }}
                  >
                    Messages to{" "}
                    <strong>
                      {selectedRunner.name} (#{selectedRunner.runner_code})
                    </strong>{" "}
                    – only coach can write; runner can only read.
                  </p>

                  <form onSubmit={handleSaveNote}>
                    <textarea
                      style={{
                        width: "100%",
                        minHeight: 80,
                        resize: "vertical",
                        padding: 8,
                        boxSizing: "border-box",
                      }}
                      value={newNote}
                      onChange={(e) => setNewNote(e.target.value)}
                      disabled={savingNote}
                    />
                    <div
                      style={{
                        marginTop: 8,
                        display: "flex",
                        alignItems: "center",
                        gap: 12,
                        flexWrap: "wrap",
                      }}
                    >
                      <button type="submit" disabled={savingNote}>
                        {savingNote ? "Saving..." : "Send note"}
                      </button>
                      {saveError && (
                        <span style={{ fontSize: 12, color: "red" }}>
                          {saveError}
                        </span>
                      )}
                      {saveSuccess && (
                        <span style={{ fontSize: 12, color: "green" }}>
                          {saveSuccess}
                        </span>
                      )}
                    </div>
                  </form>

                  <div style={{ marginTop: "1.5rem" }}>
                    <div
                      style={{
                        fontWeight: 600,
                        marginBottom: 6,
                        fontSize: 14,
                      }}
                    >
                      Previous notes
                    </div>
                    {notesLoading && (
                      <div style={{ fontSize: 13, color: "#666" }}>
                        Loading notes...
                      </div>
                    )}
                    {notesError && (
                      <div style={{ fontSize: 13, color: "red" }}>
                        {notesError}
                      </div>
                    )}
                    {!notesLoading && !notesError && notes.length === 0 && (
                      <div style={{ fontSize: 13, color: "#777" }}>
                        No notes yet.
                      </div>
                    )}
                    {!notesLoading &&
                      !notesError &&
                      notes.length > 0 && (
                        <ul style={{ listStyle: "none", paddingLeft: 0 }}>
                          {notes.map((n) => (
                            <li
                              key={n.id}
                              style={{
                                padding: "6px 0",
                                borderBottom: "1px dashed #eee",
                              }}
                            >
                              <div
                                style={{
                                  fontSize: 12,
                                  color: "#999",
                                  marginBottom: 2,
                                }}
                              >
                                {n.coach_name ?? "Coach"} ·{" "}
                                {new Date(n.created_at).toLocaleString()}
                              </div>
                              <div style={{ whiteSpace: "pre-wrap" }}>
                                {n.content}
                              </div>
                            </li>
                          ))}
                        </ul>
                      )}
                  </div>
                </div>
              </>
            ) : (
              <p>Bind and select a runner to view their plan and notes.</p>
            )}
          </Card>
        </section>
      </main>
    </div>
  );
};
