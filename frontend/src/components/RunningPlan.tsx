// src/components/RunningPlan.tsx
import React, { useEffect, useState, useRef } from "react";
import {
  RunningPlanCalendarResponse,
  RunningPlanDayPlan,
  DayPlanCreateRequest,
  fetchRunningPlanCalendar,
  createDayPlanApi,
  deleteDayPlanApi,
  AiPlanGenerateRequest,
  AiPlanPreviewResponse,
  AiPlanPreviewDay,
  AiPlanPreviewActivity,
  AiPlanApplyRequest,
  previewAiPlan,
  applyAiPlan,
  CoachNote,
  fetchRunnerNotes,
  createCoachNoteApi,
} from "../api";
import { Card } from "./Card";

interface RunningPlanProps {
  // userId always refers to the runner's id
  userId: string;
  // If coachId exists, current view is coach view and can write notes
  coachId?: string;
}

interface LocalWeeklySlot {
  weekday: number; // 0-6
  enabled: boolean;
  start_time: string; // HH:MM
  end_time: string; // HH:MM
}

// Internal types for AI form
type GoalMode = "distance" | "weight";
type FitnessLevel = "beginner" | "regular" | "athlete";

export const RunningPlan: React.FC<RunningPlanProps> = ({ userId, coachId }) => {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1); // 1-12

  const [calendar, setCalendar] = useState<RunningPlanCalendarResponse | null>(
    null
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ---- Day plan: form used in create-day modal ----
  const [newPlan, setNewPlan] = useState<DayPlanCreateRequest>({
    date: today.toISOString().slice(0, 10),
    start_time: "07:00",
    duration_minutes: 30,
    distance_km: 5,
    activity: "",
    description: "",
  });

  // Last click info, used to detect "fake double-click" on same date
  const [lastClick, setLastClick] = useState<{
    time: number;
    date: string;
  } | null>(null);

  // Timer for delayed single-click behavior
  const clickTimerRef = useRef<number | null>(null);

  const [dayModalOpen, setDayModalOpen] = useState(false);

  // ---- View-day modal: show all plans for a date ----
  const [viewModalOpen, setViewModalOpen] = useState(false);
  const [viewModalDate, setViewModalDate] = useState<string>("");
  const [viewModalPlans, setViewModalPlans] = useState<RunningPlanDayPlan[]>([]);

  // ---- Week plan: bottom card (manual weekly template) ----
  const [weekPlanWeekday, setWeekPlanWeekday] = useState<number>(1); // 1 = Monday
  const [weekPlanStartDate, setWeekPlanStartDate] = useState(
    today.toISOString().slice(0, 10)
  );
  const [weekPlanEndDate, setWeekPlanEndDate] = useState(
    new Date(today.getFullYear(), today.getMonth(), today.getDate() + 28)
      .toISOString()
      .slice(0, 10)
  );
  const [weekPlanStartTime, setWeekPlanStartTime] = useState("07:00");
  const [weekPlanDuration, setWeekPlanDuration] = useState(30);
  const [weekPlanDistance, setWeekPlanDistance] = useState(5);
  const [weekPlanActivity, setWeekPlanActivity] = useState("Main run");
  const [weekPlanApplying, setWeekPlanApplying] = useState(false);

  // -------- AI config & result --------
  const [aiPreview, setAiPreview] = useState<AiPlanPreviewResponse | null>(
    null
  );
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  //const [aiLastPayload, setAiLastPayload] =
  //  useState<AiPlanGenerateRequest | null>(null);

  // Modal open state for AI config
  const [aiModalOpen, setAiModalOpen] = useState(false);

  // Basic profile: height / weight / age
  const [aiHeight, setAiHeight] = useState<number>(170);
  const [aiWeight, setAiWeight] = useState<number>(60);
  const [aiAge, setAiAge] = useState<number>(25);

  // Goal: race distance vs weight loss
  const [aiGoalMode, setAiGoalMode] = useState<GoalMode>("distance");
  const [aiRaceDistance, setAiRaceDistance] = useState<string>("5000"); // meters
  const [aiTargetWeight, setAiTargetWeight] = useState<number>(55);

  // NEW: Fitness level
  const [aiFitnessLevel, setAiFitnessLevel] =
    useState<FitnessLevel>("beginner");

  // Injury information
  const [aiHasInjury, setAiHasInjury] = useState(false);
  const [aiInjuryDetail, setAiInjuryDetail] = useState("");

  // Weekly availability slots for AI
  const [aiWeeklySlots, setAiWeeklySlots] = useState<LocalWeeklySlot[]>(() =>
    Array.from({ length: 7 }, (_, i) => ({
      weekday: i, // 0 = Sun
      enabled: false,
      start_time: "07:00",
      end_time: "08:00",
    }))
  );

  // -------- Coach notes --------
  const [notes, setNotes] = useState<CoachNote[]>([]);
  const [notesLoading, setNotesLoading] = useState(false);
  const [notesError, setNotesError] = useState<string | null>(null);
  const [noteInput, setNoteInput] = useState("");

  const isCoachView = !!coachId;

  // Cleanup click timer on unmount
  useEffect(() => {
    return () => {
      if (clickTimerRef.current !== null) {
        window.clearTimeout(clickTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    loadCalendar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, year, month]);

  useEffect(() => {
    loadNotes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  async function loadCalendar() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRunningPlanCalendar(userId, year, month);
      setCalendar(data);
    } catch (e: any) {
      console.error(e);
      setError(e.message || "Failed to load calendar");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreatePlan() {
    try {
      await createDayPlanApi(userId, newPlan);
      await loadCalendar();
      setDayModalOpen(false);
    } catch (e: any) {
      alert(e.message || "Failed to create plan");
    }
  }

  async function handleDeletePlan(plan: RunningPlanDayPlan) {
    if (!window.confirm("Delete this plan?")) return;
    try {
      await deleteDayPlanApi(userId, plan.id);
      await loadCalendar();
      setViewModalPlans((prev) => prev.filter((p) => p.id !== plan.id));
    } catch (e: any) {
      alert(e.message || "Failed to delete plan");
    }
  }

  function changeMonth(delta: number) {
    let m = month + delta;
    let y = year;
    if (m < 1) {
      m = 12;
      y -= 1;
    } else if (m > 12) {
      m = 1;
      y += 1;
    }
    setMonth(m);
    setYear(y);
  }

  // -------- Notes-related logic --------

  async function loadNotes() {
    setNotesLoading(true);
    setNotesError(null);
    try {
      const list = await fetchRunnerNotes(userId);
      // Put the newest at the top
      setNotes(
        list.slice().sort((a, b) => b.created_at.localeCompare(a.created_at))
      );
    } catch (e: any) {
      console.error(e);
      setNotesError(e.message || "Failed to load notes");
    } finally {
      setNotesLoading(false);
    }
  }

  async function handleAddNote() {
    if (!coachId) return;
    const content = noteInput.trim();
    if (!content) return;

    try {
      const newNote = await createCoachNoteApi(coachId, userId, content);
      setNoteInput("");
      setNotes((prev) => [newNote, ...prev]);
    } catch (e: any) {
      console.error(e);
      alert(e.message || "Failed to add note");
    }
  }

  function formatNoteTime(iso: string) {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString();
  }

  // -------- Calendar cell click: single-click view, double-click create --------

  function openCreatePlanForDate(dateStr: string) {
    setNewPlan((prev) => ({
      ...prev,
      date: dateStr,
    }));
    setDayModalOpen(true);
  }

  function handleCalendarCellClick(dateStr: string, plans: RunningPlanDayPlan[]) {
    const now = Date.now();

    // Second click on same date within 350ms → treat as double-click
    if (
      lastClick &&
      lastClick.date === dateStr &&
      now - lastClick.time < 350
    ) {
      if (clickTimerRef.current !== null) {
        window.clearTimeout(clickTimerRef.current);
        clickTimerRef.current = null;
      }
      setLastClick(null);
      openCreatePlanForDate(dateStr);
      return;
    }

    // First click or click after timeout
    setLastClick({ time: now, date: dateStr });

    if (clickTimerRef.current !== null) {
      window.clearTimeout(clickTimerRef.current);
      clickTimerRef.current = null;
    }

    clickTimerRef.current = window.setTimeout(() => {
      setViewModalDate(dateStr);
      setViewModalPlans(plans);
      setViewModalOpen(true);
      clickTimerRef.current = null;
    }, 350);
  }

  // -------- Week plan (manual batch apply) --------

  function parseDate(s: string): Date {
    const [y, m, d] = s.split("-").map((x) => Number(x));
    return new Date(y, m - 1, d);
  }

  function formatDate(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  }

  async function handleApplyWeekPlan() {
    try {
      if (!weekPlanStartDate || !weekPlanEndDate) {
        alert("Please select start and end date.");
        return;
      }
      const start = parseDate(weekPlanStartDate);
      const end = parseDate(weekPlanEndDate);
      if (start > end) {
        alert("Start date must be before end date.");
        return;
      }

      setWeekPlanApplying(true);

      const weekdayTarget = weekPlanWeekday; // 0=Sun … 6=Sat

      const tasks: Promise<any>[] = [];
      const cur = new Date(start.getTime());
      while (cur <= end) {
        const jsWeekday = cur.getDay(); // 0 = Sun ... 6 = Sat
        const mapped = jsWeekday;
        if (mapped === weekdayTarget) {
          const dateStr = formatDate(cur);
          const payload: DayPlanCreateRequest = {
            date: dateStr,
            start_time: weekPlanStartTime,
            duration_minutes: weekPlanDuration,
            distance_km: weekPlanDistance,
            activity: weekPlanActivity,
          };
          tasks.push(createDayPlanApi(userId, payload));
        }
        cur.setDate(cur.getDate() + 1);
      }

      if (tasks.length === 0) {
        alert("No matching days in the selected range.");
        setWeekPlanApplying(false);
        return;
      }

      for (const t of tasks) {
        // eslint-disable-next-line no-await-in-loop
        await t;
      }

      await loadCalendar();
      alert(`Created ${tasks.length} day plans for the selected weekday.`);
    } catch (e: any) {
      console.error(e);
      alert(e.message || "Failed to apply week plan");
    } finally {
      setWeekPlanApplying(false);
    }
  }

  // -------- AI modal & actions --------

  const weekdayLabels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  function handleChangeSlot(
    idx: number,
    field: "enabled" | "start_time" | "end_time",
    value: boolean | string
  ) {
    setAiWeeklySlots((prev) =>
      prev.map((slot, i) =>
        i === idx ? { ...slot, [field]: value } : slot
      )
    );
  }

  function defaultDescription(activity: string): string {
    const lower = activity.toLowerCase();
    if (lower.includes("warm")) {
      return "Easy jog or brisk walk with dynamic mobility drills to prepare your joints and muscles.";
    }
    if (lower.includes("cool") || lower.includes("stretch")) {
      return "Gradually slow down to an easy walk, then stretch calves, quads, hamstrings and hips.";
    }
    if (lower.includes("main") || lower.includes("run")) {
      return "Run at a comfortable, conversational pace. You should not feel all-out.";
    }
    return "Move at an easy, comfortable effort and focus on smooth breathing.";
  }

  async function handleGenerateAiPlan() {
    try {
      if (!aiHeight || !aiWeight || !aiAge) {
        alert("Please fill height, weight and age.");
        return;
      }

      const enabledSlots = aiWeeklySlots.filter((s) => s.enabled);
      if (enabledSlots.length === 0) {
        alert("Please enable at least one time slot in the week.");
        return;
      }

      let goal_type: string | undefined;
      let target_distance_m: number | undefined;
      let target_weight_kg: number | undefined;

      if (aiGoalMode === "distance") {
        const dist = Number(aiRaceDistance);
        if (!dist || Number.isNaN(dist)) {
          alert("Please choose a valid race distance.");
          return;
        }
        target_distance_m = dist;
        goal_type = `race_${dist}m`;
      } else {
        if (!aiTargetWeight || aiTargetWeight <= 0) {
          alert("Please input a valid target weight.");
          return;
        }
        goal_type = "weight_loss";
        target_weight_kg = aiTargetWeight;
      }

      if (aiHasInjury && aiInjuryDetail.trim()) {
        const sanitized = aiInjuryDetail.trim().replace(/\s+/g, "_");
        goal_type = (goal_type || "general") + `_injury_${sanitized}`;
      }

      const payload: AiPlanGenerateRequest = {
        height_cm: aiHeight,
        weight_kg: aiWeight,
        age: aiAge,
        goal_type,
        target_distance_m,
        target_weight_kg,

        // NEW: send fitness level to backend
        fitness_level: aiFitnessLevel,

        weekly_slots: enabledSlots.map((s) => ({
          weekday: s.weekday,
          start_time: s.start_time,
          end_time: s.end_time,
        })),
      };

      setAiLoading(true);
      setAiError(null);
      const res = await previewAiPlan(userId, payload);
      setAiPreview(res);
      //setAiLastPayload(payload);
      setAiModalOpen(false);
    } catch (e: any) {
      console.error(e);
      setAiError(e.message || "Failed to preview AI plan");
    } finally {
      setAiLoading(false);
    }
  }

  async function handleApplyAi() {
    if (!aiPreview) {
      alert("Please generate your AI plan first.");
      return;
    }

    try {
      setAiLoading(true);
      setAiError(null);

      const applyPayload: AiPlanApplyRequest = {
        weekly_template: aiPreview.weekly_template,
      };

      await applyAiPlan(userId, applyPayload);
      await loadCalendar();
      alert("AI weekly plan applied for the next 30 days.");
    } catch (e: any) {
      console.error(e);
      setAiError(e.message || "Failed to apply AI plan");
    } finally {
      setAiLoading(false);
    }
  }


  return (
    <div className="running-plan-page">
      <Card title="Running plan calendar">
        <div className="calendar-header">
          <button onClick={() => changeMonth(-1)}>{"<"}</button>
          <span>
            {year} - {month.toString().padStart(2, "0")}
          </span>
          <button onClick={() => changeMonth(1)}>{">"}</button>
        </div>

        {loading && <div>Loading calendar...</div>}
        {error && <div className="error-text">{error}</div>}

        {calendar && (
          <div className="calendar-grid">
            {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => (
              <div key={d} className="calendar-weekday">
                {d}
              </div>
            ))}
            {calendar.days.map((day) => (
              <div
                key={day.date}
                className={
                  "calendar-cell" + (day.is_today ? " calendar-cell-today" : "")
                }
                onClick={() => handleCalendarCellClick(day.date, day.plans)}
                style={{ cursor: "pointer" }}
                title="Single-click to view plans, double-click to create a new plan"
              >
                <div className="calendar-date">{day.date.slice(-2)}</div>
                {day.plans.length === 0 ? (
                  <div className="calendar-no-plan">No plan</div>
                ) : (
                  day.plans.map((p) => (
                    <div key={p.id} className="calendar-plan">
                      <div>
                        {p.start_time} · {p.duration_minutes}min ·{" "}
                        {p.distance_km}km
                      </div>
                      {p.activity && (
                        <div className="calendar-plan-activity">
                          {p.activity}
                        </div>
                      )}
                      <button
                        className="calendar-plan-delete"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeletePlan(p);
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  ))
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Create day plan modal */}
      {dayModalOpen && (
        <div className="modal-backdrop">
          <div className="modal">
            <h3>Create a day plan</h3>
            <div className="form-row">
              <label>
                Date
                <input
                  type="date"
                  value={newPlan.date}
                  onChange={(e) =>
                    setNewPlan((p) => ({ ...p, date: e.target.value }))
                  }
                />
              </label>
              <label>
                Start time
                <input
                  type="time"
                  value={newPlan.start_time}
                  onChange={(e) =>
                    setNewPlan((p) => ({ ...p, start_time: e.target.value }))
                  }
                />
              </label>
            </div>
            <div className="form-row">
              <label>
                Duration (min)
                <input
                  type="number"
                  value={newPlan.duration_minutes}
                  onChange={(e) =>
                    setNewPlan((p) => ({
                      ...p,
                      duration_minutes: Number(e.target.value),
                    }))
                  }
                />
              </label>
              <label>
                Distance (km)
                <input
                  type="number"
                  value={newPlan.distance_km}
                  onChange={(e) =>
                    setNewPlan((p) => ({
                      ...p,
                      distance_km: Number(e.target.value),
                    }))
                  }
                />
              </label>
            </div>
            <div className="form-row">
              <label>
                Activity
                <input
                  type="text"
                  value={newPlan.activity ?? ""}
                  onChange={(e) =>
                    setNewPlan((p) => ({ ...p, activity: e.target.value }))
                  }
                />
              </label>
            </div>
            <div className="form-row">
              <label>
                Description
                <textarea
                  value={newPlan.description ?? ""}
                  onChange={(e) =>
                    setNewPlan((p) => ({ ...p, description: e.target.value }))
                  }
                  rows={4}
                  style={{ width: "100%" }}
                />
              </label>
            </div>
            <div className="modal-actions">
              <button onClick={() => setDayModalOpen(false)}>Cancel</button>
              <button onClick={handleCreatePlan}>Create</button>
            </div>
          </div>
        </div>
      )}

      {/* View day details modal */}
      {viewModalOpen && (
        <div className="modal-backdrop">
          <div className="modal" style={{ maxWidth: 600 }}>
            <h3>Plan for {viewModalDate}</h3>

            {viewModalPlans.length === 0 ? (
              <div>No plan for this day.</div>
            ) : (
              <div className="day-plan-list">
                {viewModalPlans.map((p) => (
                  <div key={p.id} className="day-plan-item">
                    <div style={{ fontWeight: 600 }}>
                      {p.start_time} · {p.duration_minutes}min ·{" "}
                      {p.distance_km}km
                    </div>
                    {p.activity && (
                      <div style={{ marginTop: 4 }}>
                        <strong>Activity: </strong>
                        {p.activity}
                      </div>
                    )}
                    {p.description && (
                      <div
                        style={{
                          marginTop: 4,
                          fontSize: 13,
                          color: "#555",
                          whiteSpace: "pre-wrap",
                        }}
                      >
                        <strong>Description: </strong>
                        {p.description}
                      </div>
                    )}
                    <button
                      className="calendar-plan-delete"
                      onClick={() => handleDeletePlan(p)}
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="modal-actions">
              <button onClick={() => setViewModalOpen(false)}>Close</button>
              <button onClick={() => openCreatePlanForDate(viewModalDate)}>
                Add plan on this day
              </button>
            </div>
          </div>
        </div>
      )}

      {/* AI config modal */}
      {aiModalOpen && (
        <div className="modal-backdrop">
          <div className="modal" style={{ maxWidth: 700 }}>
            <h3>Generate my AI plan</h3>

            <div className="form-row">
              <label>
                Height (cm)
                <input
                  type="number"
                  value={aiHeight}
                  onChange={(e) => setAiHeight(Number(e.target.value))}
                />
              </label>
              <label>
                Weight (kg)
                <input
                  type="number"
                  value={aiWeight}
                  onChange={(e) => setAiWeight(Number(e.target.value))}
                />
              </label>
              <label>
                Age
                <input
                  type="number"
                  value={aiAge}
                  onChange={(e) => setAiAge(Number(e.target.value))}
                />
              </label>
            </div>

            <div className="form-row">
              <label>
                Fitness level
                <select
                  value={aiFitnessLevel}
                  onChange={(e) =>
                    setAiFitnessLevel(e.target.value as FitnessLevel)
                  }
                >
                  <option value="beginner">Beginner</option>
                  <option value="regular">regular</option>
                  <option value="athlete">Athlete</option>
                </select>
              </label>

              <label>
                Goal
                <select
                  value={aiGoalMode}
                  onChange={(e) => setAiGoalMode(e.target.value as GoalMode)}
                >
                  <option value="distance">Race performance</option>
                  <option value="weight">Weight loss</option>
                </select>
              </label>

              {aiGoalMode === "distance" && (
                <label>
                  Target event
                  <select
                    value={aiRaceDistance}
                    onChange={(e) => setAiRaceDistance(e.target.value)}
                  >
                    <option value="100">100m</option>
                    <option value="200">200m</option>
                    <option value="400">400m</option>
                    <option value="800">800m</option>
                    <option value="1500">1500m</option>
                    <option value="3000">3000m</option>
                    <option value="5000">5000m</option>
                    <option value="10000">10000m</option>
                    <option value="42195">Marathon</option>
                  </select>
                </label>
              )}

              {aiGoalMode === "weight" && (
                <label>
                  Target weight (kg)
                  <input
                    type="number"
                    value={aiTargetWeight}
                    onChange={(e) =>
                      setAiTargetWeight(Number(e.target.value))
                    }
                  />
                </label>
              )}
            </div>

            <div className="form-row">
              <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <input
                  type="checkbox"
                  checked={aiHasInjury}
                  onChange={(e) => setAiHasInjury(e.target.checked)}
                />
                Have injury
              </label>
              <label style={{ flex: 1 }}>
                Injury detail (e.g. left knee, Achilles)
                <input
                  type="text"
                  value={aiInjuryDetail}
                  onChange={(e) => setAiInjuryDetail(e.target.value)}
                  disabled={!aiHasInjury}
                />
              </label>
            </div>

            <div style={{ marginTop: 16 }}>
              <strong>Weekly availability</strong>
              <p style={{ fontSize: 12, color: "#666", marginBottom: 8 }}>
                For each weekday, enable if you can train on that day and set a
                time window.
              </p>
              <div className="ai-weekly-grid">
                {aiWeeklySlots.map((slot, idx) => (
                  <div key={slot.weekday} className="ai-weekly-row">
                    <label style={{ width: 70 }}>
                      <input
                        type="checkbox"
                        checked={slot.enabled}
                        onChange={(e) =>
                          handleChangeSlot(
                            idx,
                            "enabled",
                            e.target.checked
                          )
                        }
                      />{" "}
                      {weekdayLabels[slot.weekday]}
                    </label>
                    <label>
                      From
                      <input
                        type="time"
                        value={slot.start_time}
                        disabled={!slot.enabled}
                        onChange={(e) =>
                          handleChangeSlot(
                            idx,
                            "start_time",
                            e.target.value
                          )
                        }
                      />
                    </label>
                    <label>
                      To
                      <input
                        type="time"
                        value={slot.end_time}
                        disabled={!slot.enabled}
                        onChange={(e) =>
                          handleChangeSlot(idx, "end_time", e.target.value)
                        }
                      />
                    </label>
                  </div>
                ))}
              </div>
            </div>

            <div className="modal-actions">
              <button onClick={() => setAiModalOpen(false)}>Cancel</button>
              <button onClick={handleGenerateAiPlan} disabled={aiLoading}>
                {aiLoading ? "Generating..." : "Generate"}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="running-plan-bottom">
        {/* Manual week plan batch creator */}
        <Card title="Create a week plan">
          <p style={{ marginBottom: "0.5rem", fontSize: 13, color: "#555" }}>
            Select a date range and a weekday. The same plan will be created on
            every matching day in that range.
          </p>
          <div className="form-row">
            <label>
              From
              <input
                type="date"
                value={weekPlanStartDate}
                onChange={(e) => setWeekPlanStartDate(e.target.value)}
              />
            </label>
            <label>
              To
              <input
                type="date"
                value={weekPlanEndDate}
                onChange={(e) => setWeekPlanEndDate(e.target.value)}
              />
            </label>
          </div>
          <div className="form-row">
            <label>
              Weekday
              <select
                value={weekPlanWeekday}
                onChange={(e) => setWeekPlanWeekday(Number(e.target.value))}
              >
                <option value={1}>Mon</option>
                <option value={2}>Tue</option>
                <option value={3}>Wed</option>
                <option value={4}>Thu</option>
                <option value={5}>Fri</option>
                <option value={6}>Sat</option>
                <option value={0}>Sun</option>
              </select>
            </label>
            <label>
              Start time
              <input
                type="time"
                value={weekPlanStartTime}
                onChange={(e) => setWeekPlanStartTime(e.target.value)}
              />
            </label>
          </div>
          <div className="form-row">
            <label>
              Duration (min)
              <input
                type="number"
                value={weekPlanDuration}
                onChange={(e) => setWeekPlanDuration(Number(e.target.value))}
              />
            </label>
            <label>
              Distance (km)
              <input
                type="number"
                value={weekPlanDistance}
                onChange={(e) => setWeekPlanDistance(Number(e.target.value))}
              />
            </label>
          </div>
          <div className="form-row">
            <label>
              Activity
              <input
                type="text"
                value={weekPlanActivity}
                onChange={(e) => setWeekPlanActivity(e.target.value)}
              />
            </label>
          </div>
          <button onClick={handleApplyWeekPlan} disabled={weekPlanApplying}>
            {weekPlanApplying ? "Applying..." : "Apply to range"}
          </button>
        </Card>

        {/* Coach notes */}
        <Card title="Coach notes">
          {notesLoading && <div>Loading notes...</div>}
          {notesError && <div className="error-text">{notesError}</div>}

          {isCoachView ? (
            <div className="coach-notes-form">
              <textarea
                className="coach-notes-textarea"
                placeholder="Write a note for this runner..."
                value={noteInput}
                onChange={(e) => setNoteInput(e.target.value)}
              />
              <button
                className="coach-notes-button"
                onClick={handleAddNote}
                disabled={!noteInput.trim()}
              >
                Add note
              </button>
            </div>
          ) : (
            <p className="coach-notes-hint">
              These notes are written by your coach and cannot be edited.
            </p>
          )}

          <div className="coach-notes-list">
            {notes.length === 0 ? (
              <div className="coach-notes-empty">No notes yet.</div>
            ) : (
              notes.map((n) => (
                <div key={n.id} className="coach-notes-item">
                  <div className="coach-notes-meta">
                    <span className="coach-notes-author">
                      {n.coach_name || "Coach"}
                    </span>
                    <span className="coach-notes-time">
                      {formatNoteTime(n.created_at)}
                    </span>
                  </div>
                  <div className="coach-notes-content">{n.content}</div>
                </div>
              ))
            )}
          </div>
        </Card>

        {/* AI weekly plan */}
        <Card title="AI weekly plan">
          <p>
            Let ChatGPT generate a weekly training template based on your
            profile, goal, fitness level and available time. You can preview the
            plan and then apply it to the next 30 days in your calendar.
          </p>
          <div className="ai-plan-actions">
            <button disabled={aiLoading} onClick={() => setAiModalOpen(true)}>
              Generate my AI plan
            </button>
            <button
              disabled={aiLoading || !aiPreview}
              onClick={handleApplyAi}
            >
              Apply to next 30 days
            </button>
          </div>
          {aiLoading && <div>Working...</div>}
          {aiError && <div className="error-text">{aiError}</div>}
          {aiPreview && (
            <div className="ai-preview">
              {aiPreview.weekly_template.map(
                (day: AiPlanPreviewDay) => (
                  <div key={day.weekday} className="ai-preview-day">
                    <strong>
                      {weekdayLabels[day.weekday]} (weekday {day.weekday})
                    </strong>
                    {day.activities.length === 0 ? (
                      <div>No activities</div>
                    ) : (
                      <ul>
                        {day.activities.map(
                          (a: AiPlanPreviewActivity, idx: number) => (
                            <li key={idx}>
                              <div>
                                {a.start_time} · {a.duration_minutes}min ·{" "}
                                {a.distance_km}km · {a.activity}
                              </div>
                              <div className="ai-preview-desc">
                                {a.description ?? defaultDescription(a.activity)}
                              </div>
                            </li>
                          )
                        )}
                      </ul>
                    )}
                  </div>
                )
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};

export default RunningPlan;
