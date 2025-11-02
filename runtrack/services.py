#services.py
from typing import Optional, Dict, Any
from .repository import Repo

repo = Repo()

def resolve_or_create_user(username: str, role: str = "runner") -> Dict[str, Any]:
    return repo.resolve_or_create_user(username, role)

#started_at
def start_run(user_id: str, note: Optional[str] = None) -> Dict[str, Any]:
    return repo.create_active_session(user_id, note)

def add_metric(user_id: str, distance_km: float, duration_seconds: int,
               start_time: Optional[str] = None, end_time: Optional[str] = None) -> Dict[str, Any]:
    active = repo.get_active_session(user_id)
    if not active:
        raise ValueError("no active session for user")
    return repo.add_metric(active["id"], distance_km, duration_seconds, start_time, end_time)

#end
def stop_run(user_id: str, total_distance_km: Optional[float] = None) -> Dict[str, Any]:
    active = repo.get_active_session(user_id)
    if not active:
        raise ValueError("no active session for user")
    return repo.finish_session(active["id"], total_distance_km)

#view history and Prompt
def view_history(user_id: str, limit: int = 20) -> Dict[str, Any]:
    return repo.fetch_history_by_user(user_id, limit)

def build_prompt_payload(user_id: str, last_n: int = 5) -> Dict[str, Any]:
    return repo.prompt_payload(user_id, last_n)
