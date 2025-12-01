// src/components/RunRecord.tsx
import React, { useEffect, useState, useMemo } from "react";
import {
  TodayRunRecordResponse,
  fetchTodayRunRecord,
  setCaloriesPerHourApi,
  startRunApi,
  stopRunApi,
  pauseRunApi,
  resumeRunApi,
} from "../api";
import { Card } from "./Card";

interface RunRecordProps {
  userId: string;
}

export const RunRecord: React.FC<RunRecordProps> = ({ userId }) => {
  const [data, setData] = useState<TodayRunRecordResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [cphInput, setCphInput] = useState<number | "">("");
  const [totalDistanceInput, setTotalDistanceInput] = useState<number | "">("");

  // Only responsible for "current time", independent of whether the user is running
  const [nowTs, setNowTs] = useState<number>(Date.now());

  // ----------------- Generic timer: refresh every 1s when component is mounted -----------------
  useEffect(() => {
    const id = window.setInterval(() => {
      setNowTs(Date.now());
    }, 1000);
    return () => window.clearInterval(id);
  }, []);

  // ----------------------------------------------------------------------

  useEffect(() => {
    loadToday();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  async function loadToday() {
    setLoading(true);
    setError(null);
    try {
      const d = await fetchTodayRunRecord(userId);
      setData(d);
      setCphInput(d.settings.calories_per_hour);
    } catch (e: any) {
      console.error(e);
      setError(e.message || "Failed to load today record");
    } finally {
      setLoading(false);
    }
  }

  async function handleUpdateCph() {
    if (cphInput === "" || cphInput <= 0) {
      alert("Calories per hour must be > 0");
      return;
    }
    try {
      await setCaloriesPerHourApi(userId, Number(cphInput));
      await loadToday();
    } catch (e: any) {
      alert(e.message || "Failed to update settings");
    }
  }

  async function handleStartRun() {
    try {
      await startRunApi(userId);
      await loadToday();
    } catch (e: any) {
      alert(e.message || "Failed to start run");
    }
  }

  async function handlePauseRun() {
    try {
      await pauseRunApi(userId);  // Backend only performs validation

      setData((prev) => {
        if (!prev || !prev.active_session) return prev;

        return {
          ...prev,
          active_session: {
            ...prev.active_session,
            elapsed_seconds: activeElapsedSec,  // ✔ Lock in the current accumulated time
            is_paused: true,
          },
        };
      });
    } catch (e: any) {
      alert(e.message || "Failed to pause run");
    }
  }

  async function handleResumeRun() {
    try {
      await resumeRunApi(userId);

      setData((prev) => {
        if (!prev || !prev.active_session) return prev;

        return {
          ...prev,
          active_session: {
            ...prev.active_session,
            is_paused: false,
            started_at: new Date().toISOString(),  // ✔ Recalculate extra time starting from now
          },
        };
      });
    } catch (e: any) {
      alert(e.message || "Failed to resume run");
    }
  }

  async function handleStopRun() {
    try {
      const dist =
        totalDistanceInput === "" ? undefined : Number(totalDistanceInput);

      // ⭐ Send the current session's accumulated seconds to the backend so finish_session uses elapsed_seconds
      await stopRunApi(userId, dist, activeElapsedSec || 0);

      setTotalDistanceInput("");
      await loadToday();
    } catch (e: any) {
      alert(e.message || "Failed to stop run");
    }
  }

  function formatDuration(sec: number): string {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    const pad = (n: number) => n.toString().padStart(2, "0");
    return `${pad(h)}:${pad(m)}:${pad(s)}`;
  }

  // How long the current session has been running:
  // Backend keeps the accumulated valid time in active_session.elapsed_seconds
  // Frontend only adds the "current segment" extra time when is_paused === false
  const activeElapsedSec = useMemo(() => {
    if (!data?.active_session) return 0;

    const base = data.active_session.elapsed_seconds ?? 0;

    if (data.active_session.is_paused) {
      // Paused: only use the accumulated value, time will no longer increase
      return base;
    }

    const started = new Date(data.active_session.started_at).getTime();
    const extra = Math.max(0, Math.floor((nowTs - started) / 1000));
    return base + extra;
  }, [nowTs, data?.active_session]);

  // Today's total time = value in summary + real-time portion of the current session
  const totalDurationWithActive =
    (data?.today_summary.total_duration_seconds ?? 0) + activeElapsedSec;

  const totalDistanceKm = data?.today_summary.total_distance_km ?? 0;
  const totalCalories = data?.today_summary.total_calories ?? 0;
  const sessionsCount = data?.today_summary.sessions.length ?? 0;

  // Average pace: total time / total distance
  const avgPaceSecPerKm = useMemo(() => {
    if (!totalDistanceKm || totalDistanceKm <= 0) return null;
    return Math.floor(totalDurationWithActive / totalDistanceKm);
  }, [totalDurationWithActive, totalDistanceKm]);

  function formatPace(sec: number | null): string {
    if (sec == null || !isFinite(sec)) return "--";
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    const pad = (n: number) => n.toString().padStart(2, "0");
    return `${m}'${pad(s)}"/km`;
  }

  // Ring progress bar: goal duration from backend (seconds)
  const goalSeconds = data?.today_goal_seconds ?? 0;
  const isGoalReached = goalSeconds > 0 && totalDurationWithActive >= goalSeconds;
  const progress = Math.max(
    0,
    Math.min(1, totalDurationWithActive / goalSeconds)
  );
  const radius = 90;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - progress);

  const active = data?.active_session;
  const isPaused = !!active?.is_paused;

  return (
    <div className="runrecord-root">
      <Card title="Today run record">
        {loading && <div>Loading...</div>}
        {error && <div className="error-text">{error}</div>}

        {data && (
          <>
            {/* Ring + stats */}
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
                      className={`ring-circle-progress ${
                        isGoalReached ? "ring-finished" : ""
                      }`}
                      cx="110"
                      cy="110"
                      r={radius}
                      strokeDasharray={circumference}
                      strokeDashoffset={offset}
                    />
                  </svg>
                  <div className="ring-center-text">
                    <div className="ring-main-value">
                      {formatDuration(totalDurationWithActive)}
                    </div>
                    <div className="ring-sub-label">
                      Today duration · goal {Math.round(goalSeconds / 60)} min
                    </div>
                    <div
                      className={`ring-status ${
                        isGoalReached
                          ? "ring-status-finished"
                          : "ring-status-unfinished"
                      }`}
                    >
                      {isGoalReached ? "Finished" : "Unfinished"}
                    </div>
                  </div>
                </div>

                <div className="today-ring-stats">
                  <div className="stat-block">
                    <span className="stat-label">DATE</span>
                    <span className="stat-value">{data.date}</span>
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
                  <div className="stat-block">
                    <span className="stat-label">AVG PACE</span>
                    <span className="stat-value">
                      {formatPace(avgPaceSecPerKm)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Control area */}
              <div className="today-ring-controls">
                <div>
                  <div className="runrecord-buttons-row">
                    <div className="runrecord-buttons">
                      {!active && (
                        <button
                          className="runrecord-btn start"
                          onClick={handleStartRun}
                        >
                          Start a run
                        </button>
                      )}

                      {active && !isPaused && (
                        <>
                          <button
                            className="runrecord-btn"
                            onClick={handlePauseRun}
                          >
                            Pause
                          </button>
                          <button
                            className="runrecord-btn stop"
                            onClick={handleStopRun}
                          >
                            Stop
                          </button>
                        </>
                      )}

                      {active && isPaused && (
                        <>
                          <button
                            className="runrecord-btn start"
                            onClick={handleResumeRun}
                          >
                            Resume
                          </button>
                          <button
                            className="runrecord-btn stop"
                            onClick={handleStopRun}
                          >
                            Stop
                          </button>
                        </>
                      )}
                    </div>

                    {active && (
                      <div className="runrecord-live-timer">
                        Current session: {formatDuration(activeElapsedSec || 0)}{" "}
                        {isPaused && "(paused)"}
                      </div>
                    )}
                  </div>

                  {active && (
                    <div style={{ marginTop: 8 }}>
                      <label style={{ fontSize: 12 }}>
                        Distance of this run (km, optional)
                        <input
                          type="number"
                          className="runrecord-input small"
                          value={totalDistanceInput}
                          onChange={(e) =>
                            setTotalDistanceInput(
                              e.target.value === ""
                                ? ""
                                : Number(e.target.value)
                            )
                          }
                        />
                      </label>
                    </div>
                  )}
                </div>

                <div className="calories-setting">
                  <label>
                    <span>Calories per hour</span>
                    <input
                      type="number"
                      value={cphInput}
                      onChange={(e) =>
                        setCphInput(
                          e.target.value === "" ? "" : Number(e.target.value)
                        )
                      }
                    />
                  </label>
                  <button
                    className="runrecord-btn small"
                    type="button"
                    onClick={handleUpdateCph}
                  >
                    Update
                  </button>
                </div>
              </div>
            </div>

            {/* Today sessions list */}
            <div style={{ marginTop: 24 }}>
              <h4 style={{ marginBottom: 8, fontSize: 14 }}>Today sessions</h4>
              {data.today_summary.sessions.length === 0 ? (
                <div className="runrecord-placeholder">No sessions today.</div>
              ) : (
                <div className="sessions-table-wrapper">
                  <table className="sessions-table">
                    <thead>
                      <tr>
                        <th>Start</th>
                        <th>End</th>
                        <th>Duration</th>
                        <th>Distance (km)</th>
                        <th>Calories</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.today_summary.sessions.map((s) => (
                        <tr key={s.id}>
                          <td>{s.started_at}</td>
                          <td>{s.ended_at ?? "--"}</td>
                          <td>{formatDuration(s.total_duration_seconds)}</td>
                          <td>{s.total_distance_km.toFixed(2)}</td>
                          <td>{s.total_calories.toFixed(1)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}
      </Card>
    </div>
  );
};
