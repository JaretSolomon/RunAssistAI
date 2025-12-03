// src/components/Dashboard.tsx
import React, { useState, useEffect, useMemo } from "react";
import {
  DashboardResponse,
  TodayRunRecordResponse,
  fetchTodayRunRecord,
} from "../api";
import { Card } from "./Card";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";
import { RunRecord } from "./RunRecord";
import { RunningPlan } from "./RunningPlan";

type MainView = "overview" | "runrecord" | "runningplan";

interface DashboardProps {
  data: DashboardResponse | null;
  username: string;
  userId: string;
  days: number;
  weeks: number;
  onChangeDays: (d: number) => void;
  onChangeWeeks: (w: number) => void;
  runnerCode?: number | null;
}

export const Dashboard: React.FC<DashboardProps> = ({
  data,
  username,
  userId,
  days,
  weeks,
  onChangeDays,
  onChangeWeeks,
  runnerCode,
}) => {
  const [view, setView] = useState<MainView>("overview");

  const overview = data?.overview;
  const daily = data?.daily.daily ?? [];
  const timeOfDay = data?.time_of_day.time_of_day_distribution ?? [];
  const weeklyLoad = data?.training_load.weeks ?? [];

  // ---------- Shared formatting functions ----------
  function formatDuration(totalSeconds: number): string {
    const h = Math.floor(totalSeconds / 3600);
    const m = Math.floor((totalSeconds % 3600) / 60);
    const s = totalSeconds % 60;
    const pad = (n: number) => n.toString().padStart(2, "0");
    return `${pad(h)}:${pad(m)}:${pad(s)}`;
  }

  function formatPace(sec: number | null): string {
    if (sec == null || !isFinite(sec)) return "--";
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    const pad = (n: number) => n.toString().padStart(2, "0");
    return `${m}'${pad(s)}"/km`;
  }

  // ---------- States needed for the Today ring at bottom-right ----------

  const [todayRecord, setTodayRecord] = useState<TodayRunRecordResponse | null>(
    null
  );
  const [todayError, setTodayError] = useState<string | null>(null);
  const [nowTs, setNowTs] = useState(() => Date.now());

  // Let the time inside the ring tick every second
  useEffect(() => {
    const id = window.setInterval(() => setNowTs(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  // Fetch “today’s run record”
  useEffect(() => {
    async function loadToday() {
      try {
        const d = await fetchTodayRunRecord(userId);
        setTodayRecord(d);
        setTodayError(null);
      } catch (e: any) {
        console.error(e);
        setTodayError(e.message || "Failed to load today record");
      }
    }
    loadToday();
  }, [userId]);

  // How long the current session has been running (for today ring)
  const activeElapsedSec = useMemo(() => {
    if (!todayRecord?.active_session) return 0;
    const base = todayRecord.active_session.elapsed_seconds ?? 0;

    if (todayRecord.active_session.is_paused) {
      return base;
    }
    const started = new Date(
      todayRecord.active_session.started_at
    ).getTime();
    const extra = Math.max(0, Math.floor((nowTs - started) / 1000));
    return base + extra;
  }, [nowTs, todayRecord?.active_session]);

  const totalDurationWithActive =
    (todayRecord?.today_summary.total_duration_seconds ?? 0) +
    activeElapsedSec;

  const totalDistanceKmDash = todayRecord?.today_summary.total_distance_km ?? 0;
  const totalCaloriesDash = todayRecord?.today_summary.total_calories ?? 0;
  const sessionsCountDash =
    todayRecord?.today_summary.sessions.length ?? 0;

  const avgPaceSecPerKmDash = useMemo(() => {
    if (!totalDistanceKmDash || totalDistanceKmDash <= 0) return null;
    return Math.floor(totalDurationWithActive / totalDistanceKmDash);
  }, [totalDurationWithActive, totalDistanceKmDash]);

  // ★ The goal duration here is currently a fixed 60 min;
  // If you have “today's total minutes from running plan”, replace 60 with that variable.
  const goalMinutesDash = 60;
  const goalSecondsDash = goalMinutesDash * 60;

  const progressDash = Math.max(
    0,
    Math.min(1, totalDurationWithActive / goalSecondsDash)
  );
  const radiusDash = 90;
  const circumferenceDash = 2 * Math.PI * radiusDash;
  const offsetDash = circumferenceDash * (1 - progressDash);
  const finishedDash = totalDurationWithActive >= goalSecondsDash;

  const logoRightLabel =
    runnerCode !== null && runnerCode !== undefined
      ? `#${runnerCode}`
      : undefined;

  return (
    <div className="layout-root">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo-row">
          <div className="sidebar-logo">K</div>
          {logoRightLabel && (
            <div className="sidebar-runner-code">{logoRightLabel}</div>
          )}
        </div>
        <nav className="sidebar-nav">
          <div
            className={`sidebar-item ${
              view === "overview" ? "sidebar-item-active" : ""
            }`}
            onClick={() => setView("overview")}
          >
            Dashboard
          </div>
          <div
            className={`sidebar-item ${
              view === "runrecord" ? "sidebar-item-active" : ""
            }`}
            onClick={() => setView("runrecord")}
          >
            Run record
          </div>
          <div
            className={`sidebar-item ${
              view === "runningplan" ? "sidebar-item-active" : ""
            }`}
            onClick={() => setView("runningplan")}
          >
            Running plan
          </div>
        </nav>
        <div className="sidebar-bottom">Logged in as {username}</div>
      </aside>

      {/* Main content */}
      <main className="main">
        <header className="main-header">
          <div className="main-title">Activity Dashboard</div>
          {view === "overview" && (
            <div className="main-filters">
              <label>
                Range (days):
                <select
                  value={days}
                  onChange={(e) => onChangeDays(Number(e.target.value))}
                >
                  <option value={7}>Last 7 days</option>
                  <option value={30}>Last 30 days</option>
                  <option value={365}>Last year</option>
                </select>
              </label>
              <label>
                Training load weeks:
                <select
                  value={weeks}
                  onChange={(e) => onChangeWeeks(Number(e.target.value))}
                >
                  <option value={4}>Last 4 weeks</option>
                  <option value={6}>Last 6 weeks</option>
                  <option value={8}>Last 8 weeks</option>
                </select>
              </label>
            </div>
          )}
        </header>

        {/* Overview */}
        {view === "overview" && (
          <>
            {data && overview ? (
              <>
                <section className="grid grid-3">
                  <Card title="Summary">
                    <div className="overview-grid">
                      <div className="overview-item">
                        <div className="overview-label">Total sessions</div>
                        <div className="overview-value">
                          {overview.total_sessions}
                        </div>
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
                        <div className="overview-label">
                          Estimated calories
                        </div>
                        <div className="overview-value">
                          {overview.estimated_calories.toFixed(0)} kcal
                        </div>
                      </div>
                    </div>
                  </Card>

                  <Card title="Recent distance trend">
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
                  </Card>

                  <Card title="Time-of-day distribution">
                    <div className="tod-list">
                      {timeOfDay.map((item) => (
                        <div key={item.slot} className="tod-row">
                          <div className="tod-label">
                            {slotToLabel(item.slot)} ({item.sessions})
                          </div>
                          <div className="tod-bar">
                            <div
                              className="tod-bar-inner"
                              style={{ width: `${item.percentage * 100}%` }}
                            />
                          </div>
                          <div className="tod-percent">
                            {(item.percentage * 100).toFixed(1)}%
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                </section>

                <section className="grid grid-2">
                  <Card title="Weekly training load">
                    <div className="chart-wrapper">
                      <ResponsiveContainer width="100%" height={240}>
                        <LineChart data={weeklyLoad}>
                          <XAxis
                            dataKey="week_label"
                            tick={{ fontSize: 10 }}
                          />
                          <YAxis />
                          <Tooltip />
                          <Line
                            type="monotone"
                            dataKey="training_load"
                            strokeWidth={2}
                            dot={{ r: 3 }}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="training-summary">
                      <div>
                        Current week load:{" "}
                        <strong>{data.training_load.current_week_load}</strong>
                      </div>
                      <div>
                        Average weekly load:{" "}
                        <strong>{data.training_load.average_week_load}</strong>
                      </div>
                    </div>
                  </Card>

                  {/* Bottom-right Today run record (ring version) */}
                  <Card title="Today run record">
                    {!todayRecord ? (
                      todayError ? (
                        <div className="error-text">{todayError}</div>
                      ) : (
                        <div>Loading...</div>
                      )
                    ) : (
                      <div className="today-ring-summary-root">
                        <div className="today-ring-layout">
                          {/* Left side ring */}
                          <div className="today-ring-visual">
                            <div className="ring-svg-wrapper">
                              <svg
                                className="ring-svg"
                                viewBox="0 0 220 220"
                              >
                                <circle
                                  className="ring-circle-bg"
                                  cx="110"
                                  cy="110"
                                  r={radiusDash}
                                />
                                <circle
                                  className={
                                    finishedDash
                                      ? "ring-circle-progress ring-finished"
                                      : "ring-circle-progress"
                                  }
                                  cx="110"
                                  cy="110"
                                  r={radiusDash}
                                  strokeDasharray={circumferenceDash}
                                  strokeDashoffset={offsetDash}
                                />
                              </svg>
                              <div className="ring-center-text">
                                <div className="ring-main-value">
                                  {formatDuration(totalDurationWithActive)}
                                </div>
                                <div className="ring-sub-label">
                                  Today duration · goal {goalMinutesDash} min
                                </div>
                                <div
                                  className={
                                    finishedDash
                                      ? "ring-status-text finished"
                                      : "ring-status-text"
                                  }
                                >
                                  {finishedDash ? "Finished" : "Unfinished"}
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Right side small stats */}
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
                                {totalDistanceKmDash.toFixed(2)} km
                              </span>
                            </div>
                            <div className="stat-block">
                              <span className="stat-label">CALORIES</span>
                              <span className="stat-value">
                                {totalCaloriesDash.toFixed(1)} kcal
                              </span>
                            </div>
                            <div className="stat-block">
                              <span className="stat-label">SESSIONS</span>
                              <span className="stat-value">
                                {sessionsCountDash}
                              </span>
                            </div>
                            <div className="stat-block">
                              <span className="stat-label">AVG PACE</span>
                              <span className="stat-value">
                                {formatPace(avgPaceSecPerKmDash)}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </Card>
                </section>
              </>
            ) : (
              <section className="grid">
                <Card title="Summary">
                  <p>No dashboard data yet.</p>
                </Card>
              </section>
            )}
          </>
        )}

        {/* Run record */}
        {view === "runrecord" && (
          <section>
            <RunRecord userId={userId} />
          </section>
        )}

        {/* Running plan */}
        {view === "runningplan" && (
          <section>
            <RunningPlan userId={userId} />
          </section>
        )}
      </main>
    </div>
  );
};

function slotToLabel(slot: string): string {
  switch (slot) {
    case "morning":
      return "Morning";
    case "forenoon":
      return "Late morning";
    case "afternoon":
      return "Afternoon";
    case "evening":
      return "Evening";
    case "night":
      return "Night";
    default:
      return slot;
  }
}
