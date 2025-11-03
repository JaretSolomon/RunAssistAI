#Import classes we're testing from the Main.py script
from Main import Runner,  RunnerSessionFactory, runnerSession, RunMetric

#Used unittest to have a premade testing framework
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta


#Test the runner class (create a user and fill in details)
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
#builtins.print replaces the real print statement with a mock output (like the mocks we discussed in class)
#then mock_print.assert_called_once_with checks that the output matches the expected output
#See the documentation for unittest mock here: https://docs.python.org/3/library/unittest.mock.html#patch-builtins

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
        #Assert that the sesion has a start time
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

    
    def test_reset(self):
        #Create data to clear
        session = runnerSession("S6")
        session.startTime = datetime.now()
        session.endTime = datetime.now()
        session.totalDistance = 15.0
        session.metrics.append(RunMetric(1.0,100))
        #Actually reset/clear the session
        session.reset()

        #Now test that all these categories are empty
        self.assertIsNone(session.startTime)
        self.assertIsNone(session.endTime)
        self.assertTrue(session.totalDistance == 0.0)



if __name__ == '__main__':
    unittest.main()
