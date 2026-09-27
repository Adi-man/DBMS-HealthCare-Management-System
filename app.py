from functools import wraps
from decimal import Decimal

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
    """Create new tables/columns and seed login users if the old schema is already loaded."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Rooms (
            room_id INT PRIMARY KEY AUTO_INCREMENT,
            room_number VARCHAR(20) NOT NULL UNIQUE,
            room_type VARCHAR(50) NOT NULL,
            daily_rate DECIMAL(10, 2) NOT NULL
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
        CREATE TABLE IF NOT EXISTS Users (
            user_id INT PRIMARY KEY AUTO_INCREMENT,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL,
            doctor_id INT,
            FOREIGN KEY (doctor_id) REFERENCES Doctors(doctor_id) ON DELETE CASCADE
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
            consultation_fee DECIMAL(10, 2) NOT NULL DEFAULT 0,
            room_charge DECIMAL(10, 2) NOT NULL DEFAULT 0,
            medicine_charge DECIMAL(10, 2) NOT NULL DEFAULT 0,
            total_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
            generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES Patient(patient_id) ON DELETE CASCADE
        )
    """)

    if not column_exists(cursor, 'Doctors', 'consultation_fee'):
        cursor.execute(
            "ALTER TABLE Doctors ADD COLUMN consultation_fee DECIMAL(10, 2) NOT NULL DEFAULT 500.00"
        )

    if not column_exists(cursor, 'Patient', 'room_id'):
        cursor.execute("ALTER TABLE Patient ADD COLUMN room_id INT NULL")
        cursor.execute(
            """
            ALTER TABLE Patient
            ADD CONSTRAINT fk_patient_room
            FOREIGN KEY (room_id) REFERENCES Rooms(room_id) ON DELETE SET NULL
            """
        )

    extra_employees = [
        (5, 'Priya', 'Sharma', 'Doctor', '555-0105', 'p.sharma@hospital.org'),
        (6, 'James', 'Wilson', 'Doctor', '555-0106', 'j.wilson@hospital.org'),
        (7, 'Aisha', 'Khan', 'Doctor', '555-0107', 'a.khan@hospital.org'),
        (8, 'Thomas', 'Lee', 'Doctor', '555-0108', 't.lee@hospital.org'),
    ]
    cursor.executemany(
        """
        INSERT IGNORE INTO Employee (employee_id, first_name, last_name, role, phone, email)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        extra_employees
    )

    extra_doctors = [
        (3, 5, 'Orthopedics', 'MS Ortho', 1200.00),
        (4, 6, 'Neurology', 'DM Neuro', 1800.00),
        (5, 7, 'Dermatology', 'MD Derm', 900.00),
        (6, 8, 'General Medicine', 'MBBS, MD', 600.00),
    ]
    cursor.executemany(
        """
        INSERT IGNORE INTO Doctors (doctor_id, employee_id, specialization, qualification, consultation_fee)
        VALUES (%s, %s, %s, %s, %s)
        """,
        extra_doctors
    )
    cursor.execute("UPDATE Doctors SET consultation_fee = 1500.00 WHERE doctor_id = 1")
    cursor.execute("UPDATE Doctors SET consultation_fee = 800.00 WHERE doctor_id = 2")
    cursor.execute("UPDATE Doctors SET consultation_fee = 1200.00 WHERE doctor_id = 3")
    cursor.execute("UPDATE Doctors SET consultation_fee = 1800.00 WHERE doctor_id = 4")
    cursor.execute("UPDATE Doctors SET consultation_fee = 900.00 WHERE doctor_id = 5")
    cursor.execute("UPDATE Doctors SET consultation_fee = 600.00 WHERE doctor_id = 6")

    cursor.executemany(
        """
        INSERT IGNORE INTO Rooms (room_id, room_number, room_type, daily_rate)
        VALUES (%s, %s, %s, %s)
        """,
        [
            (1, 'G-101', 'General Ward', 1500.00),
            (2, 'G-102', 'General Ward', 1500.00),
            (3, 'SP-201', 'Semi-Private', 3000.00),
            (4, 'P-301', 'Private', 5000.00),
            (5, 'ICU-1', 'ICU', 8000.00),
        ]
    )
    cursor.executemany(
        """
        INSERT IGNORE INTO Medicines (medicine_id, name, unit_price)
        VALUES (%s, %s, %s)
        """,
        [
            (1, 'Paracetamol 500mg', 20.00),
            (2, 'Amoxicillin 250mg', 80.00),
            (3, 'Ibuprofen 400mg', 35.00),
            (4, 'Aspirin 75mg', 25.00),
            (5, 'Cetirizine 10mg', 40.00),
            (6, 'Omeprazole 20mg', 55.00),
            (7, 'Insulin (vial)', 150.00),
            (8, 'Salbutamol Inhaler', 90.00),
        ]
    )

    extra_patients = [
        (5, 'Raj', 'Patel', 34, 74.00, '2026-09-26 09:00:00', 'Pending', 3, 3, 2),
        (6, 'Linda', 'Nguyen', 51, 66.40, '2026-09-26 10:30:00', 'Pending', 4, 3, 4),
        (7, 'Omar', 'Hassan', 22, 70.10, '2026-09-26 15:00:00', 'Pending', 5, 3, 1),
        (8, 'Grace', 'Kim', 40, 58.00, '2026-09-26 16:30:00', 'Pending', 6, 3, 3),
        (9, 'Anita', 'Singh', 55, 64.00, '2026-09-26 08:30:00', 'Pending', 1, 3, 4),
    ]
    cursor.executemany(
        """
        INSERT IGNORE INTO Patient
        (patient_id, first_name, last_name, age, weight_kg, appointment_time, status,
         assigned_doctor_id, registered_by_employee_id, room_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        extra_patients
    )
    # Give existing sample patients a room if they have none
    cursor.execute("UPDATE Patient SET room_id = 4 WHERE patient_id = 1 AND room_id IS NULL")
    cursor.execute("UPDATE Patient SET room_id = 1 WHERE patient_id = 2 AND room_id IS NULL")
    cursor.execute("UPDATE Patient SET room_id = 5 WHERE patient_id = 3 AND room_id IS NULL")
    cursor.execute("UPDATE Patient SET room_id = 3 WHERE patient_id = 4 AND room_id IS NULL")

    cursor.execute("SELECT COUNT(*) FROM Users WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO Users (username, password_hash, role, doctor_id) VALUES (%s, %s, %s, %s)",
            ('admin', generate_password_hash('admin123'), 'admin', None)
        )

    cursor.execute(
        """
        SELECT d.doctor_id, LOWER(CONCAT(LEFT(e.first_name, 1), e.last_name)) AS username
        FROM Doctors d
        JOIN Employee e ON d.employee_id = e.employee_id
        ORDER BY d.doctor_id
        """
    )
    doctor_rows = cursor.fetchall()
    doctor_pw = generate_password_hash('doctor123')
    for doctor_id, username in doctor_rows:
        cursor.execute("SELECT COUNT(*) FROM Users WHERE username = %s", (username,))
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO Users (username, password_hash, role, doctor_id) VALUES (%s, %s, %s, %s)",
                (username, doctor_pw, 'doctor', doctor_id)
            )

    conn.commit()
    cursor.close()
    conn.close()


try:
    init_db()
    print("Database connection successful!")
except mysql.connector.Error as err:
    print(f"Error: {err}")


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
        if not user:
            return jsonify({'error': 'Please log in'}), 401
        if user['role'] != 'admin':
            return jsonify({'error': 'Only the admin can perform this action'}), 403
        return fn(*args, **kwargs)
    return wrapper


def money(value):
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def parse_appointment_time(raw):
    appointment_time = (raw or '').replace('T', ' ')
    if len(appointment_time) == 16:
        appointment_time += ':00'
    return appointment_time


def patient_list_query(where_sql='', params=()):
    query = f"""
        SELECT
            p.patient_id,
            p.first_name,
            p.last_name,
            CONCAT(p.first_name, ' ', p.last_name) AS full_name,
            p.age,
            p.weight_kg,
            DATE_FORMAT(p.appointment_time, '%Y-%m-%d %H:%i') AS appointment_time,
            DATE(p.appointment_time) AS appointment_date,
            p.status,
            p.assigned_doctor_id,
            CONCAT('Dr. ', de.first_name, ' ', de.last_name) AS doctor_name,
            d.consultation_fee,
            p.registered_by_employee_id,
            CONCAT(re.first_name, ' ', re.last_name) AS registered_by_name,
            p.room_id,
            r.room_number,
            r.room_type,
            r.daily_rate AS room_rate
        FROM Patient p
        LEFT JOIN Doctors d ON p.assigned_doctor_id = d.doctor_id
        LEFT JOIN Employee de ON d.employee_id = de.employee_id
        LEFT JOIN Employee re ON p.registered_by_employee_id = re.employee_id
        LEFT JOIN Rooms r ON p.room_id = r.room_id
        {where_sql}
        ORDER BY p.appointment_time ASC, p.patient_id ASC
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
        if row.get('weight_kg') is not None:
            row['weight_kg'] = money(row['weight_kg'])
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
            rows = patient_list_query(
                'WHERE p.assigned_doctor_id = %s',
                (user['doctor_id'],)
            )
        else:
            rows = patient_list_query()
        return jsonify(rows)
    except Error as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/patients/today', methods=['GET'])
@login_required
def get_today_patients():
    try:
        user = current_user()
        if user['role'] != 'doctor':
            return jsonify({'error': 'Only doctor accounts can view this dashboard'}), 403
        rows = patient_list_query(
            """
            WHERE p.assigned_doctor_id = %s
              AND DATE(p.appointment_time) = CURDATE()
              AND p.status <> 'Cancelled'
            """,
            (user['doctor_id'],)
        )
        return jsonify({
            'count': len(rows),
            'doctor_name': user['display_name'],
            'patients': rows
        })
    except Error as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/patients', methods=['POST'])
@admin_required
def add_patient():
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()

        age = int(data['age']) if data.get('age') not in (None, '') else None
        weight_kg = float(data['weight_kg']) if data.get('weight_kg') not in (None, '') else None
        doc_id = int(data['assigned_doctor_id']) if data.get('assigned_doctor_id') not in (None, '') else None
        emp_id = int(data['registered_by_employee_id']) if data.get('registered_by_employee_id') not in (None, '') else None
        room_id = int(data['room_id']) if data.get('room_id') not in (None, '') else None
        status = data.get('status', 'Pending')
        appointment_time = parse_appointment_time(data.get('appointment_time'))

        query = """
            INSERT INTO Patient
            (first_name, last_name, age, weight_kg, appointment_time, status,
             assigned_doctor_id, registered_by_employee_id, room_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            data['first_name'], data['last_name'], age, weight_kg, appointment_time,
            status, doc_id, emp_id, room_id
        )
        cursor.execute(query, values)
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

        age = int(data['age']) if data.get('age') not in (None, '') else None
        weight_kg = float(data['weight_kg']) if data.get('weight_kg') not in (None, '') else None
        doc_id = int(data['assigned_doctor_id']) if data.get('assigned_doctor_id') not in (None, '') else None
        emp_id = int(data['registered_by_employee_id']) if data.get('registered_by_employee_id') not in (None, '') else None
        room_id = int(data['room_id']) if data.get('room_id') not in (None, '') else None
        status = data.get('status', 'Pending')
        appointment_time = parse_appointment_time(data.get('appointment_time'))

        query = """
            UPDATE Patient
            SET first_name = %s, last_name = %s, age = %s, weight_kg = %s,
                appointment_time = %s, status = %s, assigned_doctor_id = %s,
                registered_by_employee_id = %s, room_id = %s
            WHERE patient_id = %s
        """
        values = (
            data['first_name'], data['last_name'], age, weight_kg, appointment_time,
            status, doc_id, emp_id, room_id, patient_id
        )
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Patient updated successfully'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/patients/<int:patient_id>/cancel', methods=['PUT'])
@admin_required
def cancel_patient(patient_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "UPDATE Patient SET status = 'Cancelled' WHERE patient_id = %s"
        cursor.execute(query, (patient_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Appointment cancelled successfully'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/doctors', methods=['GET'])
@login_required
def get_doctors():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT
                d.doctor_id,
                d.employee_id,
                CONCAT('Dr. ', e.first_name, ' ', e.last_name) AS name,
                d.specialization,
                d.qualification,
                d.consultation_fee
            FROM Doctors d
            JOIN Employee e ON d.employee_id = e.employee_id
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


@app.route('/api/employees', methods=['GET'])
@login_required
def get_employees():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT employee_id, CONCAT(first_name, ' ', last_name) AS name, role, phone, email
            FROM Employee
            ORDER BY employee_id ASC
        """
        cursor.execute(query)
        employees = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(employees)
    except Error as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rooms', methods=['GET'])
@login_required
def get_rooms():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT room_id, room_number, room_type, daily_rate
            FROM Rooms
            ORDER BY room_id ASC
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
        cursor.execute(
            """
            SELECT medicine_id, name, unit_price
            FROM Medicines
            ORDER BY medicine_id ASC
            """
        )
        medicines = cursor.fetchall()
        cursor.close()
        conn.close()
        for med in medicines:
            med['unit_price'] = money(med.get('unit_price'))
        return jsonify(medicines)
    except Error as e:
        return jsonify({'error': str(e)}), 500


def fetch_patient_medicines(cursor, patient_id):
    cursor.execute(
        """
        SELECT pm.medicine_id, pm.quantity, m.name, m.unit_price
        FROM PatientMedicine pm
        JOIN Medicines m ON pm.medicine_id = m.medicine_id
        WHERE pm.patient_id = %s
        ORDER BY m.name
        """,
        (patient_id,)
    )
    items = cursor.fetchall()
    for item in items:
        item['unit_price'] = money(item.get('unit_price'))
        item['line_total'] = round(item['unit_price'] * int(item['quantity']), 2)
    return items


@app.route('/api/billing/<int:patient_id>', methods=['GET'])
@login_required
def get_billing(patient_id):
    try:
        user = current_user()
        rows = patient_list_query('WHERE p.patient_id = %s', (patient_id,))
        if not rows:
            return jsonify({'error': 'Patient not found'}), 404
        patient = rows[0]
        if user['role'] == 'doctor' and patient['assigned_doctor_id'] != user['doctor_id']:
            return jsonify({'error': 'You can only view bills for your own patients'}), 403

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        medicines = fetch_patient_medicines(cursor, patient_id)
        cursor.execute("SELECT * FROM Bills WHERE patient_id = %s", (patient_id,))
        bill = cursor.fetchone()
        cursor.close()
        conn.close()

        consultation = money(patient.get('consultation_fee'))
        room_charge = money(patient.get('room_rate'))
        medicine_charge = round(sum(item['line_total'] for item in medicines), 2)
        preview = {
            'consultation_fee': consultation,
            'room_charge': room_charge,
            'medicine_charge': medicine_charge,
            'total_amount': round(consultation + room_charge + medicine_charge, 2)
        }
        if bill:
            bill['consultation_fee'] = money(bill.get('consultation_fee'))
            bill['room_charge'] = money(bill.get('room_charge'))
            bill['medicine_charge'] = money(bill.get('medicine_charge'))
            bill['total_amount'] = money(bill.get('total_amount'))
            if bill.get('generated_at'):
                bill['generated_at'] = str(bill['generated_at'])

        return jsonify({
            'patient': patient,
            'medicines': medicines,
            'preview': preview,
            'bill': bill
        })
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
                b.bill_id,
                b.patient_id,
                CONCAT(p.first_name, ' ', p.last_name) AS patient_name,
                CONCAT('Dr. ', de.first_name, ' ', de.last_name) AS doctor_name,
                d.specialization,
                r.room_number,
                r.room_type,
                b.consultation_fee,
                b.room_charge,
                b.medicine_charge,
                b.total_amount,
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
        room_id = int(data['room_id']) if data.get('room_id') not in (None, '') else None
        medicines = data.get('medicines') or []

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT p.patient_id, p.assigned_doctor_id, d.consultation_fee
            FROM Patient p
            LEFT JOIN Doctors d ON p.assigned_doctor_id = d.doctor_id
            WHERE p.patient_id = %s
            """,
            (patient_id,)
        )
        patient = cursor.fetchone()
        if not patient:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Patient not found'}), 404

        consultation = money(patient.get('consultation_fee'))
        room_charge = 0.0
        if room_id:
            cursor.execute("SELECT daily_rate FROM Rooms WHERE room_id = %s", (room_id,))
            room = cursor.fetchone()
            if not room:
                cursor.close()
                conn.close()
                return jsonify({'error': 'Room not found'}), 400
            room_charge = money(room.get('daily_rate'))

        cursor.execute("UPDATE Patient SET room_id = %s WHERE patient_id = %s", (room_id, patient_id))
        cursor.execute("DELETE FROM PatientMedicine WHERE patient_id = %s", (patient_id,))

        medicine_charge = 0.0
        for item in medicines:
            medicine_id = item.get('medicine_id')
            quantity = int(item.get('quantity') or 0)
            if not medicine_id or quantity <= 0:
                continue
            cursor.execute("SELECT unit_price FROM Medicines WHERE medicine_id = %s", (medicine_id,))
            med = cursor.fetchone()
            if not med:
                continue
            cursor.execute(
                """
                INSERT INTO PatientMedicine (patient_id, medicine_id, quantity)
                VALUES (%s, %s, %s)
                """,
                (patient_id, medicine_id, quantity)
            )
            medicine_charge += money(med.get('unit_price')) * quantity

        medicine_charge = round(medicine_charge, 2)
        total = round(consultation + room_charge + medicine_charge, 2)

        cursor.execute(
            """
            INSERT INTO Bills (patient_id, consultation_fee, room_charge, medicine_charge, total_amount)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                consultation_fee = VALUES(consultation_fee),
                room_charge = VALUES(room_charge),
                medicine_charge = VALUES(medicine_charge),
                total_amount = VALUES(total_amount),
                generated_at = CURRENT_TIMESTAMP
            """,
            (patient_id, consultation, room_charge, medicine_charge, total)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({
            'message': 'Bill saved',
            'consultation_fee': consultation,
            'room_charge': room_charge,
            'medicine_charge': medicine_charge,
            'total_amount': total
        }), 201
    except Error as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
