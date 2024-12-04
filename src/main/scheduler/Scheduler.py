from model.Vaccine import Vaccine
from model.Caregiver import Caregiver
from model.Patient import Patient
from util.Util import Util
from db.ConnectionManager import ConnectionManager
import pymssql
import datetime


'''
objects to keep track of the currently logged-in user
Note: it is always true that at most one of currentCaregiver and currentPatient is not null
        since only one user can be logged-in at a time
'''
current_patient = None

current_caregiver = None


def create_patient(tokens):
    
    # Part 1 
    global current_patient, current_caregiver

    username = tokens[1]
    password = tokens[2]

    if current_patient is not None:
        print("User already logged in, try again")
        return

    if current_caregiver is not None:
        print("User already logged in, try again")
        return

    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor(as_dict=True)
    try:
        cursor.execute("SELECT * FROM Patients WHERE Username = %s", username)
        if cursor.fetchone():
            print("Username taken, try again")
            return
    except pymssql.Error as e:
        print("Create patient failed")
        print("Db-Error:", e)
        return
    finally:
        cm.close_connection()

  
    salt = Util.generate_salt()
    hash = Util.generate_hash(password, salt)

    patient = Patient(username=username, salt=salt, hash=hash)
    try:
        patient.save_to_db()
        print(f"Created user {username}")
    except Exception as e:
        print("Create patient failed")
        print(e)


def create_caregiver(tokens):
    # create_caregiver <username> <password>
    # check 1: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Failed to create user.")
        return

    username = tokens[1]
    password = tokens[2]
    # check 2: check if the username has been taken already
    if username_exists_caregiver(username):
        print("Username taken, try again!")
        return

    salt = Util.generate_salt()
    hash = Util.generate_hash(password, salt)

    # create the caregiver
    caregiver = Caregiver(username, salt=salt, hash=hash)

    # save to caregiver information to our database
    try:
        caregiver.save_to_db()
    except pymssql.Error as e:
        print("Failed to create user.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Failed to create user.")
        print(e)
        return
    print("Created user ", username)


def username_exists_caregiver(username):
    cm = ConnectionManager()
    conn = cm.create_connection()

    select_username = "SELECT * FROM Caregivers WHERE Username = %s"
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(select_username, username)
        #  returns false if the cursor is not before the first record or if there are no rows in the ResultSet.
        for row in cursor:
            return row['Username'] is not None
    except pymssql.Error as e:
        print("Error occurred when checking username")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when checking username")
        print("Error:", e)
    finally:
        cm.close_connection()
    return False


def login_patient(tokens):
    ## Part 1 
    global current_patient, current_caregiver


    if len(tokens) != 3:
        print("Login patient failed")
        return

    username = tokens[1]
    password = tokens[2]

    if current_patient is not None: 
        print("User already logged in, try again")
        return 
    
    if current_caregiver is not None: 
        print("User already logged in, try again")

    try:
        patient = Patient(username=username, password=password).get()
        if patient is None:
            print("Login patient failed")
        else:
            current_patient = patient
            print(f"Logged in as {username}")
    except Exception as e:
        print("Login patient failed")
        print(e)


def login_caregiver(tokens):
    # login_caregiver <username> <password>
    # check 1: if someone's already logged-in, they need to log out first
    global current_caregiver
    if current_caregiver is not None or current_patient is not None:
        print("User already logged in.")
        return

    # check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Login failed.")
        return

    username = tokens[1]
    password = tokens[2]

    caregiver = None
    try:
        caregiver = Caregiver(username, password=password).get()
    except pymssql.Error as e:
        print("Login failed.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Login failed.")
        print("Error:", e)
        return

    # check if the login was successful
    if caregiver is None:
        print("Login failed.")
    else:
        print("Logged in as: " + username)
        current_caregiver = caregiver



def search_caregiver_schedule(tokens):
    # Part 2
    global current_caregiver, current_patient

    user_log_in = False
    if current_caregiver is not None or current_patient is not None:
         user_log_in = True

    if not  user_log_in:
        print("Please login first")
        return

    if len(tokens) != 2:
        print("Please try again")
        return

    date = tokens[1]

    formatted_date = None
    try:
        date_parts = date.split("-")
        if len(date_parts) == 3:
            month = int(date_parts[0])
            day = int(date_parts[1])
            year = int(date_parts[2])
            formatted_date = datetime.datetime(year, month, day)
        else:
            raise ValueError("Date format incorrect")
    except (ValueError, IndexError):
        print("Please try again")
        return

    cm = ConnectionManager()
    conn = cm.create_connection()

    try:
        cursor = conn.cursor(as_dict=True)
        caregiver_query = """
            SELECT Username 
            FROM Availabilities 
            WHERE Time = %s
            ORDER BY Username;
        """
        cursor.execute(caregiver_query, formatted_date)

        caregivers = []
        for row in cursor:
            caregivers.append(row['Username'])

        vaccine_query = """
            SELECT Name, Doses 
            FROM Vaccines
            WHERE Doses > 0;
        """
        cursor.execute(vaccine_query)

        vaccines = []
        for row in cursor:
            vaccine_name = row['Name']
            doses = row['Doses']
            vaccines.append((vaccine_name, doses))

        if len(caregivers) > 0:
            for caregiver in caregivers:
                print(caregiver)
        else:
            print("No caregivers available")

        if len(vaccines) > 0:
            for vaccine in vaccines:
                print(vaccine[0] + " " + str(vaccine[1]))
        else:
            print("No vaccines available")

    except pymssql.Error as db_error:
        print("Please try again")
    except Exception as error:
        print("Please try again")
    finally:
        cm.close_connection()


def reserve(tokens):
    global current_patient, current_caregiver

    #Part 2

    user_log_in = False
    if current_patient is not None:
        user_log_in = True
    elif current_caregiver is not None:
        user_log_in = True

    if not user_log_in:
        print("Please login first")
        return

    if current_patient is None:
        print("Please login as a patient")
        return

    if len(tokens) != 3:
        print("Please try again")
        return

    date = tokens[1]
    vaccine_name = tokens[2]

    formatted_date = None
    try:
        date_parts = date.split("-")
        if len(date_parts) == 3:
            month = int(date_parts[0])
            day = int(date_parts[1])
            year = int(date_parts[2])
            formatted_date = datetime.datetime(year, month, day)
        else:
            raise ValueError("Invalid date format")
    except (ValueError, IndexError):
        print("Please try again")
        return

    cm = ConnectionManager()
    conn = cm.create_connection()

    try:
        cursor = conn.cursor(as_dict=True)

        caregiver_query = """
            SELECT Username 
            FROM Availabilities 
            WHERE Time = %s
            ORDER BY Username;
        """
        cursor.execute(caregiver_query, formatted_date)
        caregiver_row = cursor.fetchone()

        if caregiver_row is None:
            print("No caregiver is available")
            return

        caregiver_username = caregiver_row['Username']

        vaccine_query = """
            SELECT Doses 
            FROM Vaccines 
            WHERE Name = %s;
        """
        cursor.execute(vaccine_query, vaccine_name)
        vaccine_row = cursor.fetchone()

        if vaccine_row is None or vaccine_row['Doses'] <= 0:
            print("Not enough available doses")
            return


        reservation_query = """
            INSERT INTO Reservations (patient_username, caregiver_username, vaccine_name, reservation_date)
            OUTPUT Inserted.reservation_id
            VALUES (%s, %s, %s, %s);
        """
        cursor.execute(reservation_query, (current_patient.username, caregiver_username, vaccine_name, formatted_date))
        reservation_result = cursor.fetchone()

        if reservation_result is not None:
            reservation_id = reservation_result['reservation_id']
        else:
            print("Failed to create a reservation")
            return

        update_vaccine_query = """
            UPDATE Vaccines 
            SET Doses = Doses - 1 
            WHERE Name = %s;
        """
        cursor.execute(update_vaccine_query, vaccine_name)

        delete_availability_query = """
            DELETE FROM Availabilities 
            WHERE Time = %s AND Username = %s;
        """
        cursor.execute(delete_availability_query, (formatted_date, caregiver_username))

        conn.commit()

        print("Appointment ID", reservation_id, ", Caregiver username", caregiver_username)

    except pymssql.Error as db_error:
        print("Please try again")
    except Exception as error:
        print("Please try again")
    finally:
        cm.close_connection()





def upload_availability(tokens):
    #  upload_availability <date>
    #  check 1: check if the current logged-in user is a caregiver
    global current_caregiver
    if current_caregiver is None:
        print("Please login as a caregiver first!")
        return

    # check 2: the length for tokens need to be exactly 2 to include all information (with the operation name)
    if len(tokens) != 2:
        print("Please try again!")
        return

    date = tokens[1]
    # assume input is hyphenated in the format mm-dd-yyyy
    date_tokens = date.split("-")
    month = int(date_tokens[0])
    day = int(date_tokens[1])
    year = int(date_tokens[2])
    try:
        d = datetime.datetime(year, month, day)
        current_caregiver.upload_availability(d)
    except pymssql.Error as e:
        print("Upload Availability Failed")
        print("Db-Error:", e)
        quit()
    except ValueError:
        print("Please enter a valid date!")
        return
    except Exception as e:
        print("Error occurred when uploading availability")
        print("Error:", e)
        return
    print("Availability uploaded!")


def cancel(tokens):
    """
    TODO: Extra Credit
    """
    pass


def add_doses(tokens):
    #  add_doses <vaccine> <number>
    #  check 1: check if the current logged-in user is a caregiver
    global current_caregiver
    if current_caregiver is None:
        print("Please login as a caregiver first!")
        return

    #  check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Please try again!")
        return

    vaccine_name = tokens[1]
    doses = int(tokens[2])
    vaccine = None
    try:
        vaccine = Vaccine(vaccine_name, doses).get()
    except pymssql.Error as e:
        print("Error occurred when adding doses")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when adding doses")
        print("Error:", e)
        return

    # if the vaccine is not found in the database, add a new (vaccine, doses) entry.
    # else, update the existing entry by adding the new doses
    if vaccine is None:
        vaccine = Vaccine(vaccine_name, doses)
        try:
            vaccine.save_to_db()
        except pymssql.Error as e:
            print("Error occurred when adding doses")
            print("Db-Error:", e)
            quit()
        except Exception as e:
            print("Error occurred when adding doses")
            print("Error:", e)
            return
    else:
        # if the vaccine is not null, meaning that the vaccine already exists in our table
        try:
            vaccine.increase_available_doses(doses)
        except pymssql.Error as e:
            print("Error occurred when adding doses")
            print("Db-Error:", e)
            quit()
        except Exception as e:
            print("Error occurred when adding doses")
            print("Error:", e)
            return
    print("Doses updated!")


def show_appointments(tokens):
    
    # Part 2
    global current_caregiver, current_patient
    user_log_in = False
    if current_caregiver is not None or current_patient is not None:
        user_log_in = True

    if not user_log_in:
        print("Please login first")
        return

    cm = ConnectionManager()
    conn = cm.create_connection()

    try:
        cursor = conn.cursor(as_dict=True)

        if current_caregiver is not None:
            appointment_query = """
                SELECT reservation_id, vaccine_name, reservation_date, patient_username
                FROM Reservations
                WHERE caregiver_username = %s
                ORDER BY reservation_id;
            """
            caregiver_username = current_caregiver.username
            cursor.execute(appointment_query, caregiver_username)
            appointments = []
            for row in cursor:
                reservation_id = row['reservation_id']
                vaccine_name = row['vaccine_name']
                reservation_date = row['reservation_date']
                patient_username = row['patient_username']
                appointments.append(f"{reservation_id} {vaccine_name} {reservation_date} {patient_username}")

            if len(appointments) > 0:
                for appointment in appointments:
                    print(appointment)
            else:
                print("No appointments found for the caregiver")

        elif current_patient is not None:
            appointment_query = """
                SELECT reservation_id, vaccine_name, reservation_date, caregiver_username
                FROM Reservations
                WHERE patient_username = %s
                ORDER BY reservation_id;
            """
            patient_username = current_patient.username
            cursor.execute(appointment_query, patient_username)
            appointments = []
            for row in cursor:
                reservation_id = row['reservation_id']
                vaccine_name = row['vaccine_name']
                reservation_date = row['reservation_date']
                caregiver_username = row['caregiver_username']
                appointments.append(f"{reservation_id} {vaccine_name} {reservation_date} {caregiver_username}")

            if len(appointments) > 0:
                for appointment in appointments:
                    print(appointment)
            else:
                print("No appointments found for the patient")

    except pymssql.Error as db_error:
        print("Please try again")
    except Exception as error:
        print("Please try again")
    finally:
        cm.close_connection()



def logout(tokens):
    # Part 2

    global current_patient, current_caregiver
    user_log_in = False
    
    if current_patient is not None:
        user_log_in = True
    elif current_caregiver is not None:
        user_log_in = True

    if not user_log_in:
        print("Please login first")
        return

    try:
        if current_patient is not None:
            current_patient = None
        if current_caregiver is not None:
            current_caregiver = None
        print("Successfully logged out")

    except Exception as error:
        print("Please try again")



def start():
    stop = False
    print()
    print(" *** Please enter one of the following commands *** ")
    print("> create_patient <username> <password>")  # //TODO: implement create_patient (Part 1)
    print("> create_caregiver <username> <password>")
    print("> login_patient <username> <password>")  # // TODO: implement login_patient (Part 1)
    print("> login_caregiver <username> <password>")
    print("> search_caregiver_schedule <date>")  # // TODO: implement search_caregiver_schedule (Part 2)
    print("> reserve <date> <vaccine>")  # // TODO: implement reserve (Part 2)
    print("> upload_availability <date>")
    print("> cancel <appointment_id>")  # // TODO: implement cancel (extra credit)
    print("> add_doses <vaccine> <number>")
    print("> show_appointments")  # // TODO: implement show_appointments (Part 2)
    print("> logout")  # // TODO: implement logout (Part 2)
    print("> Quit")
    print()
    while not stop:
        response = ""
        print("> ", end='')

        try:
            response = str(input())
        except ValueError:
            print("Please try again!")
            break

        response = response.lower()
        tokens = response.split(" ")
        if len(tokens) == 0:
            ValueError("Please try again!")
            continue
        operation = tokens[0]
        if operation == "create_patient":
            create_patient(tokens)
        elif operation == "create_caregiver":
            create_caregiver(tokens)
        elif operation == "login_patient":
            login_patient(tokens)
        elif operation == "login_caregiver":
            login_caregiver(tokens)
        elif operation == "search_caregiver_schedule":
            search_caregiver_schedule(tokens)
        elif operation == "reserve":
            reserve(tokens)
        elif operation == "upload_availability":
            upload_availability(tokens)
        elif operation == cancel:
            cancel(tokens)
        elif operation == "add_doses":
            add_doses(tokens)
        elif operation == "show_appointments":
            show_appointments(tokens)
        elif operation == "logout":
            logout(tokens)
        elif operation == "quit":
            print("Bye!")
            stop = True
        else:
            print("Invalid operation name!")


if __name__ == "__main__":
    '''
    // pre-define the three types of authorized vaccines
    // note: it's a poor practice to hard-code these values, but we will do this ]
    // for the simplicity of this assignment
    // and then construct a map of vaccineName -> vaccineObject
    '''

    # start command line
    print()
    print("Welcome to the COVID-19 Vaccine Reservation Scheduling Application!")

    start()
