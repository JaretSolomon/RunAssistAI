



def Get_Running_Plan():
    run_length  = input("Enter what length you are training for: 5k, 10k, half-marathon, marathon:\n")

    if run_length == "5k":
        print("Check out these 5k training plans!:\n")
        print("Nike: https://www.nike.com/running/5k-training-plan\n")
        print("Runner's World: https://www.runnersworld.com/beginner/a40267826/couch-to-5k-runners-program/\n")
    else:

        if run_length == "10k":
            print("Check out these 10k training plans!:\n")
            print("Boston Athletic Association: https://www.baa.org/races/baa-10k/train\n")
            print("REI: https://www.rei.com/learn/expert-advice/road-running-10k-training-plan.html\n")
        else:

            if run_length == "half-marathon":
                print("Check out these half-marathon training plans!:\n")
                print("Saint Jude: https://www.stjude.org/get-involved/fitness-fundraisers/memphis-marathon/event-information/training/half-marathon-training-schedule-and-tips.html\n")
                print("Boston Athletic Association: https://www.baa.org/races/baa-half-marathon/train\n")
            else:
                
                if run_length == "marathon":
                    print("Check out these marathon training plans!:\n")
                    print("Hal Higdon: https://www.halhigdon.com/training/marathon-training/\n")
                    print("Runner's World: https://www.runnersworld.com/training/a19492479/marathon-training-plans/n\n")

                return
    print("What else can I help you with?\n")
    main()


def Enter_Stats():
    print("Welcome, please enter your statistics!")
    run_distance = input("How far did you run?: ")
    run_time = input("How much time did you spend running?: ")


def main():
    #print("Hello, welcome to RunAssist! How can I help you? Please enter the correct number below:\n")
    user_choice = input("1: Get a running plan\n2: Enter stats from run\n")

    if user_choice == "1":
        Get_Running_Plan()

    if user_choice == "2":
        Enter_Stats()
    return

print("Hello, welcome to RunAssist! How can I help you? Please enter the correct number below:\n")
main()
