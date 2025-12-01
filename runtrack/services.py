from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone, timedelta, date
from typing import Optional, Dict, Any, List
from zoneinfo import ZoneInfo

from openai import OpenAI
import os

from .repository import Repo

repo = Repo()
CENTRAL_TZ = "America/Chicago"

# === OpenAI 初始化（推荐用环境变量） ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    # 提前报错，让你一眼就看到问题，而不是悄悄走 stub
    raise RuntimeError("OPENAI_API_KEY is not set. Please set it before starting the server.")

client = OpenAI(api_key=OPENAI_API_KEY)

# ---------- Helpers ----------


def _since_iso_from_days(days: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.isoformat()


def _local_range_to_utc_iso(
    start_date: date,
    end_date_exclusive: date,
    tz_name: str,
) -> tuple[str, str]:
    tz = ZoneInfo(tz_name)
    start_local = datetime(
        start_date.year,
        start_date.month,
        start_date.day,
        0,
        0,
        0,
        tzinfo=tz,
    )
    end_local = datetime(
        end_date_exclusive.year,
        end_date_exclusive.month,
        end_date_exclusive.day,
        0,
        0,
        0,
        tzinfo=tz,
    )
    start_utc = start_local.astimezone(timezone.utc).isoformat()
    end_utc = end_local.astimezone(timezone.utc).isoformat()
    return start_utc, end_utc


def _build_active_session_info(
    active: Dict[str, Any],
    is_paused: bool = False,
) -> Dict[str, Any]:
    """
    Build a unified active_session structure for the frontend:
    {
        "session_id": ...,
        "started_at": ...,
        "calories_per_hour": ...,
        "elapsed_seconds": int,
        "is_paused": bool
    }
    Currently we do not store pause state in DB; we approximate elapsed_seconds
    by subtracting started_at from now.
    """
    started_at = active.get("started_at")
    elapsed = 0
    if started_at:
        try:
            dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            elapsed = int(max(0, (now - dt).total_seconds()))
        except Exception:
            elapsed = 0

    return {
        "session_id": active["id"],
        "started_at": active["started_at"],
        "calories_per_hour": float(active["calories_per_hour"]),
        "elapsed_seconds": elapsed,
        "is_paused": is_paused,
    }


# ---------- USER & BASIC RUN FEATURES ----------


def register_user(username: str, role: str) -> Dict[str, Any]:
    username = username.strip()
    if not username:
        raise ValueError("username must not be empty")
    return repo.create_user(username, role)


def login_user(username: str) -> Dict[str, Any]:
    username = username.strip()
    if not username:
        raise ValueError("username must not be empty")

    user = repo.get_user_by_username(username)
    if not user:
        raise ValueError("user not found")

    return user


def resolve_or_create_user(username: str, role: str = "runner") -> Dict[str, Any]:
    return repo.resolve_or_create_user(username, role)


def start_run(user_id: str, note: Optional[str] = None) -> Dict[str, Any]:
    user = repo.get_user_by_id(user_id)
    if not user:
        raise ValueError("user not found")
    settings = repo.get_or_create_user_settings(user_id)
    return repo.create_active_session(
        user_id,
        note,
        calories_per_hour=settings["calories_per_hour"],
    )


def add_metric(
    user_id: str,
    distance_km: float,
    duration_seconds: int,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> Dict[str, Any]:
    active = repo.get_active_session(user_id)
    if not active:
        raise ValueError("No active session for this user")
    return repo.add_metric(
        active["id"],
        distance_km,
        duration_seconds,
        start_time,
        end_time,
    )


def stop_run(
    user_id: str,
    total_distance_km: Optional[float] = None,
    elapsed_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    active = repo.get_active_session(user_id)
    if not active:
        raise ValueError("No active session for this user")
    return repo.finish_session(
        active["id"],
        total_distance_km=total_distance_km,
        elapsed_seconds=elapsed_seconds,
    )


# ---------- pause / resume (frontend-driven timing) ----------


def pause_run(user_id: str) -> Dict[str, Any]:
    """
    Pause: does not modify DB.
    It only checks that user and active session exist,
    then returns active_session info with is_paused=True.
    """
    user = repo.get_user_by_id(user_id)
    if not user:
        raise ValueError("user not found")

    active = repo.get_active_session(user_id)
    if not active:
        raise ValueError("No active session for this user")

    return _build_active_session_info(active, is_paused=True)


def resume_run(user_id: str) -> Dict[str, Any]:
    """
    Resume: same as pause_run, just returns is_paused=False after checks.
    """
    user = repo.get_user_by_id(user_id)
    if not user:
        raise ValueError("user not found")

    active = repo.get_active_session(user_id)
    if not active:
        raise ValueError("No active session for this user")

    return _build_active_session_info(active, is_paused=False)


def view_history(user_id: str, limit: int = 20) -> Dict[str, Any]:
    return repo.fetch_history_by_user_id(user_id, limit)


def build_prompt_payload(user_id: str, last_n: int = 5) -> Dict[str, Any]:
    return repo.fetch_recent_for_prompt_by_user_id(user_id, last_n)


# ---------- USER SETTINGS ----------


def get_user_settings(user_id: str) -> Dict[str, Any]:
    return repo.get_or_create_user_settings(user_id)


def set_calories_per_hour(user_id: str, value: float) -> Dict[str, Any]:
    if value <= 0:
        raise ValueError("calories_per_hour must be positive")
    return repo.update_user_calories_per_hour(user_id, value)


# ---------- HISTORY JSON FOR AI ----------


def build_history_json(user_id: str, limit: int = 50) -> Dict[str, Any]:
    raw = repo.fetch_history_by_user_id(user_id, limit)
    if not raw["user_id"]:
        return {
            "user": None,
            "overall_stats": {
                "total_distance_km": 0.0,
                "total_sessions": 0,
                "avg_distance_per_session": 0.0,
            },
            "sessions": [],
        }

    total_dist = 0.0
    for s in raw["sessions"]:
        total_dist += float(s["total_distance_km"] or 0.0)
    count = raw["count"]
    avg_dist = total_dist / count if count > 0 else 0.0

    sessions = []
    for s in raw["sessions"]:
        sessions.append(
            {
                "session_id": s["id"],
                "started_at": s["started_at"],
                "ended_at": s["ended_at"],
                "total_distance_km": float(s["total_distance_km"] or 0.0),
                "total_duration_seconds": int(s["total_duration_seconds"] or 0),
                "total_calories": float(s["total_calories"] or 0.0),
                "calories_per_hour": float(s["calories_per_hour"] or 600.0),
                "metrics": [
                    {
                        "metric_id": m["id"],
                        "distance_km": float(m["distance"]),
                        "duration_seconds": int(m["duration_seconds"]),
                        "start_time": m["start_time"],
                        "end_time": m["end_time"],
                    }
                    for m in s["metrics"]
                ],
            }
        )

    return {
        "user": {
            "id": raw["user_id"],
            "name": raw["username"],
            "role": "runner",
        },
        "overall_stats": {
            "total_distance_km": round(total_dist, 3),
            "total_sessions": count,
            "avg_distance_per_session": round(avg_dist, 3),
        },
        "sessions": sessions,
    }


# ---------- TRAINING PLANS (generic) ----------


def create_plan(
    user_id: str,
    name: str,
    goal_type: str,
    target_event_date: Optional[str],
    meta_json: Optional[Dict[str, Any]],
    entries: List[Dict[str, Any]],
    created_by_ai: bool = False,
) -> Dict[str, Any]:
    return repo.create_plan(
        user_id=user_id,
        name=name,
        goal_type=goal_type,
        target_event_date=target_event_date,
        created_by_ai=created_by_ai,
        meta_json=meta_json,
        entries=entries,
    )


def list_plans(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    return repo.list_plans_by_user_id(user_id, limit)


def get_plan_detail(plan_id: str) -> Dict[str, Any]:
    plan = repo.get_plan_with_entries(plan_id)
    if not plan:
        raise ValueError("plan not found")
    return plan


def link_plan_entry_to_session(plan_entry_id: str, session_id: str) -> Dict[str, Any]:
    return repo.link_plan_entry_to_session(plan_entry_id, session_id)


# ---------- COACH <-> RUNNER BINDING ----------


def bind_runner_to_coach(coach_id: str, runner_code: int) -> Dict[str, Any]:
    coach = repo.get_user_by_id(coach_id)
    if not coach:
        raise ValueError("coach not found")
    if coach.get("role") != "coach":
        raise ValueError("only coach can bind runners")

    runner = repo.get_user_by_runner_code(runner_code)
    if not runner:
        raise ValueError("runner with this code not found")

    repo.bind_coach_to_runner(coach_id, runner["id"])

    return {
        "coach_id": coach_id,
        "runner": {
            "id": runner["id"],
            "name": runner["username"],
            "runner_code": runner["runner_code"],
        },
    }


def list_coach_runners(coach_id: str) -> List[Dict[str, Any]]:
    coach = repo.get_user_by_id(coach_id)
    if not coach:
        raise ValueError("coach not found")
    if coach.get("role") != "coach":
        raise ValueError("only coach can have bound runners")

    rows = repo.list_runners_for_coach(coach_id)
    return [
        {
            "id": r["id"],
            "name": r["username"],
            "runner_code": r["runner_code"],
        }
        for r in rows
    ]


# ---------- COACH NOTES ----------


def create_coach_note_for_runner(
    coach_id: str,
    runner_id: str,
    content: str,
) -> Dict[str, Any]:
    coach = repo.get_user_by_id(coach_id)
    if not coach:
        raise ValueError("coach not found")
    if coach.get("role") != "coach":
        raise ValueError("only coach can create notes")

    runner = repo.get_user_by_id(runner_id)
    if not runner:
        raise ValueError("runner not found")
    if runner.get("role") != "runner":
        raise ValueError("target user is not a runner")

    content = content.strip
    if not content:
        raise ValueError("content must not be empty")

    note = repo.create_coach_note(
        coach_id=coach_id,
        runner_id=runner_id,
        coach_name=coach.get("username"),
        content=content,
    )
    return note


def list_notes_for_runner(runner_id: str) -> List[Dict[str, Any]]:
    runner = repo.get_user_by_id(runner_id)
    if not runner:
        raise ValueError("runner not found")
    if runner.get("role") != "runner":
        raise ValueError("target user is not a runner")

    return repo.list_coach_notes_for_runner(runner_id)


# ---------- STATS: OVERVIEW, DAILY, TIME-OF-DAY, TRAINING LOAD ----------


def get_stats_overview(user_id: str, days: int) -> Dict[str, Any]:
    since_iso = _since_iso_from_days(days)
    overview = repo.stats_overview(user_id, since_iso)
    calories = overview["total_distance_km"] * 60.0
    overview["estimated_calories"] = round(calories, 1)
    overview["range_days"] = days
    return overview


def get_stats_daily(user_id: str, days: int) -> Dict[str, Any]:
    since_iso = _since_iso_from_days(days)
    daily = repo.stats_daily(user_id, since_iso)
    return {
        "range_days": days,
        "daily": daily,
    }


def _bucket_for_hour(hour: int) -> str:
    if 5 <= hour < 10:
        return "morning"
    if 10 <= hour < 14:
        return "forenoon"
    if 14 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 22:
        return "evening"
    return "night"


def get_stats_time_of_day(user_id: str, days: int) -> Dict[str, Any]:
    since_iso = _since_iso_from_days(days)
    sessions = repo.stats_sessions_since(user_id, since_iso)

    buckets = {
        "morning": {"sessions": 0, "distance_km": 0.0, "duration_seconds": 0},
        "forenoon": {"sessions": 0, "distance_km": 0.0, "duration_seconds": 0},
        "afternoon": {"sessions": 0, "distance_km": 0.0, "duration_seconds": 0},
        "evening": {"sessions": 0, "distance_km": 0.0, "duration_seconds": 0},
        "night": {"sessions": 0, "distance_km": 0.0, "duration_seconds": 0},
    }

    total_sessions = 0
    for s in sessions:
        dt = datetime.fromisoformat(s["started_at"].replace("Z", "+00:00"))
        hour = dt.hour
        key = _bucket_for_hour(hour)
        b = buckets[key]
        b["sessions"] += 1
        b["distance_km"] += s["total_distance_km"]
        b["duration_seconds"] += s["total_duration_seconds"]
        total_sessions += 1

    result_list: List[Dict[str, Any]] = []
    for key, val in buckets.items():
        percentage = (val["sessions"] / total_sessions) if total_sessions > 0 else 0.0
        result_list.append(
            {
                "slot": key,
                "sessions": val["sessions"],
                "distance_km": round(val["distance_km"], 3),
                "duration_seconds": val["duration_seconds"],
                "percentage": round(percentage, 4),
            }
        )

    return {
        "range_days": days,
        "time_of_day_distribution": result_list,
        "total_sessions": total_sessions,
    }


def get_stats_training_load(user_id: str, weeks: int) -> Dict[str, Any]:
    days = weeks * 7
    since_iso = _since_iso_from_days(days)
    sessions = repo.stats_sessions_since(user_id, since_iso)

    weekly: Dict[str, float] = {}
    week_start_dates: Dict[str, str] = {}

    for s in sessions:
        dt = datetime.fromisoformat(s["started_at"].replace("Z", "+00:00"))
        iso_year, iso_week, iso_weekday = dt.isocalendar()
        week_key = f"{iso_year}-W{iso_week:02d}"
        monday = dt - timedelta(days=iso_weekday - 1)
        week_start_dates[week_key] = monday.date().isoformat()
        load = s["total_distance_km"] * 100.0
        weekly[week_key] = weekly.get(week_key, 0.0) + load

    weeks_list: List[Dict[str, Any]] = []
    for key, load in sorted(weekly.items(), key=lambda x: x[0]):
        weeks_list.append(
            {
                "week_label": key,
                "week_start": week_start_dates[key],
                "training_load": round(load, 1),
            }
        )

    current_week_load = weeks_list[-1]["training_load"] if weeks_list else 0.0
    avg_load = (
        sum(w["training_load"] for w in weeks_list) / len(weeks_list)
        if weeks_list
        else 0.0
    )

    return {
        "range_weeks": weeks,
        "weeks": weeks_list,
        "current_week_load": round(current_week_load, 1),
        "average_week_load": round(avg_load, 1),
    }


def get_dashboard(user_id: str, days: int, weeks: int) -> Dict[str, Any]:
    overview = get_stats_overview(user_id, days)
    daily = get_stats_daily(user_id, days)
    time_of_day = get_stats_time_of_day(user_id, days)
    training_load = get_stats_training_load(user_id, weeks)

    return {
        "overview": overview,
        "daily": daily,
        "time_of_day": time_of_day,
        "training_load": training_load,
    }


# ---------- RUN RECORD APIS ----------


def get_today_run_record(user_id: str, tz_name: str = CENTRAL_TZ) -> Dict[str, Any]:
    user = repo.get_user_by_id(user_id)
    if not user:
        raise ValueError("user not found")

    settings = repo.get_or_create_user_settings(user_id)

    now_local = datetime.now(ZoneInfo(tz_name))
    today = now_local.date()
    start_utc, end_utc = _local_range_to_utc_iso(
        today,
        today + timedelta(days=1),
        tz_name,
    )

    # Compute today's goal seconds based on today's running plan.
    today_plans = repo.list_daily_plans_for_date(user_id, today.isoformat())
    goal_minutes = sum(p.get("duration_minutes", 0) for p in today_plans)
    if goal_minutes > 0:
        today_goal_seconds = goal_minutes * 60
    else:
        today_goal_seconds = 60 * 60

    sessions = repo.fetch_sessions_between(user_id, start_utc, end_utc)

    total_duration = sum(s["total_duration_seconds"] for s in sessions)
    total_calories = sum(s["total_calories"] for s in sessions)
    total_distance = sum(s["total_distance_km"] for s in sessions)

    active = repo.get_active_session(user_id)
    active_info = None
    if active:
        active_info = _build_active_session_info(active, is_paused=False)

    return {
        "timezone": tz_name,
        "date": today.isoformat(),
        "settings": settings,
        "active_session": active_info,
        "today_summary": {
            "total_duration_seconds": total_duration,
            "total_calories": total_calories,
            "total_distance_km": total_distance,
            "sessions": sessions,
        },
        "today_goal_seconds": today_goal_seconds,
    }


def get_run_record_list(
    user_id: str,
    start_date_str: str,
    end_date_str: str,
    tz_name: str = CENTRAL_TZ,
) -> Dict[str, Any]:
    user = repo.get_user_by_id(user_id)
    if not user:
        raise ValueError("user not found")

    start_date = date.fromisoformat(start_date_str)
    end_date = date.fromisoformat(end_date_str)
    end_exclusive = end_date + timedelta(days=1)

    start_utc, end_utc = _local_range_to_utc_iso(start_date, end_exclusive, tz_name)
    sessions = repo.fetch_sessions_between(user_id, start_utc, end_utc)

    total_duration = sum(s["total_duration_seconds"] for s in sessions)
    total_distance = sum(s["total_distance_km"] for s in sessions)
    total_calories = sum(s["total_calories"] for s in sessions)

    return {
        "timezone": tz_name,
        "start_date": start_date_str,
        "end_date": end_date_str,
        "summary": {
            "total_sessions": len(sessions),
            "total_distance_km": total_distance,
            "total_duration_seconds": total_duration,
            "total_calories": total_calories,
        },
        "sessions": sessions,
    }


def get_run_record_calendar(
    user_id: str,
    year: int,
    month: int,
    tz_name: str = CENTRAL_TZ,
) -> Dict[str, Any]:
    user = repo.get_user_by_id(user_id)
    if not user:
        raise ValueError("user not found")

    first_day = date(year, month, 1)
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)

    start_utc, end_utc = _local_range_to_utc_iso(first_day, next_month, tz_name)
    daily = repo.fetch_daily_aggregates_between(user_id, start_utc, end_utc)

    return {
        "timezone": tz_name,
        "year": year,
        "month": month,
        "days": daily,
    }


# ---------- WEEK PLAN RULE (legacy interface) ----------


def get_week_plan_rule(user_id: str) -> Dict[str, Any]:
    user = repo.get_user_by_id(user_id)
    if not user:
        raise ValueError("user not found")
    return repo.get_weekly_plan_rule_or_default(user_id)


def set_week_plan_rule(
    user_id: str,
    weekday: int,
    start_time: str,
    duration_minutes: int,
    distance_km: float,
) -> Dict[str, Any]:
    user = repo.get_user_by_id(user_id)
    if not user:
        raise ValueError("user not found")

    if weekday < 0 or weekday > 6:
        raise ValueError("weekday must be in [0, 6]")
    if duration_minutes <= 0:
        raise ValueError("duration_minutes must be positive")
    if distance_km < 0:
        raise ValueError("distance_km must be >= 0")

    return repo.upsert_weekly_plan_rule(
        user_id,
        weekday,
        start_time,
        duration_minutes,
        distance_km,
    )


# ---------- DAILY RUNNING PLAN + CALENDAR ----------


def create_day_plan(
    user_id: str,
    date_str: str,
    start_time: str,
    duration_minutes: int,
    distance_km: float,
    activity: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    user = repo.get_user_by_id(user_id)
    if not user:
        raise ValueError("user not found")

    try:
        d = date.fromisoformat(date_str)
    except Exception:
        raise ValueError("date must be YYYY-MM-DD")

    try:
        hh, mm = map(int, start_time.split(":"))
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            raise ValueError
    except Exception:
        raise ValueError("start_time must be HH:MM")

    if duration_minutes <= 0:
        raise ValueError("duration_minutes must be positive")
    if distance_km < 0:
        raise ValueError("distance_km must be >= 0")

    _ = d
    return repo.create_daily_plan(
        user_id,
        date_str,
        start_time,
        duration_minutes,
        distance_km,
        activity or None,
        description or None,
    )


def delete_day_plan(user_id: str, plan_id: str) -> None:
    user = repo.get_user_by_id(user_id)
    if not user:
        raise ValueError("user not found")
    repo.delete_daily_plan(user_id, plan_id)


def list_day_plans_for_date(user_id: str, date_str: str) -> List[Dict[str, Any]]:
    user = repo.get_user_by_id(user_id)
    if not user:
        raise ValueError("user not found")
    try:
        _ = date.fromisoformat(date_str)
    except Exception:
        raise ValueError("date must be YYYY-MM-DD")
    return repo.list_daily_plans_for_date(user_id, date_str)


def create_weekly_batch_plans(
    user_id: str,
    year: int,
    month: int,
    weekday: int,
    start_time: str,
    duration_minutes: int,
    distance_km: float,
    activity: Optional[str] = None,
) -> Dict[str, Any]:
    user = repo.get_user_by_id(user_id)
    if not user:
        raise ValueError("user not found")

    if weekday < 0 or weekday > 6:
        raise ValueError("weekday must be in [0, 6]")

    tmp = create_day_plan(
        user_id=user_id,
        date_str=f"{year:04d}-{month:02d}-01",
        start_time=start_time,
        duration_minutes=duration_minutes,
        distance_km=distance_km,
        activity=activity,
    )
    repo.delete_daily_plan(user_id, tmp["id"])

    first_day = date(year, month, 1)
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)

    d = first_day
    created: List[Dict[str, Any]] = []
    while d < next_month:
        if d.weekday() == weekday:
            created.append(
                repo.create_daily_plan(
                    user_id,
                    d.isoformat(),
                    start_time,
                    duration_minutes,
                    distance_km,
                    activity or None,
                    None,
                )
            )
        d += timedelta(days=1)

    return {"created": created, "count": len(created)}


def get_running_plan_calendar(
    user_id: str,
    year: int,
    month: int,
    tz_name: str = CENTRAL_TZ,
) -> Dict[str, Any]:
    user = repo.get_user_by_id(user_id)
    if not user:
        raise ValueError("user not found")

    tz = ZoneInfo(tz_name)
    today_local = datetime.now(tz).date()

    first_day = date(year, month, 1)
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)

    plans_rows = repo.list_daily_plans_for_month(
        user_id,
        first_day.isoformat(),
        next_month.isoformat(),
    )
    plans_by_date: Dict[str, List[Dict[str, Any]]] = {}
    for p in plans_rows:
        plans_by_date.setdefault(p["plan_date"], []).append(
            {
                "id": p["id"],
                "start_time": p["start_time_local"],
                "duration_minutes": p["duration_minutes"],
                "distance_km": p["distance_km"],
                "activity": p["activity"],
                "description": p.get("description"),
            }
        )

    days: List[Dict[str, Any]] = []
    d = first_day
    while d < next_month:
        date_str = d.isoformat()
        day_plans = plans_by_date.get(date_str, [])
        days.append(
            {
                "date": date_str,
                "weekday": d.weekday(),
                "is_today": d == today_local,
                "plans": day_plans,
            }
        )
        d += timedelta(days=1)

    return {
        "timezone": tz_name,
        "year": year,
        "month": month,
        "days": days,
    }


# ---------- AI: history-based and goal-based plans (still heuristic) ----------


def ai_analyze_history_and_plan(
    user_id: str,
    limit: int,
    weeks_to_plan: int,
    extra_notes: Optional[str] = None,
) -> Dict[str, Any]:
    history = build_history_json(user_id, limit)
    if history["user"] is None:
        raise ValueError("user not found or no history")

    total_days = weeks_to_plan * 7
    entries: List[Dict[str, Any]] = []

    for i in range(total_days):
        dow = i % 7
        if dow in (0, 3):
            focus = "rest"
            target_distance = None
            target_duration = None
            workout_text = "Rest day with light stretching or walking."
        elif dow == 5:
            focus = "long_run"
            target_distance = 8.0
            target_duration = 60 * 60
            workout_text = "Long easy run, keep the pace comfortable."
        elif dow == 2:
            focus = "interval"
            target_distance = 5.0
            target_duration = 45 * 60
            workout_text = "Interval training such as 5×800m slightly faster than usual pace."
        else:
            focus = "easy_run"
            target_distance = 5.0
            target_duration = 40 * 60
            workout_text = "Easy run at conversational pace."

        entries.append(
            {
                "day_index": i,
                "date": None,
                "focus": focus,
                "target_distance_km": target_distance,
                "target_duration_seconds": target_duration,
                "intensity": "easy" if focus in ("easy_run", "long_run") else "moderate",
                "warmup_text": "5–10 minutes of easy jogging and dynamic stretching.",
                "workout_text": workout_text,
                "cooldown_text": "5 minutes of easy jogging, then lower-body stretching.",
                "nutrition_text": "Stay hydrated and include carbs and protein around training.",
                "notes": extra_notes,
            }
        )

    plan_name = f"Auto plan from history ({weeks_to_plan} weeks)"
    meta = {
        "source": "analyze_history",
        "extra_notes": extra_notes,
        "overall_stats_snapshot": history["overall_stats"],
    }

    plan = create_plan(
        user_id=user_id,
        name=plan_name,
        goal_type="general_fitness",
        target_event_date=None,
        meta_json=meta,
        entries=entries,
        created_by_ai=True,
    )

    return {
        "history": history,
        "generated_plan": plan,
    }


def ai_goal_plan(
    user_id: str,
    goal_type: str,
    target_event_date: Optional[str],
    weeks_to_plan: Optional[int],
    current_weekly_distance_km: Optional[float],
    running_experience_level: Optional[str],
    extra_notes: Optional[str],
) -> Dict[str, Any]:
    weeks = weeks_to_plan or 8
    total_days = weeks * 7
    entries: List[Dict[str, Any]] = []

    if goal_type == "weight_loss":
        base_distance = 4.0
        plan_name = f"Weight loss plan ({weeks} weeks)"
        default_intensity = "easy"
    elif goal_type in ("5k_race", "10k_race"):
        base_distance = 5.0 if goal_type == "5k_race" else 8.0
        plan_name = f"{goal_type.upper()} training plan ({weeks} weeks)"
        default_intensity = "moderate"
    else:
        base_distance = 5.0
        plan_name = f"General training plan ({weeks} weeks)"
        default_intensity = "easy"

    for i in range(total_days):
        dow = i % 7
        if goal_type == "weight_loss":
            if dow in (0, 3):
                focus = "rest"
                dist = None
                dur = None
                workout_text = "Rest or 20–30 minutes of walking."
            else:
                focus = "easy_run"
                dist = base_distance
                dur = int(45 * 60)
                workout_text = "Low to moderate intensity continuous running."
            nutrition = "Moderate calorie deficit, high protein, plenty of vegetables."
        elif goal_type in ("5k_race", "10k_race"):
            if dow == 0:
                focus = "rest"
                dist = None
                dur = None
                workout_text = "Rest day with light stretching."
            elif dow == 2:
                focus = "interval"
                dist = base_distance
                dur = int(40 * 60)
                workout_text = "Intervals: short fast repeats with easy jog recovery."
            elif dow == 4:
                focus = "tempo_run"
                dist = base_distance - 1
                dur = int(35 * 60)
                workout_text = "Tempo run slightly faster than normal pace."
            elif dow == 5:
                focus = "long_run"
                dist = base_distance + 3
                dur = int(60 * 60)
                workout_text = "Long easy run to build endurance."
            else:
                focus = "easy_run"
                dist = base_distance - 2
                dur = int(30 * 60)
                workout_text = "Easy run for recovery."
            nutrition = "Carb-focused meals around key sessions, avoid heavy/fatty foods pre-run."
        else:
            if dow in (0, 3):
                focus = "rest"
                dist = None
                dur = None
                workout_text = "Rest or light activity."
            elif dow == 5:
                focus = "long_run"
                dist = base_distance + 3
                dur = int(60 * 60)
                workout_text = "Long easy run."
            else:
                focus = "easy_run"
                dist = base_distance
                dur = int(40 * 60)
                workout_text = "Easy run."
            nutrition = "Balanced diet, regular meals, more water and less sugar."

        entries.append(
            {
                "day_index": i,
                "date": None,
                "focus": focus,
                "target_distance_km": dist,
                "target_duration_seconds": dur,
                "intensity": default_intensity,
                "warmup_text": "5–10 minutes easy jog + dynamic stretching.",
                "workout_text": workout_text,
                "cooldown_text": "5–10 minutes easy walk + static stretching.",
                "nutrition_text": nutrition,
                "notes": extra_notes,
            }
        )

    meta = {
        "source": "goal_based_plan",
        "goal_type": goal_type,
        "target_event_date": target_event_date,
        "current_weekly_distance_km": current_weekly_distance_km,
        "running_experience_level": running_experience_level,
        "extra_notes": extra_notes,
    }

    plan = create_plan(
        user_id=user_id,
        name=plan_name,
        goal_type=goal_type,
        target_event_date=target_event_date,
        meta_json=meta,
        entries=entries,
        created_by_ai=True,
    )

    return {
        "generated_plan": plan,
    }


# ---------- ChatGPT-based weekly plan helpers ----------


def _extract_json_from_text(raw: str) -> Dict[str, Any]:
    """
    Extract the first JSON object from a model response.
    Supports plain `{...}` or fenced ```json blocks.
    """
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw).strip()

    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        raise ValueError("No JSON object found in model output")
    json_str = m.group(0)
    return json.loads(json_str)


def _build_weekly_plan_via_chatgpt(
    user_params: Dict[str, Any],
    weekly_slots: List[Dict[str, Any]],
) -> Dict[str, Any]:

    system_prompt = (
      "You are an experienced running coach and schedule designer. "
      "Given a runner's profile (including fitness_level) and weekly available time slots, "
      "you design a realistic, safe 7-day running plan.\n"
      "- Each day can have zero or more activities.\n"
      "- An 'activity' is one continuous segment, such as warm-up, interval run, easy jog, or stretching.\n"
      "- For one available time window you may create multiple activities "
      "(e.g. warm-up, fast intervals, easy 400 m jog, stretching).\n"
      "- Rest breaks should be represented as gaps between activities in time; "
      "do NOT create explicit 'Rest' activities.\n"
      "- For any activity, its start_time and (start_time + duration_minutes) must fall "
      "inside one of that day's available weekly_slots windows, and activities on the same day "
      "must be in chronological order and must not overlap.\n"
      "Output must be strict JSON with no extra commentary."
   )


    user_payload = {
        "runner_profile": user_params,
        "weekly_slots": weekly_slots,
        "output_format": {
            "user_params": {
            "height_cm": "number",
            "weight_kg": "number",
            "age": "number",
            "goal_type": "string | null",
            "target_distance_m": "number | null",
            "target_weight_kg": "number | null",
            "fitness_level": "string | null, one of: beginner, regular, athlete",
        },
        "weekly_template": [
            {
                "weekday": "int 0-6 (0=Sun, 1=Mon, ... 6=Sat)",
               "activities": [
                   {
                        "start_time": "HH:MM 24-hour",
                        "duration_minutes": "int > 0",
                        "distance_km": "float >= 0",
                        "activity": (
                            "short session title, e.g. "
                            "'Warm-up jog', '400 m intervals', "
                            "'Easy 400 m jog', 'Cooldown & stretching'"
                        ),
                        "description": (
                            "1-3 short sentences explaining how to do "
                            "this segment (warm-up, pace, effort, key focus)."
                       ),
                    }
                ],
            }
        ],
    },
    "constraints": [
            (
                "For each available time window (start_time → end_time), "
                "create 2–4 activities in sequence, typically including: "
                "a warm-up block, one or more main run blocks (e.g. intervals, tempo, steady run), "
                "and a cooldown & stretching block."
            ),
            (
                "The SUM of duration_minutes of all activities inside a single window "
                "should use MOST of that window. Aim for about 70%–90% of the available minutes. "
                "You may leave some minutes free as implicit rest, but DO NOT create separate "
                "'rest' activities."
            ),
            (
                "Activities in a window must be ordered in time and must not overlap. "
                "Start each activity at the appropriate time within the window."
            ),
            "Respect the available time window for each slot.",
            "Not every day should be hard; include rest / easy days with zero activities on some weekdays.",
            "Use realistic distances and durations for an amateur runner.",
        ],
    }

    print("=== ChatGPT weekly plan request payload ===")
    print(json.dumps(user_payload, ensure_ascii=False, indent=2))

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.6,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "Design a 7-day weekly running plan. "
                    "Return ONLY JSON, with no explanations. "
                    "Here is the input:\n\n"
                    + json.dumps(user_payload, ensure_ascii=False, indent=2)
                ),
            },
        ],
    )

    raw_content = resp.choices[0].message.content or ""
    print("=== ChatGPT weekly plan raw content ===")
    print(raw_content)

    obj = _extract_json_from_text(raw_content)

    print("=== ChatGPT weekly plan parsed JSON (keys) ===")
    print(obj.keys())

    weekly_template = obj.get("weekly_template", [])

    # Normalize by weekday and ensure we cover 0-6
    by_weekday: Dict[int, Dict[str, Any]] = {}
    for day in weekly_template:
        wd = int(day.get("weekday", -1))
        if 0 <= wd <= 6:
            by_weekday[wd] = {
                "weekday": wd,
                "activities": day.get("activities", []),
            }

    normalized_template: List[Dict[str, Any]] = []
    for wd in range(7):
        normalized_template.append(
            by_weekday.get(wd, {"weekday": wd, "activities": []})
        )

    return {
        "user_params": obj.get("user_params", user_params),
        "weekly_template": normalized_template,
    }


# ---------- AI weekly test plan (ChatGPT + stub fallback) ----------


def _hhmm_to_minutes(hhmm: str) -> int:
    h, m = map(int, hhmm.split(":"))
    return h * 60 + m


def _minutes_to_hhmm(total: int) -> str:
    total = total % (24 * 60)
    h = total // 60
    m = total % 60
    return f"{h:02d}:{m:02d}"


def _build_weekly_plan_stub(
    user_params: Dict[str, Any],
    weekly_slots: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Fallback stub implementation used when ChatGPT fails.
    Splits each available block into warm-up, main run, and cooldown.
    """
    level = (user_params.get("fitness_level") or "beginner").lower()
    if level == "athlete":
        km_per_hour = 11.0
    elif level == "regular":
        km_per_hour = 9.0
    else:
        km_per_hour = 7.0
    weekly_template: List[Dict[str, Any]] = []

    def _local_hhmm_to_minutes(hhmm: str) -> int:
        h, m = map(int, hhmm.split(":"))
        return h * 60 + m

    def _local_minutes_to_hhmm(total: int) -> str:
        total = total % (24 * 60)
        h = total // 60
        m = total % 60
        return f"{h:02d}:{m:02d}"

    for weekday in range(7):
        day_blocks = [b for b in weekly_slots if b["weekday"] == weekday]
        activities: List[Dict[str, Any]] = []

        for block in day_blocks:
            start = block["start_time"]
            end = block["end_time"]
            start_min = _local_hhmm_to_minutes(start)
            end_min = _local_hhmm_to_minutes(end)
            total = end_min - start_min
            if total <= 0:
                continue

            base = total // 3
            rest = total - base * 3
            warmup_dur = base
            run_dur = base + rest
            stretch_dur = base

            warmup_start = start_min
            run_start = warmup_start + warmup_dur
            stretch_start = run_start + run_dur

            run_distance = round(run_dur * (km_per_hour / 60.0), 2)

            warmup_desc = (
                "Easy jog or brisk walk with dynamic mobility drills to "
                "activate joints and muscles before the main session."
            )
            main_desc = (
                "Run at a comfortable, conversational pace. "
                "You should feel like you could keep going a bit longer at the end."
            )
            cooldown_desc = (
                "Gradually slow down to an easy walk, then do static stretches "
                "for calves, quads, hamstrings and hips to support recovery."
            )

            activities.append(
                {
                    "start_time": _local_minutes_to_hhmm(warmup_start),
                    "duration_minutes": warmup_dur,
                    "distance_km": 0.0,
                    "activity": "Warm-up & mobility",
                    "description": warmup_desc,
                }
            )
            activities.append(
                {
                    "start_time": _local_minutes_to_hhmm(run_start),
                    "duration_minutes": run_dur,
                    "distance_km": run_distance,
                    "activity": "Main run",
                    "description": main_desc,
                }
            )
            activities.append(
                {
                    "start_time": _local_minutes_to_hhmm(stretch_start),
                    "duration_minutes": stretch_dur,
                    "distance_km": 0.0,
                    "activity": "Cooldown & stretching",
                    "description": cooldown_desc,
                }
            )

        weekly_template.append(
            {
                "weekday": weekday,
                "activities": activities,
            }
        )

    return {
        "user_params": user_params,
        "weekly_template": weekly_template,
    }


def build_test_weekly_ai_plan(
    user_id: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Public entry point used by the FastAPI endpoint for preview.
    First tries ChatGPT, and if anything fails, falls back to a deterministic stub.
    """
    user = repo.get_user_by_id(user_id)
    if not user:
        raise ValueError("user not found")

    user_params = {
        "height_cm": payload.get("height_cm"),
        "weight_kg": payload.get("weight_kg"),
        "age": payload.get("age"),
        "goal_type": payload.get("goal_type"),
        "target_distance_m": payload.get("target_distance_m"),
        "target_weight_kg": payload.get("target_weight_kg"),
        "fitness_level": payload.get("fitness_level"), 
    }
    weekly_slots: List[Dict[str, Any]] = payload.get("weekly_slots", [])

    try:
        return _build_weekly_plan_via_chatgpt(user_params, weekly_slots)
    except Exception as e:
        # For a demo project, printing is enough; in a real app use logging.
        print("ChatGPT weekly plan failed, falling back to stub:", repr(e))
        return _build_weekly_plan_stub(user_params, weekly_slots)


def apply_test_weekly_ai_plan(
    user_id: str,
    payload: Dict[str, Any],
    default_days_ahead: int = 30,
    tz_name: str = CENTRAL_TZ,
) -> Dict[str, Any]:

    user = repo.get_user_by_id(user_id)
    if not user:
        raise ValueError("user not found")

    weekly_template = payload.get("weekly_template")
    if not isinstance(weekly_template, list):
        raise ValueError("weekly_template is required and must be a list")


    days_ahead = int(payload.get("days") or default_days_ahead)
    if days_ahead <= 0:
        raise ValueError("days must be positive")

    tz = ZoneInfo(tz_name)
    today_local = datetime.now(tz).date()

    start_date_str = payload.get("start_date")
    if start_date_str:

        start_date = date.fromisoformat(start_date_str)
    else:
        start_date = today_local + timedelta(days=1)

    end_date_excl = start_date + timedelta(days=days_ahead)

    template_by_weekday: Dict[int, List[Dict[str, Any]]] = {}
    for day in weekly_template:
        wd = int(day.get("weekday", -1))
        if 0 <= wd <= 6:
            template_by_weekday[wd] = day.get("activities", []) or []

    created: List[Dict[str, Any]] = []
    cleared_dates: List[str] = []

    d = start_date
    while d < end_date_excl:
        date_str = d.isoformat()
        weekday = d.weekday()       

        activities = template_by_weekday.get(weekday, [])

        existing = repo.list_daily_plans_for_date(user_id, date_str)
        if existing:
            cleared_dates.append(date_str)
            for p in existing:
                repo.delete_daily_plan(user_id, p["id"])

        for act in activities:
            created.append(
                repo.create_daily_plan(
                    user_id=user_id,
                    date_str=date_str,
                    start_time_local=act["start_time"],
                    duration_minutes=int(act["duration_minutes"]),
                    distance_km=float(act["distance_km"]),
                    activity=act["activity"],
                    description=act.get("description"),
                )
            )

        d += timedelta(days=1)

    return {
        "timezone": tz_name,
        "start_date": start_date.isoformat(),
        "end_date": (end_date_excl - timedelta(days=1)).isoformat(),
        "created_count": len(created),
        "cleared_dates": cleared_dates,
        "weekly_template": weekly_template,
    }

