from fastapi import FastAPI, Body, Path, Query
from pydantic import BaseModel, Field
from typing import Optional
from .services import (
    resolve_or_create_user,
    start_run,
    add_metric,
    stop_run,
    view_history,
    build_prompt_payload,
)

app = FastAPI(title="RunTracker API")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Request Models ----------
class ResolveUserIn(BaseModel):
    username: str = Field(...)


class StartRunIn(BaseModel):
    note: Optional[str] = None


class AddMetricIn(BaseModel):
    distance_km: float = Field(..., gt=0)
    duration_seconds: int = Field(..., gt=0)
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class StopRunIn(BaseModel):
    total_distance_km: Optional[float] = Field(None, gt=0)


@app.post("/users/resolve")
def api_resolve_user(payload: ResolveUserIn):
    return resolve_or_create_user(payload.username)


@app.post("/users/{user_id}/run/start")
def api_start_run(user_id: str = Path(...), payload: StartRunIn = Body(default=StartRunIn())):
    return start_run(user_id, note=payload.note)


@app.post("/users/{user_id}/run/add-metric")
def api_add_metric(user_id: str = Path(...), payload: AddMetricIn = Body(...)):
    return add_metric(
        user_id, payload.distance_km, payload.duration_seconds, payload.start_time, payload.end_time
    )


@app.post("/users/{user_id}/run/stop")
def api_stop_run(user_id: str = Path(...), payload: StopRunIn = Body(default=StopRunIn())):
    return stop_run(user_id, total_distance_km=payload.total_distance_km)


@app.get("/users/{user_id}/history")
def api_history(user_id: str = Path(...), limit: int = Query(20, ge=1, le=200)):
    return view_history(user_id, limit)


@app.get("/users/{user_id}/prompt")
def api_prompt(user_id: str = Path(...), last_n: int = Query(5, ge=1, le=50)):
    return build_prompt_payload(user_id, last_n)
