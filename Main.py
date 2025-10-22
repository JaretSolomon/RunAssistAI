from datetime import datetime

class User:
    def login(self, username, password):
        pass

    def logout(self):
        pass

    def view_history(self):
        pass

    def show_role(self):
        pass

class runnerSession:

    def __init__(self, sessionId):
        self.sessionId = sessionId
        self.startTime = None
        self.endTime = None
        self.totalDistance = 0
        self.timeSpan = endTime - startTime

    def addMetric(self, metric):
        print(f"Adding metric to runner session {self.sessionId}")



    def startRun(self):
        print(f"Runner session {self.sessionId} started")

    def endRun(self):
        print(f"Runner session {self.sessionId} ended")

class Runner(User):
    def __init__(self, name):
        self.name = name
        self.currentGoal = "No goal set"

    def login(self, username, password):
        print(f"{self.name} (Runner) logged in as {username}")

    def logout(self):
        print(f"{self.name} logged out.")

    def viewHistory(self):
        print(f"Showing run history for {self.name}")

    def showRole(self):
        print(f"I am a Runner, name: {self.name}")

    def startRun(self):
        print(f"{self.name} started a new run")
        startTime = datetime.now()
        if self.currentSession is None:
            self.currentSession = runnerSession(startTime)
        else:
            self.currentSession.startRun()

    def endRun(self):
        print(f"{self.name} ended a run")
        endTime = datetime.now()
        if self.currentSession is not None:
            self.currentSession.endRun(endTime)
        self.currentSession = None

