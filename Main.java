import java.util.List;

//User.java
public interface User {
    void login(String username, String password);
    void logout();
    void viewHistory();  
    void showRole();
}

//Runner.java
public class Runner implements User {
    private final String name;
    private String currentGoal = "No goal set";

    public Runner(String name) { this.name = name; }

    @Override
    public void login(String username, String password) {
        System.out.println(name + " (Runner) logged in as " + username);
    }

    @Override
    public void logout() {
        System.out.println(name + " logged out.");
    }

    @Override
    public void viewHistory() {
        System.out.println("Showing run history for " + name);
    }

    @Override
    public void showRole() {
        System.out.println("I am a Runner, name: " + name);
    }

    public RunnerSession startRun(String sessionId) {
        System.out.println(name + " started a new run session: " + sessionId);
        return new RunnerSession(sessionId);
    }

    public void setGoal(Goal goal) {
        this.currentGoal = goal.description();
        System.out.println(name + " set goal: " + currentGoal);
    }
}

//Coach.java
public class Coach implements User {
    private final String name;

    public Coach(String name) { this.name = name; }

    @Override
    public void login(String username, String password) {
        System.out.println(name + " (Coach) logged in as " + username);
    }

    @Override
    public void logout() {
        System.out.println(name + " logged out.");
    }

    @Override
    public void viewHistory() {
        System.out.println("Showing coach activity for " + name);
    }

    @Override
    public void showRole() {
        System.out.println("I am a Coach, name: " + name);
    }

    public void viewAthleteDashboard(String runnerName) {
        System.out.println(name + " is viewing dashboard of " + runnerName);
    }

    public void assignWorkout(String runnerName, Workout workout) {
        System.out.println(name + " assigned '" + workout.name() + "' to " + runnerName);
    }
}

//FitnessFactory.java
public class FitnessFactory {

    private FitnessFactory() {} 

    public static User createUser(String role, String name) {
        switch (role.toLowerCase()) {
            case "runner": return new Runner(name);
            case "coach":  return new Coach(name);
        }
    }
}

public class Main {
    public static void main(String[] args) {
        User r = FitnessFactory.createUser("runner", "name");
        User c = FitnessFactory.createUser("coach", "name");
        r.login("username", "XXXX");
        r.showRole();
        r.viewHistory();

        r.logout();

        c.login("username", "XXXX");
        c.showRole();
        c.viewHistory();
        c.logout();
    }
}
