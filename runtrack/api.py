from typing import Optional, List, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import services

app = FastAPI(title="RunAssistAI Demo API")

# Allow frontend Vite(5173) to access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Pydantic models ----------


class UserResolveIn(BaseModel):
    username: str


class LoginIn(BaseModel):
    username: str
    role: str  # "runner" or "coach"


class RegisterIn(BaseModel):
    username: str
    role: Literal["runner", "coach"]  # runner or coach


class UserOut(BaseModel):
    id: str
    name: str
    role: str = "runner"
    runner_code: Optional[int] = None  # Only runners have this value


class StartRunIn(BaseModel):
    note: Optional[str] = None


class StopRunIn(BaseModel):
    total_distance_km: Optional[float] = None
    elapsed_seconds: Optional[int] = None


class CaloriesPerHourIn(BaseModel):
    calories_per_hour: float


class DayPlanCreateIn(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM")
    duration_minutes: int
    distance_km: float
    activity: Optional[str] = None
    description: Optional[str] = None


# AI testing plan input model
class AiWeeklySlotIn(BaseModel):
  weekday: int = Field(..., ge=0, le=6, description="0=Mon ... 6=Sun")
  start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM")
  end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM")


class AiPlanGenerateIn(BaseModel):
    height_cm: float
    weight_kg: float
    age: int
    goal_type: Optional[str] = None
    target_distance_m: Optional[int] = None
    target_weight_kg: Optional[float] = None
    fitness_level: Optional[str] = None
    weekly_slots: List[AiWeeklySlotIn]

class AiPlanActivityIn(BaseModel):
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM")
    duration_minutes: int
    distance_km: float
    activity: str
    description: Optional[str] = None


class AiPlanDayIn(BaseModel):
    weekday: int = Field(..., ge=0, le=6, description="0-6")
    activities: List[AiPlanActivityIn]


class AiPlanApplyIn(BaseModel):
    weekly_template: List[AiPlanDayIn]
    start_date: Optional[str] = Field(
        None, description="Optional start date YYYY-MM-DD; default is tomorrow"
    )
    days: Optional[int] = Field(
        None, gt=0, description="How many days to apply; default 30"
    )


class CoachBindRunnerIn(BaseModel):
    runner_code: int = Field(..., ge=1, le=10000)


class BoundRunnerOut(BaseModel):
    id: str
    name: str
    runner_code: int


# ---------- Coach notes models ----------

class CoachNoteCreateIn(BaseModel):
    content: str


class CoachNoteOut(BaseModel):
    id: str
    runner_id: str
    coach_id: str
    coach_name: Optional[str] = None
    content: str
    created_at: str


# ---------- Users / Auth / Dashboard ----------

# Old endpoint: automatically create user (mostly unused by frontend now, but kept for compatibility)
@app.post("/api/resolve_user", response_model=UserOut)
def api_resolve_user(body: UserResolveIn):
    u = services.resolve_or_create_user(body.username)
    return UserOut(
        id=u["id"],
        name=u["username"],
        role=u.get("role", "runner"),
        runner_code=u.get("runner_code"),
    )


@app.post("/api/auth/register", response_model=UserOut)
def api_register_user(body: RegisterIn):
    try:
        user = services.register_user(body.username, body.role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return UserOut(
        id=user["id"],
        name=user["username"],
        role=user["role"],
        runner_code=user.get("runner_code"),
    )


@app.post("/api/auth/login", response_model=UserOut)
def api_login_user(body: LoginIn):
    try:
        user = services.login_user(body.username)
    except ValueError as e:
        # User not found -> 404, let frontend show "please register first"
        raise HTTPException(status_code=404, detail=str(e))

    # Ensure roles match (prevent runner logging in as coach, and vice versa)
    db_role = user.get("role", "runner")
    if db_role != body.role:
        raise HTTPException(status_code=400, detail="role mismatch")

    return UserOut(
        id=user["id"],
        name=user["username"],
        role=db_role,
        runner_code=user.get("runner_code"),
    )


@app.get("/api/dashboard/{user_id}")
def api_get_dashboard(user_id: str, days: int, weeks: int):
    try:
        return services.get_dashboard(user_id, days, weeks)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------- Coach <-> Runner binding ----------


@app.post("/api/coach/{coach_id}/bind_runner", response_model=BoundRunnerOut)
def api_coach_bind_runner(coach_id: str, body: CoachBindRunnerIn):
    try:
        res = services.bind_runner_to_coach(coach_id, body.runner_code)
        # services returns: {"coach_id": ..., "runner": {...}}
        return BoundRunnerOut(**res["runner"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/coach/{coach_id}/runners", response_model=List[BoundRunnerOut])
def api_coach_list_runners(coach_id: str):
    try:
        runners = services.list_coach_runners(coach_id)
        # services returns: [{"id", "name", "runner_code"}, ...]
        return [BoundRunnerOut(**r) for r in runners]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------- Coach notes APIs ----------


@app.post(
    "/api/coach/{coach_id}/runner/{runner_id}/notes",
    response_model=CoachNoteOut,
)
def api_create_coach_note(
    coach_id: str,
    runner_id: str,
    body: CoachNoteCreateIn,
):
    """
    Coach writes a note for a runner.
    """
    try:
        note = services.create_coach_note_for_runner(
            coach_id=coach_id,
            runner_id=runner_id,
            content=body.content,
        )
        return note
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/runner/{runner_id}/notes", response_model=List[CoachNoteOut])
def api_list_runner_notes(runner_id: str):
    """
    Query all coach notes for a runner.
    """
    try:
        return services.list_notes_for_runner(runner_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------- RunRecord & basic run actions ----------


@app.get("/api/run_record/today/{user_id}")
def api_get_today_run_record(user_id: str):
    try:
        return services.get_today_run_record(user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/run/start/{user_id}")
def api_start_run(user_id: str, payload: StartRunIn):
    try:
        return services.start_run(user_id, note=payload.note)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/run/pause/{user_id}")
def api_pause_run(user_id: str):
    try:
        return services.pause_run(user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/run/resume/{user_id}")
def api_resume_run(user_id: str):
    try:
        return services.resume_run(user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/run/stop/{user_id}")
def api_stop_run(user_id: str, payload: StopRunIn):
    try:
        return services.stop_run(
            user_id,
            total_distance_km=payload.total_distance_km,
            elapsed_seconds=payload.elapsed_seconds,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------- User settings ----------


@app.get("/api/user_settings/{user_id}")
def api_get_user_settings(user_id: str):
    """
    GET /api/user_settings/{user_id}
    """
    return services.get_user_settings(user_id)


@app.post("/api/user_settings/{user_id}/calories_per_hour")
def api_set_calories_per_hour(user_id: str, payload: CaloriesPerHourIn):
    """
    POST /api/user_settings/{user_id}/calories_per_hour
    body: { "calories_per_hour": 600 }
    """
    try:
        return services.set_calories_per_hour(user_id, payload.calories_per_hour)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------- Running plan calendar ----------


@app.get("/api/running_plan/calendar/{user_id}")
def api_get_running_plan_calendar(user_id: str, year: int, month: int):
    """
    GET /api/running_plan/calendar/{user_id}?year=2025&month=11
    """
    try:
        return services.get_running_plan_calendar(user_id, year, month)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/running_plan/day/{user_id}")
def api_create_day_plan(user_id: str, payload: DayPlanCreateIn):
    """
    POST /api/running_plan/day/{user_id}
    body: DayPlanCreateIn
    """
    try:
        return services.create_day_plan(
            user_id=user_id,
            date_str=payload.date,
            start_time=payload.start_time,
            duration_minutes=payload.duration_minutes,
            distance_km=payload.distance_km,
            activity=payload.activity,
            description=payload.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/running_plan/day/{user_id}/{plan_id}")
def api_delete_day_plan(user_id: str, plan_id: str):
    """
    DELETE /api/running_plan/day/{user_id}/{plan_id}
    """
    try:
        services.delete_day_plan(user_id, plan_id)
        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/running_plan/ai/preview/{user_id}")
def api_preview_ai_weekly_plan(user_id: str, payload: AiPlanGenerateIn):
    try:
        return services.build_test_weekly_ai_plan(
            user_id=user_id,
            payload=payload.dict(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/running_plan/ai/apply/{user_id}")
def api_apply_ai_weekly_plan(user_id: str, payload: AiPlanApplyIn):
    try:
        return services.apply_test_weekly_ai_plan(
            user_id=user_id,
            payload=payload.dict(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/coach/{coach_id}/bind_runner", response_model=BoundRunnerOut)
def api_coach_bind_runner(coach_id: str, body: CoachBindRunnerIn):
    try:
        res = services.bind_runner_to_coach(coach_id, body.runner_code)
        # services returns: {"coach_id": ..., "runner": {...}}
        return BoundRunnerOut(**res["runner"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/health")
def api_health():
    return {"status": "ok"}
