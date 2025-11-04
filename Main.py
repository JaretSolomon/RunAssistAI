import uuid
from datetime import datetime, timedelta

class User:
    def login(self, username, password):
        pass

    def logout(self):
        pass

    def view_history(self):
        pass

    def show_role(self):
        pass

class RunMetric:
    def __init__(self, distance, duration=None, start_time=None, end_time=None):
        self.distance = float(distance)
        self.start_time = start_time
        self.end_time = end_time
        if duration is None and start_time is not None and end_time is not None:
            duration = end_time - start_time
        if isinstance(duration, (int, float)):
            duration = timedelta(seconds=duration)
        self.duration = duration if duration is not None else timedelta() 

    def __repr__(self):  # This is a magic method that is used to represent the object as a string
        return (
            f"RunMetric(distance={self.distance}, duration={self.duration}, "
            f"start_time={self.start_time}, end_time={self.end_time})"
        )

class runnerSession:
    """Encapsulates a single run session for a runner."""

    def __init__(self, sessionId):
        self.sessionId = sessionId
        self.startTime = None
        self.endTime = None
        self.totalDistance = 0.0
        self.totalDuration = timedelta()
        self.metrics = []

    def begin(self):
        if self.startTime is not None:
            raise RuntimeError("Session already started")
        self.startTime = datetime.now()
        print(f"Runner session {self.sessionId} started at {self.startTime}")

    def record_metric(self, metric):
        if not isinstance(metric, RunMetric):
            raise TypeError("metric must be an instance of RunMetric")
        if self.startTime is None:
            self.begin()
        self.metrics.append(metric)
        self.totalDistance += metric.distance
        self.totalDuration += metric.duration
        return self.totalDistance, self.totalDuration

    def finish(self):
        if self.startTime is None:
            raise RuntimeError("Session was never started")
        if self.endTime is None:
            self.endTime = datetime.now()
        print(f"Runner session {self.sessionId} ended at {self.endTime}")
        summary = self.summary()
        self.reset()
        return summary

    def summary(self):
        effective_duration = self.totalDuration
        if effective_duration == timedelta() and self.startTime and self.endTime:
            effective_duration = self.endTime - self.startTime
        return {
            "session_id": self.sessionId,
            "started_at": self.startTime,
            "ended_at": self.endTime,
            "total_distance": self.totalDistance,
            "total_duration": effective_duration,
        } # This is a dictionary that is used to return the summary of the session in JSON

    def reset(self):
        self.startTime = None
        self.endTime = None
        self.totalDistance = 0.0
        self.totalDuration = timedelta()
        self.metrics.clear()

class Runner(User):
    def __init__(self, name, session_factory=None):
        self.name = name
        self.currentGoal = "No goal set"
        self.session_factory = session_factory or RunnerSessionFactory()
        self.currentSession = None
        self.sessionHistory = []

    def login(self, username, password):
        print(f"{self.name} (Runner) logged in as {username}")

    def logout(self):
        print(f"{self.name} logged out.")

    def viewHistory(self):
        print(f"Showing run history for {self.name}")

    def showRole(self):
        print(f"I am a Runner, name: {self.name}")

    def startRun(self):
        if self.currentSession is not None:
            raise RuntimeError("A session is already in progress")
        self.currentSession = self.session_factory.create_session()
        self.currentSession.begin()
        print(f"{self.name} started a new run session {self.currentSession.sessionId}")
        return self.currentSession

    def record_session_metric(self, distance, duration=None, start_time=None, end_time=None):
        if self.currentSession is None:
            raise RuntimeError("No active session to record metrics")
        metric = RunMetric(distance, duration=duration, start_time=start_time, end_time=end_time) # This is a class that is used to record the metric of the session
        return self.currentSession.record_metric(metric) # This is a method that is used to record the metric of the session

    def endRun(self):
        if self.currentSession is None:
            raise RuntimeError("No active session to end")
        summary = self.currentSession.finish()
        self.sessionHistory.append(summary)
        print(
            f"{self.name} ended session {summary['session_id']} with distance {summary['total_distance']} "
            f"and duration {summary['total_duration']}"
        )
        self.currentSession = None
        return summary

    def getSessionHistory(self):
        return list(self.sessionHistory)
class coachSession:
    def __init__(self, sessionId):
        self.sessionId = sessionId
        self.startTime = None
        self.endTime = None
        self.totalDistance = 0.0
        self.totalDuration = timedelta()
        self.metrics = []

    def begin(self):
        if self.startTime is not None:
            raise RuntimeError("Session already started")
        self.startTime = datetime.now()
        print(f"Coach session {self.sessionId} started at {self.startTime}")

    def record_metric(self, metric):
        if not isinstance(metric, RunMetric):
            raise TypeError("metric must be an instance of RunMetric")
        if self.startTime is None:
            self.begin()
        self.metrics.append(metric)
        self.totalDistance += metric.distance
        self.totalDuration += metric.duration
        return self.totalDistance, self.totalDuration

    def finish(self):
        if self.startTime is None:
            raise RuntimeError("Session was never started")
        if self.endTime is None:
            self.endTime = datetime.now()
        print(f"Coach session {self.sessionId} ended at {self.endTime}")
        summary = self.summary()
        self.reset()
        return summary

    def summary(self):
        effective_duration = self.totalDuration
        if effective_duration == timedelta() and self.startTime and self.endTime:
            effective_duration = self.endTime - self.startTime
        return {
            "session_id": self.sessionId,
            "started_at": self.startTime,
            "ended_at": self.endTime,
            "total_distance": self.totalDistance,
            "total_duration": effective_duration,
        } # This is a dictionary that is used to return the summary of the session in JSON

    def reset(self):
        self.startTime = None
        self.endTime = None
        self.totalDistance = 0.0
        self.totalDuration = timedelta()
        self.metrics.clear()

class Coach(User):
    def __init__(self, name, session_factory=None):
        self.name = name
        self.session_factory = session_factory or CoachSessionFactory()
        self.currentSession = None
        self.sessionHistory = []

    def login(self, username, password):
        print(f"{self.name} (Coach) logged in as {username}")

    def logout(self):
        print(f"{self.name} logged out.")

    def viewHistory(self):
        print(f"Showing coach activity for {self.name}")

    def showRole(self):
        print(f"I am a Coach, name: {self.name}")

    def viewAthleteDashboard(self, runnerName):
        print(f"{self.name} is viewing dashboard of {runnerName}")
        #need to implement the logic to view the dashboard of the runner

    def assignWorkout(self, runnerName, workout):
        print(f"{self.name} assigned '{workout.name()}' to {runnerName}")
        #need to implement the logic to assign the workout to the runner and reflect on the dashboard of the runner.

class RunnerSessionFactory:
    def create_session(self):
        session_id = uuid.uuid4().hex
        return runnerSession(session_id)

class CoachSessionFactory:
    def create_session(self):
        session_id = uuid.uuid4().hex
        return coachSession(session_id)

class UserFactory:
    def __init__(self, session_factory=None, coach_session_factory=None):
        self.runner_session_factory = session_factory or RunnerSessionFactory()
        self.coach_session_factory = (
            coach_session_factory or session_factory or CoachSessionFactory()
        )

    def create_user(self, role, name):
        role = role.lower()
        if role == "runner":
            return Runner(name, session_factory=self.runner_session_factory)
        if role == "coach":
            return Coach(name, session_factory=self.coach_session_factory)

        raise ValueError(f"Unsupported role: {role}")
