import sockpile.database as database

def menu():
    print("******************************************************")
    print("Welcome to Socks (🧦) C.R.U.D interface! What would you like to do? ")
    print("1. Create a new Pay Period")
    print("2. Create an Invalid Date")
    print("3. Read Pay Period Start & End Dates")
    print("4. Read Invalid Dates")
    print("5. Update a Pay Period")
    print("6. Update an Invalid Date")
    print("7. Delete a Pay Period")
    print("8. Delete Invalid Date")
    print("m. View Menu")
    print("q. Quit")
    print("******************************************************")

def main():
    db = database.Database()

    menu()
    running = True

    while running:

        choice = input("Please type your selection: ").lower()

        match choice:
            case "1":
                db.create_pay_period()
            case "2":
                db.create_invalid_date()
            case "3":
                db.read_pay_period_start_end()
            case "4":
                db.read_invalid_dates()
            case "5":
                db.update_pay_period()
            case "6":
                db.update_invalid_date()
            case "7":
                db.delete_pay_period()
            case "8":
                db.delete_invalid_date()
            case "m":
                menu()
            case "q":
                running = False
            case _:
                print(f"Choice {choice} is invalid, please try again.")

    print("\nThank you for using the (🧦) Socks (🧦) database!")

if __name__ == '__main__':
    main()