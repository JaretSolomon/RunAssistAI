import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Iterable, Dict, Any, Optional

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "runtracker.db")

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  role TEXT NOT NULL DEFAULT 'runner',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS run_sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  total_distance REAL NOT NULL DEFAULT 0,
  total_duration_seconds INTEGER NOT NULL DEFAULT 0,
  note TEXT,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS run_metrics (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  distance REAL NOT NULL,
  duration_seconds INTEGER NOT NULL,
  start_time TEXT,
  end_time TEXT,
  FOREIGN KEY (session_id) REFERENCES run_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_time ON run_sessions(user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_session ON run_metrics(session_id);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Repo:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript(SCHEMA_SQL)

    def resolve_or_create_user(self, name: str, role: str = "runner") -> Dict[str, Any]:
        with self._conn() as conn:
            cur = conn.execute("SELECT id, name, role, created_at FROM users WHERE name=?", (name,))
            row = cur.fetchone()
            if row:
                return dict(row)
            user_id = uuid.uuid4().hex
            now = now_iso()
            conn.execute(
                "INSERT INTO users(id, name, role, created_at) VALUES(?,?,?,?)",
                (user_id, name, role, now),
            )
            return {"id": user_id, "name": name, "role": role, "created_at": now}


    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.execute("SELECT id, name, role, created_at FROM users WHERE id=?", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_active_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT * FROM run_sessions WHERE user_id=? AND ended_at IS NULL", (user_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def create_active_session(self, user_id: str, note: Optional[str] = None) -> Dict[str, Any]:
        sess_id = uuid.uuid4().hex
        start_time = now_iso()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO run_sessions(id, user_id, started_at, note) VALUES(?,?,?,?)",
                (sess_id, user_id, start_time, note),
            )
        return {"session_id": sess_id, "started_at": start_time, "note": note}

    def add_metric(
        self,
        session_id: str,
        distance_km: float,
        duration_seconds: int,
        start_time: Optional[str],
        end_time: Optional[str],
    ) -> Dict[str, Any]:
        metric_id = uuid.uuid4().hex
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO run_metrics(id, session_id, distance, duration_seconds, start_time, end_time) "
                "VALUES (?,?,?,?,?,?)",
                (metric_id, session_id, distance_km, duration_seconds, start_time, end_time),
            )
            conn.execute(
                "UPDATE run_sessions "
                "SET total_distance = total_distance + ?, total_duration_seconds = total_duration_seconds + ? "
                "WHERE id=?",
                (distance_km, duration_seconds, session_id),
            )
        return {"metric_id": metric_id, "distance_km": distance_km, "duration_seconds": duration_seconds}

    def finish_session(self, session_id: str, total_distance_km: Optional[float]) -> Dict[str, Any]:
        with self._conn() as conn:
            cur = conn.execute("SELECT * FROM run_sessions WHERE id=?", (session_id,))
            sess = cur.fetchone()
            if not sess:
                raise ValueError("session not found")
            end_time = now_iso()
            if total_distance_km is not None:
                conn.execute(
                    "UPDATE run_sessions SET ended_at=?, total_distance=? WHERE id=?",
                    (end_time, total_distance_km, session_id),
                )
            else:
                conn.execute("UPDATE run_sessions SET ended_at=? WHERE id=?", (end_time, session_id))
        return {"session_id": session_id, "ended_at": end_time, "total_distance_km": total_distance_km}

    def fetch_history_by_user_id(self, user_id: str, limit: int = 20) -> Dict[str, Any]:
        with self._conn() as conn:
            user = self.get_user_by_id(user_id)
            if not user:
                return {"user_id": "", "username": "", "count": 0, "sessions": []}
            cur = conn.execute(
                "SELECT id, started_at, ended_at, total_distance, total_duration_seconds "
                "FROM run_sessions WHERE user_id=? ORDER BY started_at DESC LIMIT ?",
                (user_id, limit),
            )
            sessions = []
            for row in cur.fetchall():
                sid = row["id"]
                cm = conn.execute(
                    "SELECT id, distance, duration_seconds, start_time, end_time "
                    "FROM run_metrics WHERE session_id=? ORDER BY id ASC",
                    (sid,),
                )
                metrics = [dict(mr) for mr in cm.fetchall()]
                sessions.append(
                    {
                        "id": sid,
                        "started_at": row["started_at"],
                        "ended_at": row["ended_at"],
                        "total_distance": row["total_distance"],
                        "total_duration_seconds": row["total_duration_seconds"],
                        "metrics": metrics,
                    }
                )
            return {"user_id": user_id, "username": user["name"], "count": len(sessions), "sessions": sessions}

    def fetch_recent_for_prompt_by_user_id(self, user_id: str, last_n: int = 5) -> Dict[str, Any]:
        with self._conn() as conn:
            user = self.get_user_by_id(user_id)
            if not user:
                return {
                    "user_id": "",
                    "username": "",
                    "role": "runner",
                    "totals": {"total_distance": 0.0, "sessions": 0},
                    "recent_sessions": [],
                }
            cur = conn.execute(
                "SELECT id, started_at, ended_at, total_distance, total_duration_seconds "
                "FROM run_sessions WHERE user_id=? ORDER BY started_at DESC LIMIT ?",
                (user_id, last_n),
            )
            rows = cur.fetchall()
            total_dist, recent = 0.0, []
            for r in rows:
                dist, dur = float(r["total_distance"]), int(r["total_duration_seconds"])
                total_dist += dist
                pace = None
                if dist > 0:
                    s_per_km = dur / dist
                    pace = f"{int(s_per_km)//60:02d}:{int(s_per_km)%60:02d} /km"
                recent.append(
                    {
                        "session_id": r["id"],
                        "started_at": r["started_at"],
                        "ended_at": r["ended_at"],
                        "total_distance_km": round(dist, 3),
                        "total_duration_seconds": dur,
                        "avg_pace": pace,
                    }
                )
            return {
                "user_id": user_id,
                "username": user["name"],
                "role": user["role"],
                "totals": {"total_distance": round(total_dist, 3), "sessions": len(rows)},
                "recent_sessions": recent,
            }
