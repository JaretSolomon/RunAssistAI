



def Get_Running_Plan():
    run_length  = input("Enter what length you are training for: 5k, 10k, half-marathon, marathon, other")

    if run_length == "5k":
        print("Check out this 5k training plan from Nike!")
    else:
        return


def Enter_Stats():
    print("Welcome, please enter your statistics!")
    run_distance = input("How far did you run?: ")
    run_time = input("How much time did you spend running?: ")


def main():
    print("Hello, welcome to RunAssist! How can I help you? Please enter the correct number below:\n")
    user_choice = input("1: Get a running plan\n2: Enter stats from run\n")

    if user_choice == "1":
        Get_Running_Plan()

    if user_choice == "2":
        Enter_Stats()
    return

main()
