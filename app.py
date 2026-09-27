from functools import wraps
from decimal import Decimal
from datetime import datetime
import math

from flask import Flask, jsonify, request, send_from_directory, session
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector

app = Flask(__name__, static_url_path='', static_folder='.')
app.secret_key = 'healthcare-local-secret-key'

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Aditya123$',
    'database': 'HealthcareDB'
}


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def column_exists(cursor, table_name, column_name):
    cursor.execute(
        """
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """,
        (DB_CONFIG['database'], table_name, column_name)
    )
    return cursor.fetchone()[0] > 0


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Base Tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Rooms (
            room_id INT PRIMARY KEY AUTO_INCREMENT,
            room_number VARCHAR(20) NOT NULL UNIQUE,
            room_type VARCHAR(50) NOT NULL,
            daily_rate DECIMAL(10, 2) NOT NULL,
            facilities VARCHAR(255) DEFAULT 'Standard Facilities',
            status VARCHAR(20) DEFAULT 'Vacant'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Medicines (
            medicine_id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL,
            unit_price DECIMAL(10, 2) NOT NULL
        )
    """)

    cursor.execute("""
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
            room_id INT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PatientNotes (
            note_id INT PRIMARY KEY AUTO_INCREMENT,
            patient_id INT NOT NULL,
            doctor_id INT NOT NULL,
            note_text TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES Patient(patient_id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            user_id INT PRIMARY KEY AUTO_INCREMENT,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL,
            doctor_id INT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PatientMedicine (
            patient_id INT NOT NULL,
            medicine_id INT NOT NULL,
            quantity INT NOT NULL DEFAULT 1,
            PRIMARY KEY (patient_id, medicine_id),
            FOREIGN KEY (patient_id) REFERENCES Patient(patient_id) ON DELETE CASCADE,
            FOREIGN KEY (medicine_id) REFERENCES Medicines(medicine_id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
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
        )
    """)

    # Alter schema for missing columns if upgrading existing database
    patient_schema_updates = [
        ('phone', 'VARCHAR(20)'),
        ('address', 'VARCHAR(255)'),
        ('problem_description', 'TEXT'),
        ('has_insurance', 'BOOLEAN DEFAULT FALSE'),
        ('insurance_details', 'VARCHAR(255)'),
        ('tag', "VARCHAR(50) DEFAULT 'New'")
    ]
    for col, col_type in patient_schema_updates:
        if not column_exists(cursor, 'Patient', col):
            cursor.execute(f"ALTER TABLE Patient ADD COLUMN {col} {col_type}")

    if not column_exists(cursor, 'Rooms', 'facilities'):
        cursor.execute("ALTER TABLE Rooms ADD COLUMN facilities VARCHAR(255) DEFAULT 'AC, Wifi, TV'")
    if not column_exists(cursor, 'Rooms', 'status'):
        cursor.execute("ALTER TABLE Rooms ADD COLUMN status VARCHAR(20) DEFAULT 'Vacant'")

    if not column_exists(cursor, 'Bills', 'days_stayed'):
        cursor.execute("ALTER TABLE Bills ADD COLUMN days_stayed INT DEFAULT 1")

    # Seed Admin User
    cursor.execute("SELECT COUNT(*) FROM Users WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO Users (username, password_hash, role, doctor_id) VALUES (%s, %s, %s, %s)",
            ('admin', generate_password_hash('admin123'), 'admin', None)
        )

    # AUTO-UPDATE SEEDER: Populate details if existing database rows are empty/NULL
    sample_patient_data = [
        (1, '9876543210', '123 Main St, Kothrud, Pune', 'Chest tightness and shortness of breath during exertion.', True, 'HDFC Ergo - POL12345', 'Active'),
        (2, '9876543211', '456 Park Ave, Viman Nagar, Pune', 'High fever, sore throat, and persistent nocturnal coughing.', False, None, 'Checkup'),
        (3, '9876543212', '789 Oak Rd, Baner, Pune', 'Acute dyspnea and elevated blood pressure requiring ICU care.', True, 'Star Health - SH9876', 'Emergency'),
        (4, '9876543213', '102 MG Road, Camp, Pune', 'Recurrent migraine headaches accompanied by mild dizziness.', True, 'ICICI Lombard - IL7721', 'Active'),
        (5, '9876543214', '55 SB Road, Shivaji Nagar, Pune', 'Right knee swelling following a sports injury during football.', False, None, 'Checkup'),
        (6, '9876543215', '88 Koregaon Park, Pune', 'Persistent lower back pain radiating down the left leg.', True, 'Care Health - CH4412', 'Active'),
        (7, '9876543216', '12 FC Road, Deccan, Pune', 'Allergic skin rashes and severe itching over both arms.', False, None, 'New'),
        (8, '9876543217', '34 Aundh Road, Aundh, Pune', 'Routine post-surgery recovery checkup and vitals assessment.', True, 'Max Bupa - MB3309', 'Discharged'),
        (9, '9876543218', '90 Hadapsar Main St, Pune', 'Chronic joint stiffness and early morning hand numbness.', True, 'Bajaj Allianz - BA9012', 'Active')
    ]

    for pid, phone, addr, desc, ins, ins_det, tag in sample_patient_data:
        cursor.execute(
            """
            UPDATE Patient 
            SET phone = %s, address = %s, problem_description = %s, 
                has_insurance = %s, insurance_details = %s, tag = %s 
            WHERE patient_id = %s AND (phone IS NULL OR phone = '' OR phone = 'N/A')
            """,
            (phone, addr, desc, ins, ins_det, tag, pid)
        )

    conn.commit()
    cursor.close()
    conn.close()


try:
    init_db()
    print("Database connection & auto-seeding successful!")
except mysql.connector.Error as err:
    print(f"Database Initialization Error: {err}")


def current_user():
    if 'user_id' not in session:
        return None
    return {
        'user_id': session['user_id'],
        'username': session['username'],
        'role': session['role'],
        'doctor_id': session.get('doctor_id'),
        'display_name': session.get('display_name')
    }


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return jsonify({'error': 'Please log in'}), 401
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or user['role'] != 'admin':
            return jsonify({'error': 'Only the admin can perform this action'}), 403
        return fn(*args, **kwargs)
    return wrapper


def money(value):
    if value is None:
        return 0.0
    return float(value)


def calculate_stay_duration(appointment_time):
    if not appointment_time:
        return 1
    if isinstance(appointment_time, str):
        try:
            app_dt = datetime.strptime(appointment_time, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            app_dt = datetime.strptime(appointment_time, '%Y-%m-%d %H:%M')
    else:
        app_dt = appointment_time
    
    delta = datetime.now() - app_dt
    days = math.ceil(delta.total_seconds() / 86400)
    return max(1, days)


def parse_appointment_time(raw):
    appointment_time = (raw or '').replace('T', ' ')
    if len(appointment_time) == 16:
        appointment_time += ':00'
    return appointment_time


def patient_list_query(where_sql='', params=()):
    query = f"""
        SELECT
            p.patient_id, p.first_name, p.last_name,
            CONCAT(p.first_name, ' ', p.last_name) AS full_name,
            p.age, p.weight_kg, p.phone, p.address, p.problem_description,
            p.has_insurance, p.insurance_details, p.tag,
            DATE_FORMAT(p.appointment_time, '%Y-%m-%d %H:%i:%s') AS appointment_time_raw,
            DATE_FORMAT(p.appointment_time, '%Y-%m-%d %H:%i') AS appointment_time,
            DATE(p.appointment_time) AS appointment_date,
            p.status, p.assigned_doctor_id,
            CONCAT('Dr. ', de.first_name, ' ', de.last_name) AS doctor_name,
            d.consultation_fee, p.registered_by_employee_id,
            CONCAT(re.first_name, ' ', re.last_name) AS registered_by_name,
            p.room_id, r.room_number, r.room_type, r.daily_rate AS room_rate
        FROM Patient p
        LEFT JOIN Doctors d ON p.assigned_doctor_id = d.doctor_id
        LEFT JOIN Employee de ON d.employee_id = de.employee_id
        LEFT JOIN Employee re ON p.registered_by_employee_id = re.employee_id
        LEFT JOIN Rooms r ON p.room_id = r.room_id
        {where_sql}
        ORDER BY p.appointment_time DESC, p.patient_id DESC
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    for row in rows:
        row['consultation_fee'] = money(row.get('consultation_fee'))
        row['room_rate'] = money(row.get('room_rate'))
        row['weight_kg'] = money(row.get('weight_kg')) if row.get('weight_kg') else None
        row['days_stayed'] = calculate_stay_duration(row.get('appointment_time_raw'))
    return rows


@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')


@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json or {}
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT u.user_id, u.username, u.password_hash, u.role, u.doctor_id,
                   e.first_name, e.last_name
            FROM Users u
            LEFT JOIN Doctors d ON u.doctor_id = d.doctor_id
            LEFT JOIN Employee e ON d.employee_id = e.employee_id
            WHERE u.username = %s
            """,
            (username,)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({'error': 'Invalid username or password'}), 401

        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['role'] = user['role']
        session['doctor_id'] = user['doctor_id']
        if user['role'] == 'admin':
            session['display_name'] = 'Administrator'
        else:
            session['display_name'] = f"Dr. {user['first_name']} {user['last_name']}"
        return jsonify(current_user())
    except Error as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'})


@app.route('/api/me', methods=['GET'])
@login_required
def me():
    return jsonify(current_user())


@app.route('/api/patients', methods=['GET'])
@login_required
def get_patients():
    try:
        user = current_user()
        if user['role'] == 'doctor':
            rows = patient_list_query('WHERE p.assigned_doctor_id = %s', (user['doctor_id'],))
        else:
            rows = patient_list_query()
        return jsonify(rows)
    except Error as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/patients/<int:patient_id>/notes', methods=['GET', 'POST'])
@login_required
def handle_patient_notes(patient_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        user = current_user()

        if request.method == 'POST':
            data = request.json or {}
            note_text = data.get('note_text', '').strip()
            if not note_text:
                return jsonify({'error': 'Note text cannot be empty'}), 400
            
            doc_id = user['doctor_id'] if user['role'] == 'doctor' else (data.get('doctor_id') or 1)
            cursor.execute(
                "INSERT INTO PatientNotes (patient_id, doctor_id, note_text) VALUES (%s, %s, %s)",
                (patient_id, doc_id, note_text)
            )
            conn.commit()

        cursor.execute(
            """
            SELECT pn.note_id, pn.note_text, DATE_FORMAT(pn.created_at, '%Y-%m-%d %H:%i') AS created_at,
                   CONCAT('Dr. ', e.first_name, ' ', e.last_name) AS doctor_name
            FROM PatientNotes pn
            JOIN Doctors d ON pn.doctor_id = d.doctor_id
            JOIN Employee e ON d.employee_id = e.employee_id
            WHERE pn.patient_id = %s
            ORDER BY pn.created_at DESC
            """,
            (patient_id,)
        )
        notes = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(notes)
    except Error as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/patients', methods=['POST'])
@admin_required
def add_patient():
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            INSERT INTO Patient
            (first_name, last_name, age, weight_kg, phone, address, problem_description,
             has_insurance, insurance_details, tag, appointment_time, status,
             assigned_doctor_id, registered_by_employee_id, room_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            data.get('first_name'), data.get('last_name'),
            int(data['age']) if data.get('age') else None,
            float(data['weight_kg']) if data.get('weight_kg') else None,
            data.get('phone'), data.get('address'), data.get('problem_description'),
            bool(data.get('has_insurance')), data.get('insurance_details'),
            data.get('tag', 'New'),
            parse_appointment_time(data.get('appointment_time')),
            data.get('status', 'Pending'),
            int(data['assigned_doctor_id']) if data.get('assigned_doctor_id') else None,
            int(data['registered_by_employee_id']) if data.get('registered_by_employee_id') else None,
            int(data['room_id']) if data.get('room_id') else None
        )
        cursor.execute(query, values)
        
        if data.get('room_id'):
            cursor.execute("UPDATE Rooms SET status = 'Occupied' WHERE room_id = %s", (data['room_id'],))
            
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Patient inserted successfully'}), 201
    except Error as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/patients/<int:patient_id>', methods=['PUT'])
@admin_required
def update_patient(patient_id):
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            UPDATE Patient
            SET first_name = %s, last_name = %s, age = %s, weight_kg = %s,
                phone = %s, address = %s, problem_description = %s,
                has_insurance = %s, insurance_details = %s, tag = %s,
                appointment_time = %s, status = %s, assigned_doctor_id = %s,
                registered_by_employee_id = %s, room_id = %s
            WHERE patient_id = %s
        """
        values = (
            data.get('first_name'), data.get('last_name'),
            int(data['age']) if data.get('age') else None,
            float(data['weight_kg']) if data.get('weight_kg') else None,
            data.get('phone'), data.get('address'), data.get('problem_description'),
            bool(data.get('has_insurance')), data.get('insurance_details'),
            data.get('tag', 'New'),
            parse_appointment_time(data.get('appointment_time')),
            data.get('status', 'Pending'),
            int(data['assigned_doctor_id']) if data.get('assigned_doctor_id') else None,
            int(data['registered_by_employee_id']) if data.get('registered_by_employee_id') else None,
            int(data['room_id']) if data.get('room_id') else None,
            patient_id
        )
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Patient updated successfully'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/doctors', methods=['GET'])
@login_required
def get_doctors():
    try:
        user = current_user()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Doctors see only their own row profile
        if user['role'] == 'doctor':
            query = """
                SELECT
                    d.doctor_id, d.employee_id,
                    CONCAT('Dr. ', e.first_name, ' ', e.last_name) AS name,
                    d.specialization, d.qualification, d.consultation_fee,
                    COUNT(CASE WHEN p.status <> 'Cancelled' AND p.status <> 'Discharged' THEN p.patient_id END) AS active_patient_count
                FROM Doctors d
                JOIN Employee e ON d.employee_id = e.employee_id
                LEFT JOIN Patient p ON d.doctor_id = p.assigned_doctor_id
                WHERE d.doctor_id = %s
                GROUP BY d.doctor_id, d.employee_id, e.first_name, e.last_name, d.specialization, d.qualification, d.consultation_fee
                ORDER BY d.doctor_id ASC
            """
            cursor.execute(query, (user['doctor_id'],))
        else:
            query = """
                SELECT
                    d.doctor_id, d.employee_id,
                    CONCAT('Dr. ', e.first_name, ' ', e.last_name) AS name,
                    d.specialization, d.qualification, d.consultation_fee,
                    COUNT(CASE WHEN p.status <> 'Cancelled' AND p.status <> 'Discharged' THEN p.patient_id END) AS active_patient_count
                FROM Doctors d
                JOIN Employee e ON d.employee_id = e.employee_id
                LEFT JOIN Patient p ON d.doctor_id = p.assigned_doctor_id
                GROUP BY d.doctor_id, d.employee_id, e.first_name, e.last_name, d.specialization, d.qualification, d.consultation_fee
                ORDER BY d.doctor_id ASC
            """
            cursor.execute(query)
            
        doctors = cursor.fetchall()
        cursor.close()
        conn.close()
        for doc in doctors:
            doc['consultation_fee'] = money(doc.get('consultation_fee'))
        return jsonify(doctors)
    except Error as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rooms', methods=['GET'])
@login_required
def get_rooms():
    try:
        user = current_user()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Doctors see room occupancy for their own patients only
        if user['role'] == 'doctor':
            cursor.execute(
                """
                SELECT r.room_id, r.room_number, r.room_type, r.daily_rate, r.facilities,
                       CASE WHEN COUNT(p.patient_id) > 0 THEN 'Occupied' ELSE 'Vacant' END AS occupancy_status,
                       GROUP_CONCAT(CONCAT(p.first_name, ' ', p.last_name) SEPARATOR ', ') AS occupied_by
                FROM Rooms r
                LEFT JOIN Patient p ON r.room_id = p.room_id 
                    AND p.assigned_doctor_id = %s 
                    AND p.status <> 'Cancelled' 
                    AND p.status <> 'Discharged'
                GROUP BY r.room_id, r.room_number, r.room_type, r.daily_rate, r.facilities
                ORDER BY r.room_id ASC
                """,
                (user['doctor_id'],)
            )
        else:
            cursor.execute(
                """
                SELECT r.room_id, r.room_number, r.room_type, r.daily_rate, r.facilities,
                       CASE WHEN COUNT(p.patient_id) > 0 THEN 'Occupied' ELSE 'Vacant' END AS occupancy_status,
                       GROUP_CONCAT(CONCAT(p.first_name, ' ', p.last_name) SEPARATOR ', ') AS occupied_by
                FROM Rooms r
                LEFT JOIN Patient p ON r.room_id = p.room_id 
                    AND p.status <> 'Cancelled' 
                    AND p.status <> 'Discharged'
                GROUP BY r.room_id, r.room_number, r.room_type, r.daily_rate, r.facilities
                ORDER BY r.room_id ASC
                """
            )
        rooms = cursor.fetchall()
        cursor.close()
        conn.close()
        for room in rooms:
            room['daily_rate'] = money(room.get('daily_rate'))
        return jsonify(rooms)
    except Error as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/medicines', methods=['GET'])
@login_required
def get_medicines():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT medicine_id, name, unit_price FROM Medicines ORDER BY medicine_id ASC")
        medicines = cursor.fetchall()
        cursor.close()
        conn.close()
        for med in medicines:
            med['unit_price'] = money(med.get('unit_price'))
        return jsonify(medicines)
    except Error as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/billing/<int:patient_id>', methods=['GET'])
@login_required
def get_billing(patient_id):
    try:
        rows = patient_list_query('WHERE p.patient_id = %s', (patient_id,))
        if not rows:
            return jsonify({'error': 'Patient not found'}), 404
        patient = rows[0]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT pm.medicine_id, pm.quantity, m.name, m.unit_price
            FROM PatientMedicine pm
            JOIN Medicines m ON pm.medicine_id = m.medicine_id
            WHERE pm.patient_id = %s
            """,
            (patient_id,)
        )
        medicines = cursor.fetchall()
        cursor.execute("SELECT * FROM Bills WHERE patient_id = %s", (patient_id,))
        bill = cursor.fetchone()
        cursor.close()
        conn.close()

        days_stayed = patient['days_stayed']
        consultation = money(patient.get('consultation_fee'))
        room_charge = money(patient.get('room_rate')) * days_stayed
        
        med_charge = 0.0
        for m in medicines:
            m['unit_price'] = money(m['unit_price'])
            m['line_total'] = round(m['unit_price'] * m['quantity'], 2)
            med_charge += m['line_total']

        preview = {
            'days_stayed': days_stayed,
            'consultation_fee': consultation,
            'room_charge': room_charge,
            'medicine_charge': round(med_charge, 2),
            'total_amount': round(consultation + room_charge + med_charge, 2)
        }

        return jsonify({'patient': patient, 'medicines': medicines, 'preview': preview, 'bill': bill})
    except Error as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/bills', methods=['GET'])
@login_required
def get_bills():
    try:
        user = current_user()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT
                b.bill_id, b.patient_id, b.days_stayed,
                CONCAT(p.first_name, ' ', p.last_name) AS patient_name,
                CONCAT('Dr. ', de.first_name, ' ', de.last_name) AS doctor_name,
                r.room_number, r.room_type,
                b.consultation_fee, b.room_charge, b.medicine_charge, b.total_amount,
                DATE_FORMAT(b.generated_at, '%Y-%m-%d %H:%i') AS generated_at
            FROM Bills b
            JOIN Patient p ON b.patient_id = p.patient_id
            LEFT JOIN Doctors d ON p.assigned_doctor_id = d.doctor_id
            LEFT JOIN Employee de ON d.employee_id = de.employee_id
            LEFT JOIN Rooms r ON p.room_id = r.room_id
        """
        params = ()
        if user['role'] == 'doctor':
            query += " WHERE p.assigned_doctor_id = %s"
            params = (user['doctor_id'],)
        query += " ORDER BY b.bill_id DESC"
        cursor.execute(query, params)
        bills = cursor.fetchall()
        cursor.close()
        conn.close()
        for bill in bills:
            for key in ('consultation_fee', 'room_charge', 'medicine_charge', 'total_amount'):
                bill[key] = money(bill.get(key))
        return jsonify(bills)
    except Error as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/bills', methods=['POST'])
@admin_required
def save_bill():
    try:
        data = request.json or {}
        patient_id = int(data['patient_id'])
        room_id = int(data['room_id']) if data.get('room_id') else None
        medicines = data.get('medicines') or []

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT appointment_time, assigned_doctor_id FROM Patient WHERE patient_id = %s",
            (patient_id,)
        )
        patient = cursor.fetchone()
        if not patient:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Patient not found'}), 404

        days_stayed = calculate_stay_duration(patient['appointment_time'])

        cursor.execute("SELECT consultation_fee FROM Doctors WHERE doctor_id = %s", (patient.get('assigned_doctor_id'),))
        doc = cursor.fetchone()
        consultation = money(doc['consultation_fee']) if doc else 0.0

        room_charge = 0.0
        if room_id:
            cursor.execute("SELECT daily_rate FROM Rooms WHERE room_id = %s", (room_id,))
            room = cursor.fetchone()
            if room:
                room_charge = money(room['daily_rate']) * days_stayed

        cursor.execute("UPDATE Patient SET room_id = %s WHERE patient_id = %s", (room_id, patient_id))
        cursor.execute("DELETE FROM PatientMedicine WHERE patient_id = %s", (patient_id,))

        medicine_charge = 0.0
        for item in medicines:
            med_id = item.get('medicine_id')
            qty = int(item.get('quantity') or 0)
            if not med_id or qty <= 0:
                continue
            cursor.execute("SELECT unit_price FROM Medicines WHERE medicine_id = %s", (med_id,))
            med = cursor.fetchone()
            if med:
                cursor.execute(
                    "INSERT INTO PatientMedicine (patient_id, medicine_id, quantity) VALUES (%s, %s, %s)",
                    (patient_id, med_id, qty)
                )
                medicine_charge += money(med['unit_price']) * qty

        total = round(consultation + room_charge + medicine_charge, 2)

        cursor.execute(
            """
            INSERT INTO Bills (patient_id, days_stayed, consultation_fee, room_charge, medicine_charge, total_amount)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                days_stayed = VALUES(days_stayed),
                consultation_fee = VALUES(consultation_fee),
                room_charge = VALUES(room_charge),
                medicine_charge = VALUES(medicine_charge),
                total_amount = VALUES(total_amount),
                generated_at = CURRENT_TIMESTAMP
            """,
            (patient_id, days_stayed, consultation, room_charge, medicine_charge, total)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Bill saved successfully'}), 201
    except Error as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)