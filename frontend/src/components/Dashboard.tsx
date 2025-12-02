// src/components/Dashboard.tsx
import React, { useState, useEffect, useMemo } from "react";
import {
  DashboardResponse,
  TodayRunRecordResponse,
  fetchTodayRunRecord,
  fetchStravaStatus,
  requestStravaLink,
  StravaStatusResponse,
  fetchStravaRuns,
  StravaRecentRun,
  fetchStravaRunDetail,
  StravaRunDetail,
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
  ComposedChart,
  ReferenceLine,
  AreaChart,
  Area,
  Cell,
  CartesianGrid,
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
  const [stravaStatus, setStravaStatus] = useState<StravaStatusResponse | null>(
    null
  );
  const [stravaLoading, setStravaLoading] = useState(false);
  const [stravaError, setStravaError] = useState<string | null>(null);
  const [stravaRuns, setStravaRuns] = useState<StravaRecentRun[]>([]);
  const [stravaRunsError, setStravaRunsError] = useState<string | null>(null);
  const [selectedStravaRunId, setSelectedStravaRunId] = useState<
    number | null
  >(null);
  const [stravaRunDetail, setStravaRunDetail] = useState<StravaRunDetail | null>(
    null
  );
  const [stravaDetailError, setStravaDetailError] = useState<string | null>(null);
  const [stravaSyncStamp, setStravaSyncStamp] = useState(0);

  const mainClassName =
    view === "overview" ? "main terminal-mode" : "main";

  const normalizedRuns = useMemo(() => {
    return stravaRuns
      .map((run) => ({
        id: run.id,
        started_at: run.started_at || run.recorded_at || "",
        distance_km: run.distance_km || 0,
        duration_seconds: run.duration_seconds || 0,
      }))
      .filter((entry) => entry.started_at);
  }, [stravaRuns]);

  const paceSeries = useMemo(() => {
    // Use the same 5 runs as distanceCaloriesSeries to ensure they match
    return stravaRuns.slice(0, 5).map((run, idx) => ({
      label: `Run ${idx + 1}`,
      pace:
        run.distance_km > 0
          ? run.duration_seconds / run.distance_km
          : undefined,
      cadence: run.cadence ?? null,
      timestamp: run.recorded_at
        ? new Date(run.recorded_at).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })
        : "",
    }));
  }, [stravaRuns]);

  const tickerItems = useMemo(() => {
    const base = normalizedRuns.slice(0, 10);
    if (!base.length) {
      return [
        {
          id: "awaiting",
          label: "Awaiting telemetry...",
          positive: true,
        },
      ];
    }
    return base.map((run) => {
      const pace =
        run.distance_km > 0
          ? run.duration_seconds / run.distance_km
          : null;
      const date = new Date(run.started_at);
      return {
        id: run.id,
        label: `${date.toLocaleDateString()} ${run.distance_km.toFixed(2)} km · ${
          pace ? formatPace(pace) : "--"
        }`,
        positive: pace ? pace <= 300 : true,
      };
    });
  }, [normalizedRuns]);

  const sparklineSeries = useMemo(() => {
    if (stravaRunDetail) {
      const splits = stravaRunDetail.splits.length
        ? stravaRunDetail.splits
        : Array.from({ length: 6 }).map((_, idx) => ({
            pace_seconds:
              stravaRunDetail.average_pace_seconds || 300 + idx * 5,
            cadence: stravaRunDetail.average_cadence || null,
            index: idx + 1,
          }));
      const buildSeries = (
        label: string,
        values: number[],
        suffix: string,
        format?: (value: number) => string
      ) => {
        const data = values.map((value, idx) => ({
          index: idx,
          value,
        }));
        return {
          label,
          suffix,
          data,
          latest: values[values.length - 1] ?? null,
          format,
        };
      };
      // Use actual split data when available
      const paceValues = splits.map(
        (split) => split.pace_seconds ?? stravaRunDetail.average_pace_seconds ?? 0
      );
      const cadenceValues = splits.map(
        (split) => split.cadence ?? stravaRunDetail.average_cadence ?? 0
      );
      // For heart rate, create a trend based on average/max
      const heartRateValues = Array.from({ length: Math.max(splits.length, 6) }).map(
        (_, idx) =>
          (stravaRunDetail.average_heartrate || 140) +
          ((stravaRunDetail.max_heartrate || 150) -
            (stravaRunDetail.average_heartrate || 140)) *
            (idx / Math.max(splits.length - 1, 5))
      );
      
      return [
        buildSeries(
          "Pace",
          paceValues,
          "sec/km",
          (val) => (val ? formatPace(val) : "--")
        ),
        buildSeries(
          "Heart rate",
          heartRateValues,
          "bpm"
        ),
        buildSeries(
          "Cadence",
          cadenceValues,
          "spm"
        ),
      ];
    }

    const template = normalizedRuns.slice(0, 8);
    const fallback = template.length
      ? template
      : Array.from({ length: 6 }).map((_, idx) => ({
          duration_seconds: 320 + idx * 18,
        }));
    const buildSeries = (label: string, factor: number, offset: number, suffix: string) => {
      const data = fallback.map((run, idx) => ({
        index: idx,
        value: Math.round(
          offset + (run.duration_seconds || 1) * factor + (idx % 3) * 3
        ),
      }));
      return {
        label,
        suffix,
        data,
        latest: data[data.length - 1]?.value ?? offset,
      };
    };
    return [
      buildSeries("Heart rate", 0.08, 136, "bpm"),
      buildSeries("Cadence", 0.05, 172, "spm"),
      buildSeries("Power", 0.15, 290, "W"),
    ];
  }, [normalizedRuns, stravaRunDetail]);

  const distanceCaloriesSeries = useMemo(() => {
    return stravaRuns.slice(0, 5).map((run, idx) => ({
      label: `Run ${idx + 1}`,
      distance: run.distance_km,
      calories: run.calories ?? 0,
    }));
  }, [stravaRuns]);

  const paceCadenceSeries = useMemo(() => {
    if (!stravaRunDetail?.pace_cadence_series) {
      return [];
    }
    return stravaRunDetail.pace_cadence_series
      .filter((entry) => entry.time_seconds != null)
      .map((entry) => ({
        ...entry,
        pace_seconds: entry.pace_seconds ?? null,
        cadence: entry.cadence ?? null,
        pace_display: entry.pace_seconds ? formatPace(entry.pace_seconds) : "--",
      }));
  }, [stravaRunDetail]);

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
  }, [userId, stravaSyncStamp]);

  useEffect(() => {
    async function loadStravaStatus() {
      try {
        const status = await fetchStravaStatus(userId);
        setStravaStatus(status);
        setStravaError(null);
      } catch (e: any) {
        console.error(e);
        setStravaError(e.message || "Unable to load Strava status");
      }
    }
    loadStravaStatus();
  }, [userId]);

  useEffect(() => {
    async function loadStravaRuns(syncRequest: boolean) {
      if (!stravaStatus?.linked) {
        setStravaRuns([]);
        setSelectedStravaRunId(null);
        setStravaRunDetail(null);
        setStravaRunsError(null);
        setStravaSyncStamp(Date.now());
        return;
      }
      try {
        const runs = await fetchStravaRuns(userId, 10, syncRequest);
        setStravaRuns(runs);
        setStravaRunsError(null);
        if (runs.length > 0) {
          setSelectedStravaRunId(runs[0].strava_activity_id);
        } else {
          setSelectedStravaRunId(null);
          setStravaRunDetail(null);
        }
      } catch (e: any) {
        console.error(e);
        setStravaRuns([]);
        setStravaRunsError(e.message || "Failed to load Strava runs");
      } finally {
        setStravaSyncStamp(Date.now());
      }
    }
    loadStravaRuns(Boolean(stravaStatus?.linked));
  }, [userId, stravaStatus?.linked]);

  useEffect(() => {
    if (!selectedStravaRunId || !stravaStatus?.linked) {
      setStravaRunDetail(null);
      setStravaDetailError(null);
      return;
    }
    let cancelled = false;
    async function fetchDetail() {
      try {
        const detail = await fetchStravaRunDetail(userId, selectedStravaRunId);
        if (!cancelled) {
          setStravaRunDetail(detail);
          setStravaDetailError(null);
        }
      } catch (e: any) {
        if (!cancelled) {
          console.error(e);
          setStravaRunDetail(null);
          setStravaDetailError(e.message || "Unable to load run detail");
        }
      }
    }
    fetchDetail();
    return () => {
      cancelled = true;
    };
  }, [userId, selectedStravaRunId, stravaStatus?.linked]);

  async function handleStravaConnect() {
    setStravaLoading(true);
    setStravaError(null);
    try {
      const link = await requestStravaLink(userId);
      window.location.href = link.authorize_url;
    } catch (e: any) {
      console.error(e);
      setStravaError(e.message || "Unable to start Strava auth");
      setStravaLoading(false);
    }
  }

  function handleSelectStravaRun(run: StravaRecentRun) {
    setSelectedStravaRunId(run.strava_activity_id);
  }

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
        <div className="sidebar-strava-block">
          <button
            className="runrecord-btn small"
            onClick={handleStravaConnect}
            disabled={stravaLoading}
          >
            {stravaStatus?.linked ? "Re-link Strava" : "Connect Strava"}
          </button>
          {stravaStatus?.linked && (
            <div className="sidebar-strava-status">
              Linked · athlete #{stravaStatus.athlete_id ?? "?"}
            </div>
          )}
          {stravaError && (
            <div className="sidebar-strava-status error-text">{stravaError}</div>
          )}
        </div>
        <div className="sidebar-bottom">Logged in as {username}</div>
      </aside>

      {/* Main content */}
      <main className={mainClassName}>
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
            <div className="terminal-ribbon">
              <div className="terminal-ribbon-title">
                Biomechanics Lab · Live Console
              </div>
              <div className="terminal-ribbon-meta">
                Runner{" "}
                {runnerCode ? `#${runnerCode}` : `ID ${userId.slice(0, 6)}`}
              </div>
            </div>
            <div className="terminal-ticker">
              <div className="ticker-track">
                {[...tickerItems, ...tickerItems].map((item, idx) => (
                  <span
                    key={`${item.id}-${idx}`}
                    className={`ticker-item ${
                      item.positive ? "ticker-pos" : "ticker-neg"
                    }`}
                  >
                    {item.label}
                  </span>
                ))}
              </div>
            </div>
            <div className="terminal-card terminal-card-large">
              <div className="terminal-card-title">
                Pace variability (target 5:00/km)
              </div>
              <div className="terminal-card-body">
                {paceSeries.length === 0 ? (
                  <div className="dash-empty">No pace data detected.</div>
                ) : (
                  <ResponsiveContainer width="100%" height={220}>
                    <ComposedChart data={paceSeries}>
                      <XAxis dataKey="label" stroke="#94a3b8" />
                      <YAxis
                        yAxisId="left"
                        stroke="#f87171"
                        tickFormatter={(v) => formatPace(Number(v))}
                        label={{ value: "Pace (min/km)", angle: -90, position: "insideLeft" }}
                      />
                      <YAxis
                        yAxisId="right"
                        orientation="right"
                        stroke="#34d399"
                        label={{ value: "Cadence (spm)", angle: 90, position: "insideRight" }}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#040910",
                          border: "1px solid #1f2937",
                          color: "#f8fafc",
                        }}
                        formatter={(value, name) => {
                          if (name === "pace") {
                            return formatPace(Number(value));
                          }
                          if (name === "cadence") {
                            return `${value} spm`;
                          }
                          return value;
                        }}
                      />
                      <Bar
                        yAxisId="left"
                        dataKey="pace"
                        fill="rgba(248, 113, 113, 0.6)"
                        barSize={18}
                      />
                      <Line
                        yAxisId="right"
                        type="monotone"
                        dataKey="cadence"
                        stroke="#34d399"
                        strokeWidth={2}
                        dot={{ r: 3 }}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
            <div className="terminal-card terminal-card-large">
              <div className="terminal-card-title">
                Distance & calories (recent Strava runs)
              </div>
              <div className="terminal-card-body">
                {distanceCaloriesSeries.length === 0 ? (
                  <div className="dash-empty">
                    Link Strava to populate distance and calorie telemetry.
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height={220}>
                    <ComposedChart data={distanceCaloriesSeries}>
                      <XAxis dataKey="label" stroke="#94a3b8" />
                      <YAxis
                        yAxisId="left"
                        stroke="#34d399"
                        label={{ value: "km", angle: -90, position: "insideLeft" }}
                      />
                      <YAxis
                        yAxisId="right"
                        orientation="right"
                        stroke="#facc15"
                        label={{ value: "kcal", angle: 90, position: "insideRight" }}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#040910",
                          border: "1px solid #1f2937",
                          color: "#f8fafc",
                        }}
                      />
                      <Bar
                        yAxisId="left"
                        dataKey="distance"
                        fill="rgba(52, 211, 153, 0.6)"
                        barSize={18}
                      />
                      <Line
                        yAxisId="right"
                        type="monotone"
                        dataKey="calories"
                        stroke="#facc15"
                        strokeWidth={2}
                        dot={{ r: 3 }}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
            {data && overview ? (
              <>
                <section className="grid grid-2">
                  <Card title="Training load (last month)">
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
                        Current load:{" "}
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

                <section className="grid grid-1">
                  <Card title="Recent Strava runs">
                    {!stravaStatus?.linked ? (
                      <div className="dash-empty">
                        Link Strava to see your imported runs.
                      </div>
                    ) : stravaRunsError ? (
                      <div className="error-text">{stravaRunsError}</div>
                    ) : stravaRuns.length === 0 ? (
                      <div className="dash-empty">No Strava runs yet.</div>
                    ) : (
                      <div className="recent-runs-list">
                        {stravaRuns.map((run) => {
                          const selected =
                            selectedStravaRunId === run.strava_activity_id;
                          return (
                            <button
                              key={run.id}
                              type="button"
                              className={`recent-run-row recent-run-strava ${
                                selected ? "strava-selected" : ""
                              }`}
                              onClick={() => handleSelectStravaRun(run)}
                            >
                              <div className="recent-run-time">
                                {run.started_at
                                  ? `${new Date(
                                      run.started_at
                                    ).toLocaleDateString()} ${new Date(
                                      run.started_at
                                    ).toLocaleTimeString([], {
                                      hour: "2-digit",
                                      minute: "2-digit",
                                    })}`
                                  : "Unknown date"}
                              </div>
                              <div className="recent-run-distance">
                                {run.distance_km.toFixed(2)} km
                              </div>
                              <div className="recent-run-duration">
                                {formatDuration(run.duration_seconds)}
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </Card>
                </section>
                <section className="grid grid-1">
                  <Card title="Biomech sparklines">
                    {!stravaRunDetail ? (
                      <div className="dash-empty">
                        Select a Strava run to view biomechanics data.
                      </div>
                    ) : (
                      <div className="sparkline-grid">
                        {sparklineSeries.map((series) => (
                          <div className="sparkline-row" key={series.label}>
                            <div className="sparkline-label">{series.label}</div>
                            <div className="sparkline-chart">
                              <ResponsiveContainer width="100%" height={42}>
                                <AreaChart data={series.data}>
                                  <Area
                                    type="monotone"
                                    dataKey="value"
                                    stroke="#22d3ee"
                                    fill="rgba(34,211,238,0.25)"
                                    strokeWidth={2}
                                  />
                                </AreaChart>
                              </ResponsiveContainer>
                            </div>
                            <div className="sparkline-value">
                              {series.format
                                ? series.format(series.latest ?? 0)
                                : series.latest !== null
                                ? `${series.latest} ${series.suffix}`
                                : "--"}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>
                </section>
                <section className="grid grid-1">
                  <Card title="Selected Strava run detail">
                    {stravaDetailError ? (
                      <div className="error-text">{stravaDetailError}</div>
                    ) : !stravaRunDetail ? (
                      <div className="dash-empty">
                        Select a Strava run to view full telemetry.
                      </div>
                    ) : (
                      <div className="strava-detail-wrapper">
                        <div className="strava-detail-grid">
                          <div className="strava-detail-metric">
                            <span>Distance</span>
                            <strong>
                              {stravaRunDetail.distance_km.toFixed(2)} km
                            </strong>
                          </div>
                          <div className="strava-detail-metric">
                            <span>Duration</span>
                            <strong>
                              {formatDuration(stravaRunDetail.duration_seconds)}
                            </strong>
                          </div>
                          <div className="strava-detail-metric">
                            <span>Pace</span>
                            <strong>
                              {stravaRunDetail.average_pace_seconds
                                ? formatPace(
                                    stravaRunDetail.average_pace_seconds
                                  )
                                : "--"}
                            </strong>
                          </div>
                          <div className="strava-detail-metric">
                            <span>Calories</span>
                            <strong>
                              {stravaRunDetail.calories
                                ? `${stravaRunDetail.calories.toFixed(0)} kcal`
                                : "--"}
                            </strong>
                          </div>
                          <div className="strava-detail-metric">
                            <span>Heart rate</span>
                            <strong>
                              {stravaRunDetail.average_heartrate
                                ? `${Math.round(
                                    stravaRunDetail.average_heartrate
                                  )} bpm`
                                : "--"}
                            </strong>
                          </div>
                          <div className="strava-detail-metric">
                            <span>Cadence</span>
                            <strong>
                              {stravaRunDetail.average_cadence
                                ? `${Math.round(
                                    stravaRunDetail.average_cadence
                                  )} spm`
                                : "--"}
                            </strong>
                          </div>
                          <div className="strava-detail-metric">
                            <span>Elevation gain</span>
                            <strong>
                              {stravaRunDetail.total_elevation_gain
                                ? `${Math.round(
                                    stravaRunDetail.total_elevation_gain
                                  )} m`
                                : "--"}
                            </strong>
                          </div>
                          <div className="strava-detail-metric">
                            <span>Power</span>
                            <strong>
                              {stravaRunDetail.average_watts
                                ? `${Math.round(
                                    stravaRunDetail.average_watts
                                  )} W`
                                : "--"}
                            </strong>
                          </div>
                        </div>
                        {stravaRunDetail.splits.length > 0 && (
                          <div className="strava-splits">
                            <div className="strava-split-row header">
                              <span>KM</span>
                              <span>Pace</span>
                              <span>Cadence</span>
                              <span>Time</span>
                            </div>
                            {stravaRunDetail.splits.slice(0, 6).map((split) => (
                              <div
                                className="strava-split-row"
                                key={`split-${split.index}`}
                              >
                                <span>{split.index}</span>
                                <span>
                                  {split.pace_seconds
                                    ? formatPace(split.pace_seconds)
                                    : "--"}
                                </span>
                                <span>
                                  {split.cadence
                                    ? `${Math.round(split.cadence)} spm`
                                    : "--"}
                                </span>
                                <span>
                                  {formatDuration(split.duration_seconds)}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
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
