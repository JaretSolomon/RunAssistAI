import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Main import Coach, RunnerSessionFactory, User, UserFactory, runnerSession


class DummySessionFactory:
    def __init__(self):
        
        self.created = []

    def create_session(self):
        session = object()
        self.created.append(session)
        return session


def test_factory_creates_coach_instance():
    factory = UserFactory()
    user = factory.create_user("coach", "Jess")

    assert isinstance(user, Coach)


def test_factory_sets_coach_name():
    factory = UserFactory()
    user = factory.create_user("coach", "Jess")

    assert user.name == "Jess"


def test_factory_role_case_insensitive_for_coach():
    factory = UserFactory()
    user = factory.create_user("COACH", "Pat")

    assert isinstance(user, Coach)


def test_factory_returns_distinct_coach_instances():
    factory = UserFactory()

    first = factory.create_user("coach", "Jess")
    second = factory.create_user("coach", "Jess")

    assert first is not second


def test_factory_provides_default_session_factory_for_coach():
    factory = UserFactory()
    user = factory.create_user("coach", "Jess")

    assert isinstance(user.session_factory, RunnerSessionFactory)


def test_factory_assigns_injected_session_factory_to_coach():
    dummy_factory = DummySessionFactory()
    factory = UserFactory(session_factory=dummy_factory)

    user = factory.create_user("coach", "Jess")

    assert user.session_factory is dummy_factory


def test_factory_coach_session_factory_creates_runner_session():
    factory = UserFactory()
    user = factory.create_user("coach", "Jess")

    session = user.session_factory.create_session()

    assert isinstance(session, runnerSession)


def test_factory_coach_initial_session_history_empty():
    factory = UserFactory()
    user = factory.create_user("coach", "Jess")

    assert user.sessionHistory == []


def test_factory_coach_current_session_starts_none():
    factory = UserFactory()
    user = factory.create_user("coach", "Jess")

    assert user.currentSession is None


def test_factory_coach_is_user_subclass():
    factory = UserFactory()
    user = factory.create_user("coach", "Jess")

    assert isinstance(user, User)
