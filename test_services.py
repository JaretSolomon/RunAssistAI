import os

# 确保在 import services 之前就有一个假的 OPENAI_API_KEY，
# 避免 services 在模块加载时抛 RuntimeError
os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest

from runtrack.repository import Repo
from runtrack import services


@pytest.fixture(autouse=True)
def in_memory_repo(monkeypatch):
    mem_repo = Repo(db_path=":memory:")
    monkeypatch.setattr(services, "repo", mem_repo)
    yield


@pytest.fixture
def runner_user():
    password = "runner-pass"
    user = services.register_user("runner1", password, "runner")
    return user, password


@pytest.fixture
def coach_user():
    password = "coach-pass"
    user = services.register_user("coach1", password, "coach")
    return user, password


def test_register_runner_success():
    user, _ = services.register_user("alice", "abcd1234", "runner"), "abcd1234"
    assert user["name"] == "alice"
    assert user["role"] == "runner"
    assert isinstance(user["runner_code"], int)


def test_register_user_empty_username_raises():
    with pytest.raises(ValueError):
        services.register_user("   ", "abcd1234", "runner")


def test_register_user_short_password_raises():
    with pytest.raises(ValueError):
        services.register_user("bob", "123", "runner")


def test_login_user_success(runner_user):
    user, password = runner_user
    logged_in = services.login_user(user["username"], password, "runner")
    assert logged_in["id"] == user["id"]
    assert logged_in["username"] == user["username"]
    assert logged_in["role"] == "runner"


def test_login_user_wrong_password_raises(runner_user):
    user, _ = runner_user
    with pytest.raises(ValueError):
        services.login_user(user["username"], "wrong-password", "runner")


def test_start_and_stop_run(runner_user):
    user, _ = runner_user

    session = services.start_run(user["id"], note="easy run")
    assert session["user_id"] == user["id"]
    assert session["ended_at"] is None

    services.add_metric(
        user_id=user["id"],
        distance_km=5.0,
        duration_seconds=1800,
        start_time="2025-01-01T10:00:00Z",
        end_time="2025-01-01T10:30:00Z",
    )


    finished = services.stop_run(
        user_id=user["id"],
        total_distance_km=5.0,
        elapsed_seconds=1800,
    )

    assert finished["ended_at"] is not None
    assert finished["total_distance_km"] == 5.0
    assert finished["total_duration_seconds"] == 1800
    assert services.repo.get_active_session(user["id"]) is None

def test_create_and_list_day_plan(runner_user):
    user, _ = runner_user
    date_str = "2025-01-10"

    created = services.create_day_plan(
        user_id=user["id"],
        date_str=date_str,
        start_time="07:30",
        duration_minutes=40,
        distance_km=6.0,
        activity="easy",
        description="morning run",
    )

    assert created["plan_date"] == date_str
    assert created["distance_km"] == 6.0

    plans = services.list_day_plans_for_date(user["id"], date_str)
    assert len(plans) == 1
    p = plans[0]
    assert p["plan_date"] == date_str
    assert p["duration_minutes"] == 40
    assert p["activity"] == "easy"

def test_create_day_plan_invalid_time_raises(runner_user):
    user, _ = runner_user
    with pytest.raises(ValueError):
        services.create_day_plan(
            user_id=user["id"],
            date_str="2025-01-10",
            start_time="7:30",  # 非 HH:MM 格式
            duration_minutes=30,
            distance_km=5.0,
        )


def test_bind_runner_to_coach_and_list(coach_user, runner_user):
    coach, _ = coach_user
    runner, _ = runner_user

    result = services.bind_runner_to_coach(
        coach_id=coach["id"],
        runner_code=runner["runner_code"],
    )
    assert result["coach_id"] == coach["id"]
    assert result["runner"]["id"] == runner["id"]

    runners = services.list_coach_runners(coach["id"])
    assert len(runners) == 1
    r = runners[0]
    assert r["id"] == runner["id"]
    assert r["runner_code"] == runner["runner_code"]


def test_get_today_run_record_no_sessions(runner_user):
    user, _ = runner_user
    record = services.get_today_run_record(user["id"])

    assert record["settings"]["user_id"] == user["id"]
    today_summary = record["today_summary"]
    assert today_summary["total_distance_km"] == 0
    assert today_summary["total_duration_seconds"] == 0
    assert today_summary["total_calories"] == 0
    assert record["today_goal_seconds"] == 60 * 60
