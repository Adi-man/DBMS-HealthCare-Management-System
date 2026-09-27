-- Create Database
CREATE DATABASE IF NOT EXISTS HealthcareDB;
USE HealthcareDB;

-- 1. Employee Table
CREATE TABLE IF NOT EXISTS Employee (
    employee_id INT PRIMARY KEY AUTO_INCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    role VARCHAR(50) NOT NULL,
    phone VARCHAR(15),
    email VARCHAR(100) UNIQUE
);

-- 2. Doctors Table (Foreign Key references Employee)
CREATE TABLE IF NOT EXISTS Doctors (
    doctor_id INT PRIMARY KEY AUTO_INCREMENT,
    employee_id INT NOT NULL UNIQUE,
    specialization VARCHAR(100) NOT NULL,
    qualification VARCHAR(100) NOT NULL,
    consultation_fee DECIMAL(10, 2) NOT NULL DEFAULT 500.00,
    FOREIGN KEY (employee_id) REFERENCES Employee(employee_id) ON DELETE CASCADE
);

-- 3. Rooms Table (facilities and occupancy status)
CREATE TABLE IF NOT EXISTS Rooms (
    room_id INT PRIMARY KEY AUTO_INCREMENT,
    room_number VARCHAR(20) NOT NULL UNIQUE,
    room_type VARCHAR(50) NOT NULL,
    daily_rate DECIMAL(10, 2) NOT NULL,
    facilities VARCHAR(255) DEFAULT 'AC, Wifi, TV',
    status VARCHAR(20) DEFAULT 'Vacant'
);

-- 4. Patient Table (Fully updated with phone, address, description, insurance, tag)
CREATE TABLE IF NOT EXISTS Patient (
    patient_id INT PRIMARY KEY AUTO_INCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    age INT CHECK (age >= 0),
    weight_kg DECIMAL(5, 2),
    phone VARCHAR(20),
    address VARCHAR(255),
    problem_description TEXT,
    has_insurance BOOLEAN DEFAULT FALSE,
    insurance_details VARCHAR(255),
    tag VARCHAR(50) DEFAULT 'New',
    appointment_time DATETIME NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Pending',
    assigned_doctor_id INT,
    registered_by_employee_id INT,
    room_id INT,
    FOREIGN KEY (assigned_doctor_id) REFERENCES Doctors(doctor_id) ON DELETE SET NULL,
    FOREIGN KEY (registered_by_employee_id) REFERENCES Employee(employee_id) ON DELETE SET NULL,
    FOREIGN KEY (room_id) REFERENCES Rooms(room_id) ON DELETE SET NULL
);

-- 5. Patient Notes Table (Clinical evaluation & doctor visit history)
CREATE TABLE IF NOT EXISTS PatientNotes (
    note_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    note_text TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES Patient(patient_id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES Doctors(doctor_id) ON DELETE CASCADE
);

-- 6. Login accounts (admin and doctor users)
CREATE TABLE IF NOT EXISTS Users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,
    doctor_id INT,
    FOREIGN KEY (doctor_id) REFERENCES Doctors(doctor_id) ON DELETE CASCADE
);

-- 7. Medicines
CREATE TABLE IF NOT EXISTS Medicines (
    medicine_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL
);

-- 8. Medicines prescribed to a patient
CREATE TABLE IF NOT EXISTS PatientMedicine (
    patient_id INT NOT NULL,
    medicine_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    PRIMARY KEY (patient_id, medicine_id),
    FOREIGN KEY (patient_id) REFERENCES Patient(patient_id) ON DELETE CASCADE,
    FOREIGN KEY (medicine_id) REFERENCES Medicines(medicine_id) ON DELETE CASCADE
);

-- 9. Bills (days_stayed for dynamic room billing)
CREATE TABLE IF NOT EXISTS Bills (
    bill_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id INT NOT NULL UNIQUE,
    days_stayed INT DEFAULT 1,
    consultation_fee DECIMAL(10, 2) NOT NULL DEFAULT 0,
    room_charge DECIMAL(10, 2) NOT NULL DEFAULT 0,
    medicine_charge DECIMAL(10, 2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES Patient(patient_id) ON DELETE CASCADE
);

-- Sample Employees
INSERT IGNORE INTO Employee (employee_id, first_name, last_name, role, phone, email) VALUES
(1, 'Robert', 'Chen', 'Doctor', '555-0101', 'r.chen@hospital.org'),
(2, 'Sarah', 'Jenkins', 'Doctor', '555-0102', 's.jenkins@hospital.org'),
(3, 'Maria', 'Garcia', 'Receptionist', '555-0103', 'm.garcia@hospital.org'),
(4, 'David', 'Miller', 'Nurse', '555-0104', 'd.miller@hospital.org'),
(5, 'Priya', 'Sharma', 'Doctor', '555-0105', 'p.sharma@hospital.org'),
(6, 'James', 'Wilson', 'Doctor', '555-0106', 'j.wilson@hospital.org'),
(7, 'Aisha', 'Khan', 'Doctor', '555-0107', 'a.khan@hospital.org'),
(8, 'Thomas', 'Lee', 'Doctor', '555-0108', 't.lee@hospital.org');

-- Sample Doctors
INSERT IGNORE INTO Doctors (doctor_id, employee_id, specialization, qualification, consultation_fee) VALUES
(1, 1, 'Cardiology', 'MD, FACC', 1500.00),
(2, 2, 'Pediatrics', 'MD, FAAP', 800.00),
(3, 5, 'Orthopedics', 'MS Ortho', 1200.00),
(4, 6, 'Neurology', 'DM Neuro', 1800.00),
(5, 7, 'Dermatology', 'MD Derm', 900.00),
(6, 8, 'General Medicine', 'MBBS, MD', 600.00);

-- Sample Rooms
INSERT IGNORE INTO Rooms (room_id, room_number, room_type, daily_rate, facilities, status) VALUES
(1, 'G-101', 'General Ward', 1500.00, 'Shared AC, Wifi, Standard Bed', 'Occupied'),
(2, 'G-102', 'General Ward', 1500.00, 'Shared AC, Wifi, Standard Bed', 'Occupied'),
(3, 'SP-201', 'Semi-Private', 3000.00, 'AC, Wifi, TV, Recliner', 'Occupied'),
(4, 'P-301', 'Private', 5000.00, 'AC, Private Bathroom, Wifi, TV, Sofa Bed', 'Occupied'),
(5, 'ICU-1', 'ICU', 8000.00, '24/7 Monitoring, Ventilator, AC, Oxygen Line', 'Occupied');

-- Sample Medicines
INSERT IGNORE INTO Medicines (medicine_id, name, unit_price) VALUES
(1, 'Paracetamol 500mg', 20.00),
(2, 'Amoxicillin 250mg', 80.00),
(3, 'Ibuprofen 400mg', 35.00),
(4, 'Aspirin 75mg', 25.00),
(5, 'Cetirizine 10mg', 40.00),
(6, 'Omeprazole 20mg', 55.00),
(7, 'Insulin (vial)', 150.00),
(8, 'Salbutamol Inhaler', 90.00);

-- Sample Patients (Fully populated with Phone, Address, Description, Insurance, and Tag)
INSERT IGNORE INTO Patient (patient_id, first_name, last_name, age, weight_kg, phone, address, problem_description, has_insurance, insurance_details, tag, appointment_time, status, assigned_doctor_id, registered_by_employee_id, room_id) VALUES
(1, 'John', 'Doe', 45, 82.50, '9876543210', '123 Main St, Kothrud, Pune', 'Chest tightness and shortness of breath during exertion.', TRUE, 'HDFC Ergo - POL12345', 'Active', '2026-09-20 09:30:00', 'Pending', 1, 3, 4),
(2, 'Emily', 'Davis', 8, 24.20, '9876543211', '456 Park Ave, Viman Nagar, Pune', 'High fever, sore throat, and persistent nocturnal coughing.', FALSE, NULL, 'Checkup', '2026-09-26 10:15:00', 'Pending', 2, 3, 1),
(3, 'Michael', 'Brown', 62, 78.00, '9876543212', '789 Oak Rd, Baner, Pune', 'Acute dyspnea and elevated blood pressure requiring ICU care.', TRUE, 'Star Health - SH9876', 'Emergency', '2026-09-26 11:00:00', 'Pending', 1, 3, 5),
(4, 'Sophia', 'Wilson', 29, 61.30, '9876543213', '102 MG Road, Camp, Pune', 'Recurrent migraine headaches accompanied by mild dizziness.', TRUE, 'ICICI Lombard - IL7721', 'Active', '2026-09-25 14:00:00', 'Completed', 2, 3, 3),
(5, 'Raj', 'Patel', 34, 74.00, '9876543214', '55 SB Road, Shivaji Nagar, Pune', 'Right knee swelling following a sports injury during football.', FALSE, NULL, 'Checkup', '2026-09-26 09:00:00', 'Pending', 3, 3, 2),
(6, 'Linda', 'Nguyen', 51, 66.40, '9876543215', '88 Koregaon Park, Pune', 'Persistent lower back pain radiating down the left leg.', TRUE, 'Care Health - CH4412', 'Active', '2026-09-26 10:30:00', 'Pending', 4, 3, 4),
(7, 'Omar', 'Hassan', 22, 70.10, '9876543216', '12 FC Road, Deccan, Pune', 'Allergic skin rashes and severe itching over both arms.', FALSE, NULL, 'New', '2026-09-26 15:00:00', 'Pending', 5, 3, 1),
(8, 'Grace', 'Kim', 40, 58.00, '9876543217', '34 Aundh Road, Aundh, Pune', 'Routine post-surgery recovery checkup and vitals assessment.', TRUE, 'Max Bupa - MB3309', 'Discharged', '2026-09-26 16:30:00', 'Completed', 6, 3, 3),
(9, 'Anita', 'Singh', 55, 64.00, '9876543218', '90 Hadapsar Main St, Pune', 'Chronic joint stiffness and early morning hand numbness.', TRUE, 'Bajaj Allianz - BA9012', 'Active', '2026-09-26 08:30:00', 'Pending', 1, 3, 4);

-- Initial Clinical Notes
INSERT IGNORE INTO PatientNotes (note_id, patient_id, doctor_id, note_text, created_at) VALUES
(1, 1, 1, 'Patient presented with chest pain. ECG performed, mild ST elevated signs observed. Recommended bed rest in Private Room 301.', '2026-09-20 10:15:00'),
(2, 3, 1, 'Patient admitted to ICU due to severe dyspnea and high blood pressure. Started on IV medication.', '2026-09-26 11:30:00');