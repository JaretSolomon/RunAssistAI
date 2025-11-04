import sys
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Main import Coach, CoachSessionFactory, User, UserFactory, coachSession  # noqa: E402


class DummyCoachSessionFactory:
    def create_session(self):
        return object()


class TestCoachFactory(unittest.TestCase):
    def test_factory_creates_coach_instance(self):
        factory = UserFactory()
        user = factory.create_user("coach", "Jess")

        self.assertIsInstance(user, Coach)

    def test_factory_sets_coach_name(self):
        factory = UserFactory()
        user = factory.create_user("coach", "Jess")

        self.assertEqual(user.name, "Jess")

    def test_factory_role_case_insensitive_for_coach(self):
        factory = UserFactory()
        user = factory.create_user("COACH", "Pat")

        self.assertIsInstance(user, Coach)

    def test_factory_returns_distinct_coach_instances(self):
        factory = UserFactory()
        first = factory.create_user("coach", "Jess")
        second = factory.create_user("coach", "Jess")

        self.assertIsNot(first, second)

    def test_factory_provides_default_session_factory_for_coach(self):
        factory = UserFactory()
        user = factory.create_user("coach", "Jess")

        self.assertIsInstance(user.session_factory, CoachSessionFactory)

    def test_factory_assigns_injected_session_factory_to_coach(self):
        dummy_factory = DummyCoachSessionFactory()
        factory = UserFactory(coach_session_factory=dummy_factory)

        user = factory.create_user("coach", "Jess")

        self.assertIs(user.session_factory, dummy_factory)

    def test_coach_session_factory_creates_coach_session(self):
        session_factory = CoachSessionFactory()
        session = session_factory.create_session()

        self.assertIsInstance(session, coachSession)

    def test_factory_coach_initial_session_history_empty(self):
        factory = UserFactory()
        user = factory.create_user("coach", "Jess")

        self.assertEqual(user.sessionHistory, [])

    def test_factory_coach_current_session_starts_none(self):
        factory = UserFactory()
        user = factory.create_user("coach", "Jess")

        self.assertIsNone(user.currentSession)

    def test_factory_coach_is_user_subclass(self):
        factory = UserFactory()
        user = factory.create_user("coach", "Jess")

        self.assertIsInstance(user, User)


if __name__ == "__main__":
    unittest.main()
