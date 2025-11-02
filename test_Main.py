from Main import Runner,  RunnerSessionFactory, runnerSession, RunMetric
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta


class TestRunner(unittest.TestCase):
# Test 1: Initialize a user
    def test_initialization(self):
        runner = Runner("Alice")
        self.assertEqual(runner.name, "Alice")
        self.assertEqual(runner.currentGoal, "No goal set")
        self.assertIsNone(runner.currentSession)
        self.assertIsInstance(runner.session_factory, RunnerSessionFactory)
        self.assertIsInstance(runner.sessionHistory, list)

#Test 2: Test login
    @patch("builtins.print")
    def test_login(self, mock_print):
        runner = Runner("Bob")
        runner.login("bob123", "password")
        mock_print.assert_called_once_with("Bob (Runner) logged in as bob123")

#Test 3: Test Logout
    @patch("builtins.print")
    def test_logout(self, mock_print):
        runner = Runner("Bob")
        runner.logout()
        mock_print.assert_called_once_with("Bob logged out.")


class TestRunnerSession(unittest.TestCase):
#Test 4: Test that you can begin a session
    @patch("builtins.print")
    def test_begin(self, mock_print):
        session = runnerSession("S1")
        session.begin()
        self.assertIsNotNone(session.startTime)
        mock_print.assert_called_once()
        self.assertIn("Runner session S1 started at", mock_print.call_args[0][0])

#Test 5: Test that you can't start two sessions at once
    def test_begin_twice_raises_error(self):
        session = runnerSession("S2")
        session.begin()
        with self.assertRaises(RuntimeError):
            session.begin()

#Test 6: Assert you can log statistics about the run
    def test_record_metric(self):
            session = runnerSession("S3")
            metric = RunMetric(distance=2.5, duration=300)  # 5 minutes
            total_distance, total_duration = session.record_metric(metric)

            #Testing that the total distance metric recorded is 2.5
            self.assertEqual(total_distance, 2.5)

            #Test that a different number input is logged as incorrect/False
            self.assertFalse(total_distance == 3.5)

            #Test 300s is correctly recorded
            self.assertEqual(total_duration, timedelta(seconds=300))

            #Make sure there is only one session being recorded!
            self.assertEqual(len(session.metrics), 1)


    @patch("builtins.print")
    def test_finish(self, mock_print):
        session = runnerSession("S5")
        m = RunMetric(distance=1.0, duration=60)
        session.record_metric(m)
        summary = session.finish()
        #Test 7: Assert the sessionID is correct
        self.assertEqual(summary["session_id"], "S5")

        #Test 8: Make sure it can identify an incorrect SessionID
        self.assertFalse(summary["session_id"] == "S6")

        #Test 9: Assert the total distance is recorded correctly
        self.assertEqual(summary["total_distance"], 1.0)

        #Test 10: Assert an incorrect total distance can be identified
        self.assertFalse(summary["total_distance"] == '100.0')

        #Test 11: Assert total duration is recorded correctly
        self.assertEqual(summary["total_duration"], timedelta(seconds=60))

    
if __name__ == '__main__':
    unittest.main()
