from __future__ import annotations

import sqlite3
import uuid
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import random


def _utcnow_iso() -> str:
    """
    Return the current UTC time as an ISO-8601 string with seconds precision
    and a trailing 'Z', e.g. '2025-11-23T12:34:56Z'.
    """
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _text_id(value: Any) -> str:
    """
    Ensure IDs passed to SQLite are plain strings.
    """
    if value is None:
        raise ValueError("user_id cannot be None")
    if isinstance(value, str):
        return value
    # Handle UUID objects and other types
    result = str(value).strip()
    if not result:
        raise ValueError("user_id cannot be empty")
    return result


class Repo:
    """
    Simple SQLite repository for the RunTracker application.

    This class encapsulates all database access: schema creation, user and
    settings management, running sessions and metrics, training plans, and
    daily running plans.
    """

    def __init__(self, db_path: str = "runtracker.db") -> None:
        """
        Initialize the repository and ensure the database schema exists.
        """
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()

    # ---------- schema ----------

    def _ensure_schema(self) -> None:
        """
        Create all required tables and indexes if they do not already exist.
        """
        cur = self.conn.cursor()

        # users
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL,
                runner_code INTEGER,
                created_at TEXT NOT NULL,
                password_hash TEXT
            )
            """
        )

        # user settings
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id TEXT PRIMARY KEY,
                calories_per_hour REAL NOT NULL,  
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        # sessions
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                total_distance_km REAL NOT NULL DEFAULT 0,
                total_duration_seconds INTEGER NOT NULL DEFAULT 0,
                total_calories REAL NOT NULL DEFAULT 0,
                calories_per_hour REAL NOT NULL,
                note TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        # metrics
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                distance REAL NOT NULL,
                duration_seconds INTEGER NOT NULL,
                start_time TEXT,
                end_time TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
            """
        )

        # training plans
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS plans (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                goal_type TEXT NOT NULL,
                target_event_date TEXT,
                meta_json TEXT,
                created_by_ai INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS plan_entries (
                id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                day_index INTEGER NOT NULL,
                date TEXT,
                focus TEXT,
                target_distance_km REAL,
                target_duration_seconds INTEGER,
                intensity TEXT,
                warmup_text TEXT,
                workout_text TEXT,
                cooldown_text TEXT,
                nutrition_text TEXT,
                notes TEXT,
                linked_session_id TEXT,
                FOREIGN KEY (plan_id) REFERENCES plans(id),
                FOREIGN KEY (linked_session_id) REFERENCES sessions(id)
            )
            """
        )

        # weekly_plan_rules (legacy)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS weekly_plan_rules (
                id TEXT PRIMARY KEY,
                user_id TEXT UNIQUE NOT NULL,
                weekday INTEGER NOT NULL, -- 0=Mon ... 6=Sun
                start_time TEXT NOT NULL, -- 'HH:MM'
                duration_minutes INTEGER NOT NULL,
                distance_km REAL NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        # daily_running_plan
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_running_plan (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                plan_date TEXT NOT NULL,        -- 'YYYY-MM-DD'
                start_time_local TEXT NOT NULL, -- 'HH:MM'
                duration_minutes INTEGER NOT NULL,
                distance_km REAL NOT NULL,
                activity TEXT,
                description TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_daily_running_plan_user_date
            ON daily_running_plan(user_id, plan_date)
            """
        )

        # coach_runner_links
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS coach_runner_links (
                id TEXT PRIMARY KEY,
                coach_id TEXT NOT NULL,
                runner_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(coach_id, runner_id),
                FOREIGN KEY (coach_id) REFERENCES users(id),
                FOREIGN KEY (runner_id) REFERENCES users(id)
            )
            """
        )

        # coach_notes
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS coach_notes (
                id TEXT PRIMARY KEY,
                runner_id TEXT NOT NULL,
                coach_id TEXT NOT NULL,
                coach_name TEXT,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (runner_id) REFERENCES users(id),
                FOREIGN KEY (coach_id) REFERENCES users(id)
            )
            """
        )

        # Strava credentials per runner
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS strava_credentials (
                user_id TEXT PRIMARY KEY,
                athlete_id INTEGER NOT NULL,
                access_token TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                scope TEXT,
                last_sync TEXT,
                last_sync_cursor INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        # Imported Strava activities to avoid duplicates
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS strava_activity_imports (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                strava_activity_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                activity_start TEXT,
                distance_km REAL,
                moving_time INTEGER,
                payload_json TEXT,
                imported_at TEXT NOT NULL,
                UNIQUE(user_id, strava_activity_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
            """
        )

        self.conn.commit()

    # ---------- users ----------

    def resolve_or_create_user(self, username: str, role: str) -> Dict[str, Any]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        if row:
            return dict(row)

        if role not in ("runner", "coach"):
            role = "runner"

        user_id = uuid.uuid4().hex
        now = _utcnow_iso()
        runner_code = None
        if role == "runner":
            runner_code = self._generate_unique_runner_code()

        cur.execute(
            "INSERT INTO users(id, username, role, runner_code, created_at, password_hash) VALUES (?,?,?,?,?,?)",
            (user_id, username, role, runner_code, now, None),
      )
        self.conn.commit()
        return {
            "id": user_id,
            "username": username,
            "role": role,
            "runner_code": runner_code,
            "created_at": now,
        }

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        return dict(row) if row else None

    def create_user(self, username: str, role: str, password_hash: str) -> Dict[str, Any]:
        if role not in ("runner", "coach"):
            raise ValueError("role must be 'runner' or 'coach'")

        existing = self.get_user_by_username(username)
        if existing:
            raise ValueError("username already exists")

        user_id = uuid.uuid4().hex
        now = _utcnow_iso()

        runner_code = None
        if role == "runner":
            runner_code = self._generate_unique_runner_code()

        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO users(id, username, role, runner_code, created_at, password_hash)
            VALUES (?,?,?,?,?,?)
            """,
            (user_id, username, role, runner_code, now, password_hash),
        )
        self.conn.commit()

        return {
            "id": user_id,
            "username": username,
            "role": role,
            "runner_code": runner_code,
            "created_at": now,
        }

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        # Normalize to ensure it's a plain string
        normalized = _text_id(user_id)
        # SQLite requires plain Python strings, ensure we have one
        if not isinstance(normalized, str):
            normalized = str(normalized)
        cur = self.conn.cursor()
        # Use a list instead of tuple - some SQLite versions prefer this
        cur.execute("SELECT * FROM users WHERE id=?", [normalized])
        row = cur.fetchone()
        return dict(row) if row else None

    # ---------- settings ----------

    def get_or_create_user_settings(self, user_id: str) -> Dict[str, Any]:
        # Normalize to ensure it's a plain string
        normalized = _text_id(user_id)
        # SQLite requires plain Python strings, ensure we have one
        if not isinstance(normalized, str):
            normalized = str(normalized)
        cur = self.conn.cursor()
        # Use a list instead of tuple - some SQLite versions prefer this
        cur.execute("SELECT * FROM user_settings WHERE user_id=?", [normalized])
        row = cur.fetchone()
        if row:
            return {
                "user_id": row["user_id"],
                "calories_per_hour": row["calories_per_hour"],
            }

        try:
            cur.execute(
                "INSERT INTO user_settings(user_id, calories_per_hour) VALUES (?, ?)",
                [normalized, 600.0],
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            self.conn.rollback()
            cur.execute("SELECT * FROM user_settings WHERE user_id=?", [normalized])
            row = cur.fetchone()
            if row:
                return {
                    "user_id": row["user_id"],
                    "calories_per_hour": row["calories_per_hour"],
                }
            raise
        return {"user_id": user_id, "calories_per_hour": 600.0}

    def update_user_calories_per_hour(self, user_id: str, value: float) -> Dict[str, Any]:
        user_id = _text_id(user_id)
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO user_settings(user_id, calories_per_hour)
            VALUES(?, ?)
            ON CONFLICT(user_id) DO UPDATE SET calories_per_hour=excluded.calories_per_hour
            """,
            (user_id, value),
        )
        self.conn.commit()
        return {"user_id": user_id, "calories_per_hour": value}

    # ---------- sessions / metrics ----------

    def get_active_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        user_id = _text_id(user_id)
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM sessions
            WHERE user_id=? AND ended_at IS NULL
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (user_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def create_active_session(
        self,
        user_id: str,
        note: Optional[str],
        calories_per_hour: float,
    ) -> Dict[str, Any]:
        user_id = _text_id(user_id)
        if self.get_active_session(user_id):
            raise ValueError("Active session already exists")

        sid = uuid.uuid4().hex
        now = _utcnow_iso()
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO sessions(
              id, user_id, started_at, ended_at,
              total_distance_km, total_duration_seconds, total_calories,
              calories_per_hour, note
            )
            VALUES (?, ?, ?, NULL, 0, 0, 0, ?, ?)
            """,
            (sid, user_id, now, calories_per_hour, note),
        )
        self.conn.commit()
        cur.execute("SELECT * FROM sessions WHERE id=?", (sid,))
        return dict(cur.fetchone())

    def _recalc_session_totals(self, session_id: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT SUM(distance) AS dist, SUM(duration_seconds) AS dur FROM metrics WHERE session_id=?",
            (session_id,),
        )
        row = cur.fetchone()
        total_dist = row["dist"] or 0.0
        total_dur = row["dur"] or 0
        cur.execute("SELECT calories_per_hour FROM sessions WHERE id=?", (session_id,))
        s = cur.fetchone()
        cph = s["calories_per_hour"]
        total_hours = total_dur / 3600.0
        total_cal = total_hours * cph
        cur.execute(
            """
            UPDATE sessions
            SET total_distance_km=?, total_duration_seconds=?, total_calories=?
            WHERE id=?
            """,
            (total_dist, total_dur, total_cal, session_id),
        )
        self.conn.commit()

    def add_metric(
        self,
        session_id: str,
        distance_km: float,
        duration_seconds: int,
        start_time: Optional[str],
        end_time: Optional[str],
    ) -> Dict[str, Any]:
        mid = uuid.uuid4().hex
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO metrics(id, session_id, distance, duration_seconds, start_time, end_time)
            VALUES (?,?,?,?,?,?)
            """,
            (mid, session_id, distance_km, duration_seconds, start_time, end_time),
        )
        self.conn.commit()
        self._recalc_session_totals(session_id)

        cur.execute("SELECT * FROM metrics WHERE id=?", (mid,))
        return dict(cur.fetchone())

    def finish_session(
        self,
        session_id: str,
        total_distance_km: Optional[float],
        elapsed_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT started_at, total_duration_seconds, calories_per_hour, total_distance_km
            FROM sessions
            WHERE id=?
            """,
            (session_id,),
        )
        row = cur.fetchone()
        if not row:
            raise ValueError("session not found")

        started_at = row["started_at"]
        dur = row["total_duration_seconds"] or 0
        cph = row["calories_per_hour"]
        old_dist = row["total_distance_km"]

        # If frontend provides elapsed_seconds, use it
        if elapsed_seconds is not None:
            dur = int(max(0, elapsed_seconds))
        else:
            # Keep the original "from start until now" fallback logic
            if dur == 0 and started_at:
                start_str = started_at.rstrip("Z")
                start_dt = datetime.fromisoformat(start_str)
                now_dt = datetime.utcnow()
                dur = int(max(0, (now_dt - start_dt).total_seconds()))

        total_hours = dur / 3600.0
        total_cal = total_hours * cph
        ended_at = _utcnow_iso()

        new_dist = total_distance_km if total_distance_km is not None else old_dist

        cur.execute(
            """
            UPDATE sessions
            SET total_distance_km=?,
                total_duration_seconds=?,
                total_calories=?,
                ended_at=?
            WHERE id=?
            """,
            (new_dist, dur, total_cal, ended_at, session_id),
        )

        self.conn.commit()
        cur.execute("SELECT * FROM sessions WHERE id=?", (session_id,))
        return dict(cur.fetchone())

    # ---------- history ----------

    def fetch_history_by_user_id(self, user_id: str, limit: int) -> Dict[str, Any]:
        # Normalize to ensure it's a plain string
        normalized = _text_id(user_id)
        # SQLite requires plain Python strings, ensure we have one
        if not isinstance(normalized, str):
            normalized = str(normalized)
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users WHERE id=?", [normalized])
        user = cur.fetchone()
        if not user:
            return {
                "user_id": None,
                "username": None,
                "count": 0,
                "sessions": [],
            } #Dashboard Data

        cur.execute(
            """
            SELECT * FROM sessions
            WHERE user_id=?
            ORDER BY started_at DESC
            LIMIT ?
            """,
            [normalized, limit],
        )
        sessions_rows = cur.fetchall()
        sessions: List[Dict[str, Any]] = []
        for s in sessions_rows:
            sid = s["id"]
            cur.execute(
                "SELECT * FROM metrics WHERE session_id=? ORDER BY id",
                (sid,),
            )
            metrics_rows = cur.fetchall()
            metrics = [dict(m) for m in metrics_rows]
            sessions.append(
                {
                    "id": s["id"],
                    "started_at": s["started_at"],
                    "ended_at": s["ended_at"],
                    "total_distance_km": s["total_distance_km"],
                    "total_duration_seconds": s["total_duration_seconds"],
                    "total_calories": s["total_calories"],
                    "calories_per_hour": s["calories_per_hour"],
                    "metrics": metrics,
                }
            )

        return {
            "user_id": user["id"],
            "username": user["username"],
            "count": len(sessions),
            "sessions": sessions,
        }

    def fetch_recent_for_prompt_by_user_id(self, user_id: str, last_n: int) -> Dict[str, Any]:
        return self.fetch_history_by_user_id(user_id, last_n)
#Strava Dashboard
    # ---------- training plans ----------

    def create_plan(
        self,
        user_id: str,
        name: str,
        goal_type: str,
        target_event_date: Optional[str],
        created_by_ai: bool,
        meta_json: Optional[Dict[str, Any]],
        entries: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        user_id = _text_id(user_id)
        plan_id = uuid.uuid4().hex
        now = _utcnow_iso()
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO plans(
              id, user_id, name, goal_type, target_event_date,
              meta_json, created_by_ai, created_at
            )
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                plan_id,
                user_id,
                name,
                goal_type,
                target_event_date,
                json.dumps(meta_json) if meta_json is not None else None,
                1 if created_by_ai else 0,
                now,
            ),
        )

        for e in entries:
            pe_id = uuid.uuid4().hex
            cur.execute(
                """
                INSERT INTO plan_entries(
                  id, plan_id, day_index, date, focus,
                  target_distance_km, target_duration_seconds,
                  intensity, warmup_text, workout_text,
                  cooldown_text, nutrition_text, notes,
                  linked_session_id
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)
                """,
                (
                    pe_id,
                    plan_id,
                    e.get("day_index", 0),
                    e.get("date"),
                    e.get("focus"),
                    e.get("target_distance_km"),
                    e.get("target_duration_seconds"),
                    e.get("intensity"),
                    e.get("warmup_text"),
                    e.get("workout_text"),
                    e.get("cooldown_text"),
                    e.get("nutrition_text"),
                    e.get("notes"),
                ),
            )

        self.conn.commit()
        return self.get_plan_with_entries(plan_id)

    def list_plans_by_user_id(self, user_id: str, limit: int) -> List[Dict[str, Any]]:
        user_id = _text_id(user_id)
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM plans
            WHERE user_id=?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        return [dict(p) for p in cur.fetchall()]

    def get_plan_with_entries(self, plan_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM plans WHERE id=?", (plan_id,))
        p = cur.fetchone()
        if not p:
            return None
        cur.execute(
            "SELECT * FROM plan_entries WHERE plan_id=? ORDER BY day_index, id",
            (plan_id,),
        )
        entries = [dict(e) for e in cur.fetchall()]
        plan = dict(p)
        if plan.get("meta_json"):
            try:
                plan["meta_json"] = json.loads(plan["meta_json"])
            except Exception:
                pass
        plan["entries"] = entries
        return plan

    def link_plan_entry_to_session(self, plan_entry_id: str, session_id: str) -> Dict[str, Any]:
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE plan_entries SET linked_session_id=? WHERE id=?",
            (session_id, plan_entry_id),
        )
        self.conn.commit()
        cur.execute("SELECT * FROM plan_entries WHERE id=?", (plan_entry_id,))
        return dict(cur.fetchone())

    # ---------- stats helpers ----------

    def stats_overview(
        self, user_id: str, since_iso: str, only_strava: bool = False
    ) -> Dict[str, Any]:
        user_id = _text_id(user_id)
        cur = self.conn.cursor()
        query = """
            SELECT
              COUNT(*) AS total_sessions,
              COALESCE(SUM(total_distance_km), 0) AS total_distance_km,
              COALESCE(SUM(total_duration_seconds), 0) AS total_duration_seconds
            FROM sessions
            WHERE user_id=? AND started_at>=?
        """
        params: List[Any] = [user_id, since_iso]
        if only_strava:
            query += """
            AND EXISTS (
                SELECT 1 FROM strava_activity_imports sai
                WHERE sai.session_id = sessions.id
            )
            """
        cur.execute(query, params)
        row = cur.fetchone()
        return {
            "total_sessions": row["total_sessions"],
            "total_distance_km": row["total_distance_km"],
            "total_duration_seconds": row["total_duration_seconds"],
        }

    def stats_daily(
        self, user_id: str, since_iso: str, only_strava: bool = False
    ) -> List[Dict[str, Any]]:
        user_id = _text_id(user_id)
        cur = self.conn.cursor()
        query = """
            SELECT
              substr(started_at, 1, 10) AS date,
              COUNT(*) AS sessions,
              COALESCE(SUM(total_distance_km), 0) AS distance_km,
              COALESCE(SUM(total_duration_seconds), 0) AS duration_seconds
            FROM sessions
            WHERE user_id=? AND started_at>=?
            GROUP BY date
            ORDER BY date
        """
        params: List[Any] = [user_id, since_iso]
        if only_strava:
            query += """
            AND EXISTS (
                SELECT 1 FROM strava_activity_imports sai
                WHERE sai.session_id = sessions.id
            )
            """
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]

    def stats_sessions_since(
        self, user_id: str, since_iso: str, only_strava: bool = False
    ) -> List[Dict[str, Any]]:
        user_id = _text_id(user_id)
        cur = self.conn.cursor()
        query = """
            SELECT
              id, user_id, started_at,
              total_distance_km, total_duration_seconds, total_calories
            FROM sessions
            WHERE user_id=? AND started_at>=?
            ORDER BY started_at
        """
        params: List[Any] = [user_id, since_iso]
        if only_strava:
            query += """
            AND EXISTS (
                SELECT 1 FROM strava_activity_imports sai
                WHERE sai.session_id = sessions.id
            )
            """
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]

    def fetch_sessions_between(
        self,
        user_id: str,
        start_iso: str,
        end_iso: str,
        only_strava: bool = False,
    ) -> List[Dict[str, Any]]:
        # Normalize to ensure it's a plain string
        normalized = _text_id(user_id)
        # SQLite requires plain Python strings, ensure we have one
        if not isinstance(normalized, str):
            normalized = str(normalized)
        cur = self.conn.cursor()
        query = """
            SELECT * FROM sessions
            WHERE user_id=? AND started_at>=? AND started_at<?
            ORDER BY started_at
        """
        # Ensure all params are proper strings
        params: List[Any] = [normalized, str(start_iso), str(end_iso)]
        if only_strava:
            query += """
            AND EXISTS (
                SELECT 1 FROM strava_activity_imports sai
                WHERE sai.session_id = sessions.id
            )
            """
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]

    def fetch_daily_aggregates_between(
        self,
        user_id: str,
        start_iso: str,
        end_iso: str,
        only_strava: bool = False,
    ) -> List[Dict[str, Any]]:
        user_id = _text_id(user_id)
        cur = self.conn.cursor()
        query = """
            SELECT
              substr(started_at, 1, 10) AS date,
              COUNT(*) AS sessions,
              COALESCE(SUM(total_distance_km), 0) AS total_distance_km,
              COALESCE(SUM(total_duration_seconds), 0) AS total_duration_seconds,
              COALESCE(SUM(total_calories), 0) AS total_calories
            FROM sessions
            WHERE user_id=? AND started_at>=? AND started_at<?
            GROUP BY date
            ORDER BY date
        """
        params: List[Any] = [user_id, start_iso, end_iso]
        if only_strava:
            query += """
            AND EXISTS (
                SELECT 1 FROM strava_activity_imports sai
                WHERE sai.session_id = sessions.id
            )
            """
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]

    # ---------- weekly plan rule (legacy interface) ----------

    def get_weekly_plan_rule_or_default(self, user_id: str) -> Dict[str, Any]:
        user_id = _text_id(user_id)
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM weekly_plan_rules WHERE user_id=?",
            (user_id,),
        )
        row = cur.fetchone()
        if row:
            return dict(row)

        now = _utcnow_iso()
        rid = uuid.uuid4().hex
        cur.execute(
            """
            INSERT INTO weekly_plan_rules(
              id, user_id, weekday, start_time,
              duration_minutes, distance_km, created_at, updated_at
            )
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (rid, user_id, 0, "07:00", 45, 5.0, now, now),
        )
        self.conn.commit()
        return {
            "id": rid,
            "user_id": user_id,
            "weekday": 0,
            "start_time": "07:00",
            "duration_minutes": 45,
            "distance_km": 5.0,
            "created_at": now,
            "updated_at": now,
        }

    def upsert_weekly_plan_rule(
        self,
        user_id: str,
        weekday: int,
        start_time: str,
        duration_minutes: int,
        distance_km: float,
    ) -> Dict[str, Any]:
        # Normalize to ensure it's a plain string
        normalized = _text_id(user_id)
        # SQLite requires plain Python strings, ensure we have one
        if not isinstance(normalized, str):
            normalized = str(normalized)
        now = _utcnow_iso()
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO weekly_plan_rules(
              id, user_id, weekday, start_time,
              duration_minutes, distance_km, created_at, updated_at
            )
            VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
              weekday=excluded.weekday,
              start_time=excluded.start_time,
              duration_minutes=excluded.duration_minutes,
              distance_km=excluded.distance_km,
              updated_at=excluded.updated_at
            """,
            (uuid.uuid4().hex, normalized, weekday, start_time, duration_minutes, distance_km, now, now),
        )
        self.conn.commit()
        cur.execute("SELECT * FROM weekly_plan_rules WHERE user_id=?", [normalized])
        return dict(cur.fetchone())

    # ---------- daily running plan ----------

    def create_daily_plan(
        self,
        user_id: str,
        date_str: str,
        start_time_local: str,
        duration_minutes: int,
        distance_km: float,
        activity: Optional[str],
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        user_id = _text_id(user_id)
        pid = uuid.uuid4().hex
        now = _utcnow_iso()
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO daily_running_plan(
              id, user_id, plan_date, start_time_local,
              duration_minutes, distance_km, activity, description, created_at
            )
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                pid,
                user_id,
                date_str,
                start_time_local,
                duration_minutes,
                distance_km,
                activity,
                description,
                now,
            ),
        )
        self.conn.commit()
        cur.execute("SELECT * FROM daily_running_plan WHERE id=?", (pid,))
        return dict(cur.fetchone())

    def delete_daily_plan(self, user_id: str, plan_id: str) -> None:
        user_id = _text_id(user_id)
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM daily_running_plan WHERE id=? AND user_id=?",
            (plan_id, user_id),
        )
        self.conn.commit()

    def list_daily_plans_for_month(
        self,
        user_id: str,
        start_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        user_id = _text_id(user_id)
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM daily_running_plan
            WHERE user_id=? AND plan_date>=? AND plan_date<?
            ORDER BY plan_date, start_time_local, id
            """,
            (user_id, start_date, end_date),
        )
        return [dict(r) for r in cur.fetchall()]

    def list_daily_plans_for_date(
        self,
        user_id: str,
        date_str: str,
    ) -> List[Dict[str, Any]]:
        user_id = _text_id(user_id)
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM daily_running_plan
            WHERE user_id=? AND plan_date=?
            ORDER BY start_time_local, id
            """,
            (user_id, date_str),
        )
        return [dict(r) for r in cur.fetchall()]

    # ---------- runner code & coach <-> runner ----------

    def _generate_unique_runner_code(self) -> int:
        cur = self.conn.cursor()
        for _ in range(50):
            code = random.randint(1, 10000)
            cur.execute("SELECT 1 FROM users WHERE runner_code=?", (code,))
            if not cur.fetchone():
                return code
        raise ValueError("No available runner_code in range 1–10000")

    def get_user_by_runner_code(self, code: int) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE runner_code=? AND role='runner'",
            (code,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def bind_coach_to_runner(self, coach_id: str, runner_id: str) -> None:
        cur = self.conn.cursor()
        link_id = uuid.uuid4().hex
        now = _utcnow_iso()
        try:
            cur.execute(
                """
                INSERT INTO coach_runner_links(id, coach_id, runner_id, created_at)
                VALUES (?,?,?,?)
                """,
                (link_id, coach_id, runner_id, now),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            # If the link already exists, ignore it
            pass

    def list_runners_for_coach(self, coach_id: str) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT u.id, u.username, u.runner_code
            FROM coach_runner_links cr
            JOIN users u ON cr.runner_id = u.id
            WHERE cr.coach_id=?
            ORDER BY u.username
            """,
            (coach_id,),
        )
        return [dict(r) for r in cur.fetchall()]

    # ---------- coach notes ----------

    def create_coach_note(
        self,
        coach_id: str,
        runner_id: str,
        coach_name: Optional[str],
        content: str,
    ) -> Dict[str, Any]:
        note_id = uuid.uuid4().hex
        now = _utcnow_iso()
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO coach_notes(
              id, runner_id, coach_id, coach_name, content, created_at
            )
            VALUES (?,?,?,?,?,?)
            """,
            (note_id, runner_id, coach_id, coach_name, content, now),
        )
        self.conn.commit()
        cur.execute("SELECT * FROM coach_notes WHERE id=?", (note_id,))
        return dict(cur.fetchone())

    def list_coach_notes_for_runner(self, runner_id: str) -> List[Dict[str, Any]]:
        runner_id = _text_id(runner_id)
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM coach_notes
            WHERE runner_id=?
            ORDER BY created_at DESC, id DESC
            """,
            (runner_id,),
        )
        return [dict(r) for r in cur.fetchall()]

    # ---------- Strava integration ----------

    def upsert_strava_credentials(
        self,
        user_id: str,
        athlete_id: int,
        access_token: str,
        refresh_token: str,
        expires_at: int,
        scope: Optional[str],
    ) -> Dict[str, Any]:
        user_id = _text_id(user_id)
        now = _utcnow_iso()
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO strava_credentials(
                user_id, athlete_id, access_token, refresh_token,
                expires_at, scope, last_sync, last_sync_cursor,
                created_at, updated_at
            )
            VALUES(?,?,?,?,?,?,NULL,NULL,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
                athlete_id=excluded.athlete_id,
                access_token=excluded.access_token,
                refresh_token=excluded.refresh_token,
                expires_at=excluded.expires_at,
                scope=excluded.scope,
                updated_at=excluded.updated_at
            """,
            (user_id, athlete_id, access_token, refresh_token, expires_at, scope, now, now),
        )
        self.conn.commit()
        return self.get_strava_credentials(user_id)

    def get_strava_credentials(self, user_id: str) -> Optional[Dict[str, Any]]:
        # Normalize to ensure it's a plain string
        normalized = _text_id(user_id)
        # SQLite requires plain Python strings, ensure we have one
        if not isinstance(normalized, str):
            normalized = str(normalized)
        cur = self.conn.cursor()
        # Use a list instead of tuple - some SQLite versions prefer this
        cur.execute("SELECT * FROM strava_credentials WHERE user_id=?", [normalized])
        row = cur.fetchone()
        return dict(row) if row else None

    def update_strava_tokens(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str,
        expires_at: int,
    ) -> None:
        user_id = _text_id(user_id)
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE strava_credentials
            SET access_token=?, refresh_token=?, expires_at=?, updated_at=?
            WHERE user_id=?
            """,
            (access_token, refresh_token, expires_at, _utcnow_iso(), user_id),
        )
        self.conn.commit()

    def touch_strava_sync(
        self,
        user_id: str,
        last_sync_cursor: Optional[int],
        last_sync_iso: Optional[str],
    ) -> None:
        user_id = _text_id(user_id)
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE strava_credentials
            SET last_sync=?, last_sync_cursor=?, updated_at=?
            WHERE user_id=?
            """,
            (last_sync_iso, last_sync_cursor, _utcnow_iso(), user_id),
        )
        self.conn.commit()

    def has_imported_strava_activity(self, user_id: str, activity_id: int) -> bool:
        user_id = _text_id(user_id)
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT 1 FROM strava_activity_imports
            WHERE user_id=? AND strava_activity_id=?
            """,
            (user_id, activity_id),
        )
        return cur.fetchone() is not None

    def record_strava_activity_import(
        self,
        user_id: str,
        activity_id: int,
        session_id: str,
        activity_start: Optional[str],
        distance_km: float,
        moving_time: int,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        user_id = _text_id(user_id)
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO strava_activity_imports(
                id, user_id, strava_activity_id, session_id,
                activity_start, distance_km, moving_time,
                payload_json, imported_at
            )
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                uuid.uuid4().hex,
                user_id,
                activity_id,
                session_id,
                activity_start,
                distance_km,
                moving_time,
                json.dumps(payload) if payload is not None else None,
                _utcnow_iso(),
            ),
        )
        self.conn.commit()

    def fetch_recent_strava_runs(self, user_id: str, limit: int) -> List[Dict[str, Any]]:
        user_id = _text_id(user_id)
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT
                sai.id AS import_id,
                sai.strava_activity_id,
                sai.activity_start,
                sai.distance_km,
                sai.moving_time,
                sai.imported_at,
                sai.payload_json,
                s.id AS session_id,
                s.started_at,
                s.total_distance_km,
                s.total_duration_seconds,
                s.total_calories
            FROM strava_activity_imports sai
            JOIN sessions s ON s.id = sai.session_id
            WHERE sai.user_id=?
            ORDER BY sai.activity_start DESC, sai.imported_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    def create_session_from_import(
        self,
        user_id: str,
        started_at_iso: str,
        duration_seconds: int,
        distance_km: float,
        calories_per_hour: float,
        note: Optional[str] = None,
        calories_total: Optional[float] = None,
    ) -> Dict[str, Any]:
        user_id = _text_id(user_id)
        sid = uuid.uuid4().hex
        try:
            dt = datetime.fromisoformat(started_at_iso.replace("Z", "+00:00"))
        except ValueError:
            dt = datetime.utcnow()
        ended_dt = dt + timedelta(seconds=max(0, duration_seconds))
        ended_iso = ended_dt.isoformat().replace("+00:00", "Z")

        total_hours = max(0.0, duration_seconds / 3600.0)
        total_cal = (
            float(calories_total)
            if calories_total is not None
            else total_hours * calories_per_hour
        )

        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO sessions(
                id, user_id, started_at, ended_at,
                total_distance_km, total_duration_seconds, total_calories,
                calories_per_hour, note
            )
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                sid,
                user_id,
                started_at_iso,
                ended_iso,
                distance_km,
                duration_seconds,
                total_cal,
                calories_per_hour,
                note,
            ),
        )
        self.conn.commit()

        # Store a single metric so summaries remain consistent
        self.add_metric(
            session_id=sid,
            distance_km=distance_km,
            duration_seconds=duration_seconds,
            start_time=started_at_iso,
            end_time=ended_iso,
        )

        cur.execute("SELECT * FROM sessions WHERE id=?", (sid,))
        return dict(cur.fetchone())

    def get_strava_activity_detail(
        self, user_id: str, strava_activity_id: int
    ) -> Optional[Dict[str, Any]]:
        user_id = _text_id(user_id)
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT sai.*, s.total_calories, s.total_duration_seconds,
                   s.total_distance_km, s.calories_per_hour, s.note
            FROM strava_activity_imports sai
            JOIN sessions s ON s.id = sai.session_id
            WHERE sai.user_id=? AND sai.strava_activity_id=?
            """,
            (user_id, strava_activity_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None
