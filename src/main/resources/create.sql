CREATE TABLE Caregivers (
    username varchar(255),
    salt BINARY(16),
    Hash BINARY(16),
    PRIMARY KEY (Username)
);

CREATE TABLE Availabilities (
    Time date,
    username varchar(255) REFERENCES Caregivers,
    PRIMARY KEY (Time, username)
);


CREATE TABLE Vaccines (
    Name varchar(255),
    doses int,
    PRIMARY KEY (Name)
);

CREATE TABLE Patients (
    username varchar(255),
    salt BINARY(16),
    Hash BINARY(16),
    PRIMARY KEY (Username)
);

CREATE TABLE Reservations (
    reservation_id int IDENTITY(1,1),
    patient_username varchar(255) REFERENCES Patients(Username),
    caregiver_username varchar(255) REFERENCES Caregivers(Username),
    vaccine_name varchar(255) REFERENCES Vaccines(Name),
    reservation_date date,
    PRIMARY KEY (reservation_id)
);
