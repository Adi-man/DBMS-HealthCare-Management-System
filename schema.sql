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

-- 3. Rooms Table (room types and daily rates used for billing)
CREATE TABLE IF NOT EXISTS Rooms (
    room_id INT PRIMARY KEY AUTO_INCREMENT,
    room_number VARCHAR(20) NOT NULL UNIQUE,
    room_type VARCHAR(50) NOT NULL,
    daily_rate DECIMAL(10, 2) NOT NULL
);

-- 4. Patient Table
CREATE TABLE IF NOT EXISTS Patient (
    patient_id INT PRIMARY KEY AUTO_INCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    age INT CHECK (age >= 0),
    weight_kg DECIMAL(5, 2),
    appointment_time DATETIME NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Pending',
    assigned_doctor_id INT,
    registered_by_employee_id INT,
    room_id INT,
    FOREIGN KEY (assigned_doctor_id) REFERENCES Doctors(doctor_id) ON DELETE SET NULL,
    FOREIGN KEY (registered_by_employee_id) REFERENCES Employee(employee_id) ON DELETE SET NULL,
    FOREIGN KEY (room_id) REFERENCES Rooms(room_id) ON DELETE SET NULL
);

-- 5. Login accounts (admin and doctor users)
CREATE TABLE IF NOT EXISTS Users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,
    doctor_id INT,
    FOREIGN KEY (doctor_id) REFERENCES Doctors(doctor_id) ON DELETE CASCADE
);

-- 6. Medicines
CREATE TABLE IF NOT EXISTS Medicines (
    medicine_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL
);

-- 7. Medicines prescribed to a patient (used on the bill)
CREATE TABLE IF NOT EXISTS PatientMedicine (
    patient_id INT NOT NULL,
    medicine_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    PRIMARY KEY (patient_id, medicine_id),
    FOREIGN KEY (patient_id) REFERENCES Patient(patient_id) ON DELETE CASCADE,
    FOREIGN KEY (medicine_id) REFERENCES Medicines(medicine_id) ON DELETE CASCADE
);

-- 8. Bills (consultation + room + medicines)
CREATE TABLE IF NOT EXISTS Bills (
    bill_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id INT NOT NULL UNIQUE,
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

-- Sample Doctors (consultation fee is used on the bill)
INSERT IGNORE INTO Doctors (doctor_id, employee_id, specialization, qualification, consultation_fee) VALUES
(1, 1, 'Cardiology', 'MD, FACC', 1500.00),
(2, 2, 'Pediatrics', 'MD, FAAP', 800.00),
(3, 5, 'Orthopedics', 'MS Ortho', 1200.00),
(4, 6, 'Neurology', 'DM Neuro', 1800.00),
(5, 7, 'Dermatology', 'MD Derm', 900.00),
(6, 8, 'General Medicine', 'MBBS, MD', 600.00);

-- Sample Rooms
INSERT IGNORE INTO Rooms (room_id, room_number, room_type, daily_rate) VALUES
(1, 'G-101', 'General Ward', 1500.00),
(2, 'G-102', 'General Ward', 1500.00),
(3, 'SP-201', 'Semi-Private', 3000.00),
(4, 'P-301', 'Private', 5000.00),
(5, 'ICU-1', 'ICU', 8000.00);

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

-- Sample Patients (includes appointments on 2026-09-26 for the doctor dashboard)
INSERT IGNORE INTO Patient (patient_id, first_name, last_name, age, weight_kg, appointment_time, status, assigned_doctor_id, registered_by_employee_id, room_id) VALUES
(1, 'John', 'Doe', 45, 82.50, '2026-10-01 09:30:00', 'Pending', 1, 3, 4),
(2, 'Emily', 'Davis', 8, 24.20, '2026-10-01 10:15:00', 'Pending', 2, 3, 1),
(3, 'Michael', 'Brown', 62, 78.00, '2026-09-26 11:00:00', 'Pending', 1, 3, 5),
(4, 'Sophia', 'Wilson', 29, 61.30, '2026-10-02 14:00:00', 'Pending', 2, 3, 3),
(5, 'Raj', 'Patel', 34, 74.00, '2026-09-26 09:00:00', 'Pending', 3, 3, 2),
(6, 'Linda', 'Nguyen', 51, 66.40, '2026-09-26 10:30:00', 'Pending', 4, 3, 4),
(7, 'Omar', 'Hassan', 22, 70.10, '2026-09-26 15:00:00', 'Pending', 5, 3, 1),
(8, 'Grace', 'Kim', 40, 58.00, '2026-09-26 16:30:00', 'Pending', 6, 3, 3),
(9, 'Anita', 'Singh', 55, 64.00, '2026-09-26 08:30:00', 'Pending', 1, 3, 4);

-- Login users are created automatically the first time you run app.py
-- Admin:  admin / admin123
-- Doctors: rchen, sjenkins, psharma, jwilson, akhan, tlee  (password: doctor123)
