import streamlit as st
import sqlite3
import hashlib
import random
import string
from PIL import Image
import io
import pandas as pd
from datetime import datetime, timedelta
from pyodbc import Error
from st_aggrid import AgGrid
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import textwrap
# ===== CONFIGURATION =====
PRESET_ADMIN = {
    "username": "admin",
    "password": "Admin@123"  # Change before deployment
}
DEFAULT_PASSWORD = "123"  # Default for both students and teachers
DEGREE_PROGRAMS = [
    "BS Computer Science",
    "BS Software Engineering", 
    "BS Data Science"
]

def show_success(message):
        st.markdown(f'<div class="success-message">{message}</div>', unsafe_allow_html=True)

def show_error(message):
        st.markdown(f'<div class="error-message">{message}</div>', unsafe_allow_html=True)

def show_warning(message):
        st.markdown(f'<div class="warning-message">{message}</div>', unsafe_allow_html=True)
# Add to the top of your code (after imports)
def set_custom_style():
    st.markdown("""
    <style>
        /* Main colors */
        :root {
            --primary: #4a6fa5;
            --secondary: #166088;
            --accent: #4fc3f7;
            --background: #f8f9fa;
            --text: #333333;
            --success: #28a745;
            --warning: #ffc107;
            --danger: #dc3545;
        }
        
        /* Main container */
        .main {
            background-color: var(--background);
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, var(--primary), var(--secondary));
            color: white;
        }
        
        /* Buttons */
        .stButton>button {
            border-radius: 8px;
            background-color: var(--primary);
            color: white;
            transition: all 0.3s;
        }
        
        .stButton>button:hover {
            background-color: var(--secondary);
            transform: scale(1.02);
        }
        
        /* Cards */
        .card {
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            padding: 1.5rem;
            background: white;
            margin-bottom: 1rem;
        }
        
        /* Inputs */
        .stTextInput>div>div>input, 
        .stNumberInput>div>div>input,
        .stTextArea>div>div>textarea {
            border-radius: 8px;
            border: 1px solid #ced4da;
        }
        
        /* Metrics */
        [data-testid="stMetric"] {
            background-color: white;
            border-radius: 10px;
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        /* Tabs */
        .stTabs [role="tablist"] {
            gap: 10px;
        }
        
        .stTabs [role="tab"] {
            border-radius: 8px 8px 0 0 !important;
            padding: 0.5rem 1rem;
            background-color: #e9ecef;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: var(--primary) !important;
            color: white !important;
        }
    </style>
    """, unsafe_allow_html=True)
# ===== DATABASE FUNCTIONS =====
def connect_db():
    try:
        conn = sqlite3.connect("lms.db")
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None
def init_db():
    conn = connect_db()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        # ADMIN TABLE
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # TEACHERS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            must_change_pass INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # STUDENTS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnic TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            age INTEGER NOT NULL,
            degree TEXT NOT NULL,
            fee REAL NOT NULL,
            father_name TEXT NOT NULL,
            profile_pic BLOB,
            student_id TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            must_change_pass INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # CLASSES
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code TEXT NOT NULL,
            course_name TEXT NOT NULL,
            schedule TEXT NOT NULL,
            instructor_id TEXT NOT NULL,
            degree_program TEXT NOT NULL
        )
        """)

        # ATTENDANCE
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_cnic TEXT NOT NULL,
            class_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT CHECK(status IN ('Present','Absent')),
            UNIQUE(student_cnic, class_id, date)
        )
        """)

        # GRADES
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_cnic TEXT NOT NULL,
            class_id INTEGER NOT NULL,
            grade_point REAL NOT NULL,
            remarks TEXT,
            assigned_by TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            semester TEXT DEFAULT 'Fall 2023'
        )
        """)

        # INVOICES
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_cnic TEXT NOT NULL,
            amount REAL NOT NULL,
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            status TEXT DEFAULT 'Unpaid'
        )
        """)

        # ASSIGNMENTS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            total_marks REAL NOT NULL,
            due_date TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # ASSIGNMENT GRADES
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignment_grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            student_cnic TEXT NOT NULL,
            obtained_marks REAL NOT NULL,
            feedback TEXT,
            submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
            graded_by TEXT NOT NULL
        )
        """)

        # EXAMS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            exam_type TEXT NOT NULL,
            title TEXT NOT NULL,
            total_marks REAL NOT NULL,
            exam_date TEXT NOT NULL,
            weightage REAL NOT NULL
        )
        """)

        # EXAM GRADES
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS exam_grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            student_cnic TEXT NOT NULL,
            obtained_marks REAL NOT NULL,
            graded_by TEXT NOT NULL
        )
        """)

        # PAYMENTS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_date TEXT DEFAULT CURRENT_TIMESTAMP,
            payment_method TEXT,
            transaction_id TEXT,
            received_by TEXT
        )
        """)

        # SUBMISSIONS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignment_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            student_cnic TEXT NOT NULL,
            submission_file BLOB NOT NULL,
            file_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            submitted_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # ADMIN INSERT
        cursor.execute("""
        INSERT OR IGNORE INTO admins (username, password_hash)
        VALUES (?, ?)
        """, (
            PRESET_ADMIN["username"],
            hash_password(PRESET_ADMIN["password"])
        ))

        conn.commit()
        return True

    except Exception as e:
        st.error(f"Database Initialization Failed: {e}")
        return False

    finally:
        conn.close()
# ===== UTILITY FUNCTIONS =====
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_student_id(degree_program):
    conn = connect_db()
    if not conn:
        return None

    try:
        cursor = conn.cursor()

        # Degree mapping
        degree_map = {
            "BS Computer Science": "CS",
            "BS Software Engineering": "SE",
            "BS Data Science": "DS"
        }

        prefix = degree_map.get(degree_program, "XX")

        # SQLite query (LIMIT instead of TOP)
        cursor.execute("""
            SELECT student_id 
            FROM students 
            WHERE student_id LIKE ?
            ORDER BY id DESC
            LIMIT 1
        """, (prefix + "%",))

        result = cursor.fetchone()

        if result:
            last_id = result[0]  # e.g. CS005

            try:
                number = int(last_id[len(prefix):])
                new_number = number + 1
            except:
                new_number = 1
        else:
            new_number = 1

        return f"{prefix}{str(new_number).zfill(3)}"

    except Exception as e:
        st.error(f"Error generating student ID: {e}")
        return None

    finally:
        conn.close()
def generate_teacher_id():
    conn = connect_db()
    if not conn:
        return None

    try:
        cursor = conn.cursor()

        # SQLite version (LIMIT instead of TOP)
        cursor.execute("""
            SELECT teacher_id 
            FROM teachers 
            ORDER BY id DESC 
            LIMIT 1
        """)
        result = cursor.fetchone()

        if result:
            last_id = result[0]   # e.g. T005

            try:
                number = int(last_id[1:])  # remove 'T'
                new_id = f"T{str(number + 1).zfill(3)}"
            except:
                new_id = "T001"
        else:
            new_id = "T001"

        return new_id

    except Exception as e:
        st.error(f"Error generating teacher ID: {e}")
        return "T001"

    finally:
        conn.close()

def parse_schedule_days(schedule):
    """Extract weekdays from schedule string (e.g., 'Mon/Wed 9-10:30' -> [0, 2])"""
    day_map = {
        'mon': 0, 'tue': 1, 'wed': 2, 
        'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6
    }
    try:
        days_part = schedule.split()[0].lower()
        days = []
        
        for day in days_part.split('/'):
            day = day[:3]  # Get first 3 letters
            if day in day_map:
                days.append(day_map[day])
        
        return days
    except:
        return []

# ===== AUTHENTICATION FUNCTIONS =====
def admin_login(username, password):
    conn = connect_db()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        # Check preset admin credentials first
        if username == PRESET_ADMIN["username"] and password == PRESET_ADMIN["password"]:
            return {"username": username, "password_hash": hash_password(password)}
        
        # Check database
        cursor.execute("""
            SELECT * FROM admins 
            WHERE username = ? AND password_hash = ?
        """, (username, hash_password(password)))
        
        columns = [column[0] for column in cursor.description]
        admin = cursor.fetchone()
        if admin:
            return dict(zip(columns, admin))
        return None
    except Exception as e:
        st.error(f"🔴 Login Error: {e}")
        return None
    finally:
        conn.close()

def teacher_login(teacher_id, password):
    conn = connect_db()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM teachers 
            WHERE teacher_id = ? AND password_hash = ?
        """, (teacher_id, hash_password(password)))
        
        columns = [column[0] for column in cursor.description]
        teacher = cursor.fetchone()
        if teacher:
            teacher_dict = dict(zip(columns, teacher))
            if teacher_dict['must_change_pass'] and password == DEFAULT_PASSWORD:
                st.warning("⚠️ Please change your default password")
            return teacher_dict
        return None
    except Exception as e:
        st.error(f"🔴 Login Error: {e}")
        return None
    finally:
        conn.close()

def student_login(student_id, password):
    conn = connect_db()
    if not conn:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM students 
            WHERE student_id = ? AND password_hash = ?
        """, (student_id, hash_password(password)))

        columns = [column[0] for column in cursor.description]
        student = cursor.fetchone()
        if student:
            student_dict = dict(zip(columns, student))
            if student_dict['must_change_pass'] and password == DEFAULT_PASSWORD:
                st.warning("⚠️ Please change your default password")
            return student_dict
        return None
    except Exception as e:
        st.error(f"🔴 Login Error: {e}")
        return None
    finally:
        conn.close()


def update_password(table, id_field, id_value, new_password):
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            UPDATE {table} 
            SET password_hash = ?, must_change_pass = 0
            WHERE {id_field} = ?
        """, (hash_password(new_password), id_value))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        st.error(f"🔴 Password Update Failed: {e}")
        return False
    finally:
        conn.close()

# ===== ADMIN FUNCTIONS =====
def add_teacher(name, email):
    conn = connect_db()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        teacher_id = generate_teacher_id()
        
        cursor.execute("""
            INSERT INTO teachers (
                teacher_id, full_name, email, password_hash
            ) VALUES (?, ?, ?, ?)
        """, (teacher_id, name, email, hash_password(DEFAULT_PASSWORD)))
        
        conn.commit()
        return teacher_id
    except Exception as e:
        if "Violation of UNIQUE KEY constraint" in str(e):
            st.error("Teacher with this email already exists")
        else:
            st.error(f"🔴 Teacher Addition Failed: {e}")
        return None
    finally:
        conn.close()

def remove_teacher(teacher_id):
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM teachers WHERE teacher_id = ?", (teacher_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        st.error(f"🔴 Teacher Removal Failed: {e}")
        return False
    finally:
        conn.close()

def get_teachers():
    conn = connect_db()
    if not conn:
        return []

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT teacher_id, full_name, email, created_at
            FROM teachers
            ORDER BY id DESC
        """)

        columns = [column[0] for column in cursor.description]

        results = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

        return results

    except Exception as e:
        st.error(f"Failed to Fetch Teachers: {e}")
        return []

    finally:
        conn.close()
        
def update_teacher(teacher_id, name=None, email=None):
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Build dynamic update query
        update_fields = []
        params = []
        
        if name is not None:
            update_fields.append("full_name = ?")
            params.append(name)
        if email is not None:
            update_fields.append("email = ?")
            params.append(email)
        
        if not update_fields:
            return False  # Nothing to update
            
        query = f"""
            UPDATE teachers
            SET {', '.join(update_fields)}
            WHERE teacher_id = ?
        """
        params.append(teacher_id)
        
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        st.error(f"🔴 Teacher Update Failed: {e}")
        return False
    finally:
        conn.close()
def add_student(cnic, name, age, degree, fee, father, image=None):
    conn = connect_db()
    if not conn:
        return None

    try:
        cursor = conn.cursor()
        student_id = generate_student_id(degree)  # Use new student ID logic

        # Handle image upload
        pic_data = image.read() if image else None

        cursor.execute("""
            INSERT INTO students (
                cnic, full_name, age, degree, fee, 
                father_name, profile_pic, student_id, password_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cnic, name, age, degree, fee, 
            father, pic_data, student_id, hash_password(DEFAULT_PASSWORD)
        ))

        # Generate initial invoice
        due_date = datetime.now() + timedelta(days=30)
        cursor.execute("""
            INSERT INTO invoices (
                student_cnic, amount, issue_date, due_date
            ) VALUES (?, ?, ?, ?)
        """, (cnic, fee, datetime.now().date(), due_date.date()))

        conn.commit()
        return student_id  # Return student_id instead of username
    except Exception as e:
        if "Violation of UNIQUE KEY constraint" in str(e):
            st.error("Student with this CNIC or student ID already exists")
        else:
            st.error(f"🔴 Student Addition Failed: {e}")
        return None
    finally:
        conn.close()


def remove_student(cnic):
    conn = connect_db()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        # First delete invoices (and optionally other related records)
        cursor.execute("DELETE FROM invoices WHERE student_cnic = ?", (cnic,))

        # Then delete the student
        cursor.execute("DELETE FROM students WHERE cnic = ?", (cnic,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        st.error(f"🔴 Student Removal Failed: {e}")
        return False
    finally:
        conn.close()

def update_student(cnic, name=None, age=None, degree=None, fee=None, father=None, image=None):
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Build dynamic update query based on provided fields
        update_fields = []
        params = []
        
        if name is not None:
            update_fields.append("full_name = ?")
            params.append(name)
        if age is not None:
            update_fields.append("age = ?")
            params.append(age)
        if degree is not None:
            update_fields.append("degree = ?")
            params.append(degree)
        if fee is not None:
            update_fields.append("fee = ?")
            params.append(fee)
        if father is not None:
            update_fields.append("father_name = ?")
            params.append(father)
        if image is not None:
            update_fields.append("profile_pic = ?")
            params.append(image.read())
        
        if not update_fields:
            return False  # Nothing to update
            
        query = f"""
            UPDATE students
            SET {', '.join(update_fields)}
            WHERE cnic = ?
        """
        params.append(cnic)
        
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        st.error(f"🔴 Student Update Failed: {e}")
        return False
    finally:
        conn.close()
def get_students():
    conn = connect_db()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cnic, full_name, age, degree, fee, 
                   father_name,student_id, created_at,id
            FROM students
            ORDER BY created_at DESC
        """)
        
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
    except Exception as e:
        st.error(f"🔴 Failed to Fetch Students: {e}")
        return []
    finally:
        conn.close()
def validate_cnic(cnic):
    """
    Validates a CNIC number:
    - Must be exactly 13 digits
    - Must contain only numbers
    - Should not contain dashes or spaces
    """
    if not cnic.isdigit():
        return False
    if len(cnic) != 13:
        return False
    return True
def add_class(course_code, course_name, schedule, instructor_id, degree):
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO classes (
                course_code, course_name, schedule, instructor_id, degree_program
            ) VALUES (?, ?, ?, ?, ?)
        """, (course_code, course_name, schedule, instructor_id, degree))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"🔴 Class Addition Failed: {e}")
        return False
    finally:
        conn.close()

def get_classes():
    conn = connect_db()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.course_code, c.course_name, c.schedule, 
                   t.full_name as instructor, c.degree_program
            FROM classes c
            JOIN teachers t ON c.instructor_id = t.teacher_id
            ORDER BY c.course_code
        """)
        
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
    except Exception as e:
        st.error(f"🔴 Failed to Fetch Classes: {e}")
        return []
    finally:
        conn.close()
def update_class(class_id, course_code=None, course_name=None, schedule=None, instructor_id=None, degree_program=None):
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Build dynamic update query
        update_fields = []
        params = []
        
        if course_code is not None:
            update_fields.append("course_code = ?")
            params.append(course_code)
        if course_name is not None:
            update_fields.append("course_name = ?")
            params.append(course_name)
        if schedule is not None:
            update_fields.append("schedule = ?")
            params.append(schedule)
        if instructor_id is not None:
            update_fields.append("instructor_id = ?")
            params.append(instructor_id)
        if degree_program is not None:
            update_fields.append("degree_program = ?")
            params.append(degree_program)
        
        if not update_fields:
            return False  # Nothing to update
            
        query = f"""
            UPDATE classes
            SET {', '.join(update_fields)}
            WHERE id = ?
        """
        params.append(class_id)
        
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        st.error(f"🔴 Class Update Failed: {e}")
        return False
    finally:
        conn.close()
def remove_class(class_id):
    """Remove class from database"""
    try:
        # Your database removal logic here
        # Handle any foreign key constraints
        return True  # if successful
    except Exception as e:
        st.error(f"Error removing class: {e}")
        return False
# ===== TEACHER FUNCTIONS =====
def mark_attendance(class_id, student_cnic, date, status):
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        # Check if attendance already exists
        cursor.execute("""
            SELECT 1 FROM attendance 
            WHERE class_id = ? AND student_cnic = ? AND date = ?
        """, (class_id, student_cnic, date))
        
        if cursor.fetchone():
            # Update existing record
            cursor.execute("""
                UPDATE attendance SET status = ?
                WHERE class_id = ? AND student_cnic = ? AND date = ?
            """, (status, class_id, student_cnic, date))
        else:
            # Insert new record
            cursor.execute("""
                INSERT INTO attendance (
                    class_id, student_cnic, date, status
                ) VALUES (?, ?, ?, ?)
            """, (class_id, student_cnic, date, status))
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"🔴 Attendance Marking Failed: {e}")
        return False
    finally:
        conn.close()

def assign_grade(student_cnic, class_id, grade_point, remarks, teacher_id):
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        # Check if grade already exists
        cursor.execute("""
            SELECT 1 FROM grades 
            WHERE student_cnic = ? AND class_id = ?
        """, (student_cnic, class_id))
        
        if cursor.fetchone():
            # Update existing record
            cursor.execute("""
                UPDATE grades SET 
                    grade_point = ?,
                    remarks = ?,
                    assigned_by = ?
                WHERE student_cnic = ? AND class_id = ?
            """, (grade_point, remarks, teacher_id, student_cnic, class_id))
        else:
            # Insert new record
            cursor.execute("""
                INSERT INTO grades (
                    student_cnic, class_id, grade_point, remarks, assigned_by
                ) VALUES (?, ?, ?, ?, ?)
            """, (student_cnic, class_id, grade_point, remarks, teacher_id))
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"🔴 Grade Assignment Failed: {e}")
        return False
    finally:
        conn.close()

def get_class_students(class_id):
    conn = connect_db()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.cnic, s.full_name
            FROM students s
            JOIN classes c ON s.degree = c.degree_program
            WHERE c.id = ?
            ORDER BY s.full_name
        """, (class_id,))
        
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
    except Exception as e:
        st.error(f"🔴 Failed to Fetch Class Students: {e}")
        return []
    finally:
        conn.close()

def get_teacher_classes(teacher_id):
    conn = connect_db()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, course_code, course_name, schedule, degree_program
            FROM classes
            WHERE instructor_id = ?
            ORDER BY course_code
        """, (teacher_id,))
        
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
    except Exception as e:
        st.error(f"🔴 Failed to Fetch Teacher Classes: {e}")
        return []
    finally:
        conn.close()

def get_student_grades(class_id):
    conn = connect_db()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT g.student_cnic, s.full_name, g.grade_point, g.remarks
            FROM grades g
            JOIN students s ON g.student_cnic = s.cnic
            WHERE g.class_id = ?
            ORDER BY s.full_name
        """, (class_id,))
        
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
    except Exception as e:
        st.error(f"🔴 Failed to Fetch Student Grades: {e}")
        return []
    finally:
        conn.close()

# ===== TEACHER GRADEBOOK FUNCTIONS =====
def create_assignment(class_id, title, description, total_marks, due_date):
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO assignments (
                class_id, title, description, total_marks, due_date
            ) VALUES (?, ?, ?, ?, ?)
        """, (class_id, title, description, total_marks, due_date))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"🔴 Assignment Creation Failed: {e}")
        return False
    finally:
        conn.close()

def create_exam(class_id, exam_type, title, total_marks, exam_date, weightage):
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO exams (
                class_id, exam_type, title, total_marks, exam_date, weightage
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (class_id, exam_type, title, total_marks, exam_date, weightage))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"🔴 Exam Creation Failed: {e}")
        return False
    finally:
        conn.close()

def get_class_assignments(class_id):
    conn = connect_db()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, description, total_marks, due_date
            FROM assignments
            WHERE class_id = ?
            ORDER BY due_date
        """, (class_id,))
        
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
    except Exception as e:
        st.error(f"🔴 Failed to Fetch Assignments: {e}")
        return []
    finally:
        conn.close()

def get_class_exams(class_id):
    conn = connect_db()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, exam_type, title, total_marks, exam_date, weightage
            FROM exams
            WHERE class_id = ?
            ORDER BY exam_date
        """, (class_id,))
        
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
    except Exception as e:
        st.error(f"🔴 Failed to Fetch Exams: {e}")
        return []
    finally:
        conn.close()
def generate_invoice_pdf(invoice_data, student_data):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Set up styles
    c.setFont("Helvetica-Bold", 16)
    
    # Header
    c.drawString(100, height - 100, "EDUVATE UNIVERSITY")
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 120, "123 Education Street, Learning City")
    c.drawString(100, height - 140, "Phone: (123) 456-7890 | Email: info@eduvate.edu")
    
    # Invoice title
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width/2, height - 180, "FEE INVOICE")
    
    # Invoice details
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 220, f"Invoice #: {invoice_data['id']}")
    c.drawString(100, height - 240, f"Date Issued: {invoice_data['issue_date']}")
    c.drawString(100, height - 260, f"Due Date: {invoice_data['due_date']}")
    
    # Student info
    c.drawString(350, height - 220, f"Student ID: {student_data['student_id']}")
    c.drawString(350, height - 240, f"Student Name: {student_data['full_name']}")
    c.drawString(350, height - 260, f"Degree Program: {student_data['degree']}")
    
    # Line separator
    c.line(100, height - 280, width - 100, height - 280)
    
    # Invoice items
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, height - 310, "Description")
    c.drawString(400, height - 310, "Amount")
    
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 340, f"Tuition Fee for {student_data['degree']}")
    c.drawString(400, height - 340, f"Rs. {invoice_data['amount']:,.2f}")
    
    # Total
    c.setFont("Helvetica-Bold", 14)
    c.drawString(400, height - 380, f"Total: Rs. {invoice_data['amount']:,.2f}")
    
    # Payment status
    status_y = height - 420
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, status_y, "Payment Status:")
    c.setFont("Helvetica", 12)
    if invoice_data['status'] == "Paid":
        c.drawString(200, status_y, "PAID")
    else:
        c.drawString(200, status_y, "PENDING")
    
    # Footer
    c.setFont("Helvetica", 10)
    footer_text = "Please make payments by the due date to avoid late fees. Payments can be made at the university cashier or through bank transfer to Account #123456789."
    for i, line in enumerate(textwrap.wrap(footer_text, width=100)):
        c.drawString(100, height - 470 - (i * 15), line)
    
    # University stamp
    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(width/2, 100, "Official Invoice - Eduvate University")
    
    c.save()
    buffer.seek(0)
    return buffer
def submit_assignment_grade(assignment_id, student_cnic, obtained_marks, feedback, graded_by):
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        # Check if grade already exists
        cursor.execute("""
            SELECT 1 FROM assignment_grades 
            WHERE assignment_id = ? AND student_cnic = ?
        """, (assignment_id, student_cnic))
        
        if cursor.fetchone():
            # Update existing record
            cursor.execute("""
                UPDATE assignment_grades SET 
                    obtained_marks = ?,
                    feedback = ?,
                    graded_by = ?
                WHERE assignment_id = ? AND student_cnic = ?
            """, (obtained_marks, feedback, graded_by, assignment_id, student_cnic))
        else:
            # Insert new record
            cursor.execute("""
                INSERT INTO assignment_grades (
                    assignment_id, student_cnic, obtained_marks, feedback, graded_by
                ) VALUES (?, ?, ?, ?, ?)
            """, (assignment_id, student_cnic, obtained_marks, feedback, graded_by))
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"🔴 Assignment Grade Submission Failed: {e}")
        return False
    finally:
        conn.close()

def submit_exam_grade(exam_id, student_cnic, obtained_marks, graded_by):
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        # Check if grade already exists
        cursor.execute("""
            SELECT 1 FROM exam_grades 
            WHERE exam_id = ? AND student_cnic = ?
        """, (exam_id, student_cnic))
        
        if cursor.fetchone():
            # Update existing record
            cursor.execute("""
                UPDATE exam_grades SET 
                    obtained_marks = ?,
                    graded_by = ?
                WHERE exam_id = ? AND student_cnic = ?
            """, (obtained_marks, graded_by, exam_id, student_cnic))
        else:
            # Insert new record
            cursor.execute("""
                INSERT INTO exam_grades (
                    exam_id, student_cnic, obtained_marks, graded_by
                ) VALUES (?, ?, ?, ?)
            """, (exam_id, student_cnic, obtained_marks, graded_by))
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"🔴 Exam Grade Submission Failed: {e}")
        return False
    finally:
        conn.close()
def get_assignment_grade(assignment_id, student_cnic):
    conn = connect_db()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT obtained_marks, feedback
            FROM assignment_grades
            WHERE assignment_id = ? AND student_cnic = ?
        """, (assignment_id, student_cnic))
        
        result = cursor.fetchone()
        if result:
            return {
                'obtained_marks': result[0],
                'feedback': result[1]
            }
        return None
    except Exception as e:
        st.error(f"🔴 Failed to Fetch Assignment Grade: {e}")
        return None
    finally:
        conn.close()
def get_student_assignment_grades(student_cnic, class_id=None):
    conn = connect_db()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        if class_id:
            cursor.execute("""
                SELECT a.id, a.title, a.total_marks, ag.obtained_marks, 
                       ag.feedback, c.course_code, c.course_name, CAST(a.due_date AS DATE) as due_date
                FROM assignments a
                LEFT JOIN assignment_grades ag ON a.id = ag.assignment_id AND ag.student_cnic = ?
                JOIN classes c ON a.class_id = c.id
                WHERE a.class_id = ?
                ORDER BY a.due_date
            """, (student_cnic, class_id))
        else:
            cursor.execute("""
                SELECT a.id, a.title, a.total_marks, ag.obtained_marks, 
                       ag.feedback, c.course_code, c.course_name, CAST(a.due_date AS DATE) as due_date
                FROM assignments a
                LEFT JOIN assignment_grades ag ON a.id = ag.assignment_id AND ag.student_cnic = ?
                JOIN classes c ON a.class_id = c.id
                JOIN students s ON s.cnic = ?
                WHERE c.degree_program = s.degree
                ORDER BY a.due_date
            """, (student_cnic, student_cnic))
        
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
    except Exception as e:
        st.error(f"🔴 Failed to Fetch Assignment Grades: {e}")
        return []
    finally:
        conn.close()

def get_student_exam_grades(student_cnic, class_id=None):
    conn = connect_db()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        if class_id:
            cursor.execute("""
                SELECT e.id, e.exam_type, e.title, e.total_marks, e.weightage,
                       eg.obtained_marks, c.course_code, c.course_name, e.exam_date
                FROM exams e
                LEFT JOIN exam_grades eg ON e.id = eg.exam_id AND eg.student_cnic = ?
                JOIN classes c ON e.class_id = c.id
                WHERE e.class_id = ?
                ORDER BY e.exam_date
            """, (student_cnic, class_id))
        else:
            cursor.execute("""
                SELECT e.id, e.exam_type, e.title, e.total_marks, e.weightage,
                       eg.obtained_marks, c.course_code, c.course_name, e.exam_date
                FROM exams e
                LEFT JOIN exam_grades eg ON e.id = eg.exam_id AND eg.student_cnic = ?
                JOIN classes c ON e.class_id = c.id
                JOIN students s ON s.cnic = ?
                WHERE c.degree_program = s.degree
                ORDER BY e.exam_date
            """, (student_cnic, student_cnic))
        
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
    except Exception as e:
        st.error(f"🔴 Failed to Fetch Exam Grades: {e}")
        return []
    finally:
        conn.close()

def calculate_course_grade(student_cnic, class_id):
    conn = connect_db()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        # Get all assignments with grades
        cursor.execute("""
            SELECT a.total_marks, ag.obtained_marks
            FROM assignments a
            JOIN assignment_grades ag ON a.id = ag.assignment_id
            WHERE ag.student_cnic = ? AND a.class_id = ?
        """, (student_cnic, class_id))
        
        assignment_scores = cursor.fetchall()
        
        # Get all exams with grades
        cursor.execute("""
            SELECT e.exam_type, e.total_marks, e.weightage, eg.obtained_marks
            FROM exams e
            JOIN exam_grades eg ON e.id = eg.exam_id
            WHERE eg.student_cnic = ? AND e.class_id = ?
        """, (student_cnic, class_id))
        
        exam_scores = cursor.fetchall()
        
        # Calculate weighted average
        total_score = 0
        total_weight = 0
        
        # Process assignments (assuming equal weight)
        if assignment_scores:
            assignment_avg = sum(og/total for total, og in assignment_scores if og is not None) / len(assignment_scores)
            total_score += assignment_avg * 0.4  # Assignments weight 40%
            total_weight += 0.4
        
        # Process exams
        exam_contribution = 0
        for exam_type, total, weight, obtained in exam_scores:
            if obtained is not None and total > 0:
                exam_contribution += (obtained / total) * (weight / 100)
        
        total_score += exam_contribution * 0.6  # Exams weight 60%
        total_weight += 0.6
        
        if total_weight == 0:
            return None
        
        final_percentage = (total_score / total_weight) * 100
        
        # Convert to grade point (4.0 scale)
        if final_percentage >= 85:
            return 4.0
        elif final_percentage >= 80:
            return 3.7
        elif final_percentage >= 75:
            return 3.3
        elif final_percentage >= 70:
            return 3.0
        elif final_percentage >= 65:
            return 2.7
        elif final_percentage >= 60:
            return 2.3
        elif final_percentage >= 55:
            return 2.0
        elif final_percentage >= 50:
            return 1.7
        elif final_percentage >= 45:
            return 1.3
        elif final_percentage >= 40:
            return 1.0
        else:
            return 0.0
            
    except Exception as e:
        st.error(f"🔴 Grade Calculation Failed: {e}")
        return None
    finally:
        conn.close()

# ===== STUDENT FUNCTIONS =====
def get_student_attendance(cnic):
    conn = connect_db()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.course_code, c.course_name, a.date, a.status
            FROM attendance a
            JOIN classes c ON a.class_id = c.id
            WHERE a.student_cnic = ?
            ORDER BY a.date DESC
        """, (cnic,))
        
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
    except Exception as e:
        st.error(f"🔴 Attendance Fetch Failed: {e}")
        return []
    finally:
        conn.close()

def get_student_attendance_by_class(cnic, course_code):
    conn = connect_db()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.date, a.status, c.course_name
            FROM attendance a
            JOIN classes c ON a.class_id = c.id
            WHERE a.student_cnic = ? AND c.course_code = ?
            ORDER BY a.date DESC
        """, (cnic, course_code))
        
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
    except Exception as e:
        st.error(f"🔴 Attendance Fetch Failed: {e}")
        return []
    finally:
        conn.close()

def get_student_classes(degree):
    conn = connect_db()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT course_code, course_name, schedule, instructor_id
            FROM classes
            WHERE degree_program = ?
            ORDER BY course_code
        """, (degree,))
        
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
    except Exception as e:
        st.error(f"🔴 Failed to Fetch Student Classes: {e}")
        return []
    finally:
        conn.close()

def get_student_invoices(cnic):
    conn = connect_db()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, amount, issue_date, due_date, status
            FROM invoices
            WHERE student_cnic = ?
            ORDER BY due_date DESC
        """, (cnic,))
        
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
    except Exception as e:
        st.error(f"🔴 Invoice Fetch Failed: {e}")
        return []
    finally:
        conn.close()

def get_student_grades_report(cnic):
    conn = connect_db()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.course_code, c.course_name, g.grade_point, g.remarks, 
                   t.full_name as instructor
            FROM grades g
            JOIN classes c ON g.class_id = c.id
            JOIN teachers t ON g.assigned_by = t.teacher_id
            WHERE g.student_cnic = ?
            ORDER BY c.course_code
        """, (cnic,))
        
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
    except Exception as e:
        st.error(f"🔴 Grades Fetch Failed: {e}")
        return []
    finally:
        conn.close()

# ===== FEE MANAGEMENT FUNCTIONS =====
def record_payment(invoice_id, amount, payment_method, transaction_id, received_by):
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO payments (
                invoice_id, amount, payment_method, transaction_id, received_by
            ) VALUES (?, ?, ?, ?, ?)
        """, (invoice_id, amount, payment_method, transaction_id, received_by))
        
        # Update invoice status if fully paid
        cursor.execute("""
            UPDATE invoices
            SET status = CASE 
                WHEN amount <= (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE invoice_id = ?)
                THEN 'Paid' ELSE 'Unpaid' END
            WHERE id = ?
        """, (invoice_id, invoice_id))
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"🔴 Payment Recording Failed: {e}")
        return False
    finally:
        conn.close()

def get_invoice_payments(invoice_id):
    conn = connect_db()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT amount, payment_date, payment_method, transaction_id, received_by
            FROM payments
            WHERE invoice_id = ?
            ORDER BY payment_date DESC
        """, (invoice_id,))
        
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
    except Exception as e:
        st.error(f"🔴 Failed to Fetch Payments: {e}")
        return []
    finally:
        conn.close()

def generate_fee_invoice(student_cnic, amount, due_days=30):
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        due_date = datetime.now() + timedelta(days=due_days)
        cursor.execute("""
            INSERT INTO invoices (
                student_cnic, amount, issue_date, due_date
            ) VALUES (?, ?, ?, ?)
        """, (student_cnic, amount, datetime.now().date(), due_date.date()))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"🔴 Invoice Generation Failed: {e}")
        return False
    finally:
        conn.close()

def get_overdue_invoices():
    conn = connect_db()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.id, s.full_name, s.cnic, i.amount, i.due_date,
                   (i.amount - COALESCE(SUM(p.amount), 0)) as remaining
            FROM invoices i
            JOIN students s ON i.student_cnic = s.cnic
            LEFT JOIN payments p ON p.invoice_id = i.id
            WHERE i.due_date < CAST(GETDATE() AS DATE) AND i.status = 'Unpaid'
            GROUP BY i.id, s.full_name, s.cnic, i.amount, i.due_date
            HAVING i.amount > COALESCE(SUM(p.amount), 0)
            ORDER BY i.due_date
        """)
        
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
    except Exception as e:
        st.error(f"🔴 Failed to Fetch Overdue Invoices: {e}")
        return []
    finally:
        conn.close()
def update_invoice(invoice_id, amount=None, due_date=None):
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Build dynamic update query
        update_fields = []
        params = []
        
        if amount is not None:
            update_fields.append("amount = ?")
            params.append(amount)
        if due_date is not None:
            update_fields.append("due_date = ?")
            params.append(due_date)
        
        if not update_fields:
            return False  # Nothing to update
            
        query = f"""
            UPDATE invoices
            SET {', '.join(update_fields)}
            WHERE id = ?
        """
        params.append(invoice_id)
        
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        st.error(f"🔴 Invoice Update Failed: {e}")
        return False
    finally:
        conn.close()
        
def submit_assignment(assignment_id, student_cnic, file_data, file_name, file_type):
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Check if student already submitted
        cursor.execute("""
            SELECT 1 FROM assignment_submissions 
            WHERE assignment_id = ? AND student_cnic = ?
        """, (assignment_id, student_cnic))
        
        if cursor.fetchone():
            # Update existing submission
            cursor.execute("""
                UPDATE assignment_submissions SET 
                    submission_file = ?,
                    file_name = ?,
                    file_type = ?,
                    submitted_at = CURRENT_TIMESTAMP
                WHERE assignment_id = ? AND student_cnic = ?
            """, (file_data, file_name, file_type, assignment_id, student_cnic))
        else:
            # Insert new submission
            cursor.execute("""
                INSERT INTO assignment_submissions (
                    assignment_id, student_cnic, submission_file, file_name, file_type
                ) VALUES (?, ?, ?, ?, ?)
            """, (assignment_id, student_cnic, file_data, file_name, file_type))
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"🔴 Assignment Submission Failed: {e}")
        return False
    finally:
        conn.close()

def get_student_assignment_submission(assignment_id, student_cnic):
    conn = connect_db()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT submission_file, file_name, file_type, submitted_at
            FROM assignment_submissions
            WHERE assignment_id = ? AND student_cnic = ?
        """, (assignment_id, student_cnic))
        
        columns = [column[0] for column in cursor.description]
        result = cursor.fetchone()
        if result:
            return dict(zip(columns, result))
        return None
    except Exception as e:
        st.error(f"🔴 Failed to Fetch Submission: {e}")
        return None
    finally:
        conn.close()
def get_assignment_submissions(assignment_id):
    conn = connect_db()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.id, s.student_cnic, st.full_name, s.file_name, s.file_type, s.submitted_at
            FROM assignment_submissions s
            JOIN students st ON s.student_cnic = st.cnic
            WHERE s.assignment_id = ?
            ORDER BY s.submitted_at DESC
        """, (assignment_id,))
        
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
    except Exception as e:
        st.error(f"🔴 Failed to Fetch Submissions: {e}")
        return []
    finally:
        conn.close()

def get_submission_file(submission_id):
    conn = connect_db()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT submission_file, file_name, file_type
            FROM assignment_submissions
            WHERE id = ?
        """, (submission_id,))
        
        result = cursor.fetchone()
        if result:
            return {
                'file_data': result[0],
                'file_name': result[1],
                'file_type': result[2]
            }
        return None
    except Exception as e:
        st.error(f"🔴 Failed to Fetch Submission File: {e}")
        return None
    finally:
        conn.close()
# ===== STREAMLIT UI =====
def render_teacher_dashboard():
    teacher = st.session_state.auth['user_data']
    
    # Custom CSS for teacher dashboard
    st.markdown("""
    <style>
        .teacher-header {
            display: flex;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #e0e0e0;
        }
        .teacher-header h1 {
            margin: 0;
            color: #2c3e50;
        }
        .teacher-badge {
            background: #e3f2fd;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            display: flex;
            align-items: center;
            margin-left: auto;
            font-weight: 500;
        }
        .sidebar-header {
            padding: 1rem;
            background: linear-gradient(135deg, #4a6fa5, #166088);
            border-radius: 10px;
            color: white;
            margin-bottom: 1.5rem;
        }
        .card {
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            padding: 1.5rem;
            background: white;
            margin-bottom: 1rem;
            border: 1px solid #e0e0e0;
        }
        .metric-card {
            background-color: white;
            border-radius: 10px;
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            margin-bottom: 1rem;
            border: 1px solid #e0e0e0;
        }
        .assignment-card {
            border-left: 4px solid #4a6fa5;
            padding: 1rem;
            margin-bottom: 1rem;
            background: white;
            border-radius: 0 8px 8px 0;
        }
        .tab-content {
            padding: 1rem 0;
        }
        .attendance-badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 500;
        }
        .present-badge {
            background: #e6f7e6;
            color: #28a745;
        }
        .absent-badge {
            background: #f8d7da;
            color: #dc3545;
        }
    </style>
    """, unsafe_allow_html=True)

    # Sidebar with navigation
    with st.sidebar:
        st.markdown(f"""
        <div class="sidebar-header">
            <h3 style="margin:0; color:white;">Teacher Portal</h3>
            <p style="margin:0; opacity:0.8;">Welcome, {teacher['full_name']}</p>
        </div>
        """, unsafe_allow_html=True)

        menu = st.radio(
            "Navigation",
            ["📊 Dashboard", "📝 Attendance", "📚 Gradebook", "📋 Assignments", "👥 Classes", "⚙️ Profile"],
            label_visibility="collapsed"
        )

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.auth = {
                'logged_in': False,
                'user_type': None,
                'user_data': None
            }
            st.rerun()

    # Main content area
    st.markdown(f"""
    <div class="teacher-header">
        <h1>{menu.split()[-1]}</h1>
        <div class="teacher-badge">
            <span style="margin-right: 8px;">👨‍🏫</span>
            {teacher['teacher_id']}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if menu == "📊 Dashboard":
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("""
            <div class="card">
                <h3>📚 Your Classes</h3>
            </div>
            """, unsafe_allow_html=True)
            
            classes = get_teacher_classes(teacher['teacher_id'])
            if classes:
                df = pd.DataFrame(classes)
                st.dataframe(
                    df[['course_code', 'course_name', 'schedule', 'degree_program']],
                    column_config={
                        "course_code": "Course Code",
                        "course_name": "Course Name",
                        "schedule": "Schedule",
                        "degree_program": "Degree Program"
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No classes assigned to you")
            
            st.markdown("""
            <div class="card">
                <h3>⏰ Upcoming Deadlines</h3>
            </div>
            """, unsafe_allow_html=True)
            
            assignments = []
            for class_ in classes:
                class_assignments = get_class_assignments(class_['id'])
                for a in class_assignments:
                    a['course_code'] = class_['course_code']
                    assignments.append(a)
            
            if assignments:
                upcoming = [a for a in assignments if a['due_date'].date() > datetime.now().date()]
                if upcoming:
                    for assign in sorted(upcoming, key=lambda x: x['due_date'])[:3]:
                        days_left = (assign['due_date'] - datetime.now().date()).days
                        
                        st.markdown(f"""
                        <div class="assignment-card">
                            <div style="display: flex; justify-content: space-between;">
                                <strong>{assign['title']}</strong>
                                <span>{assign['course_code']}</span>
                            </div>
                            <p style="margin: 0.5rem 0 0; font-size: 0.9rem;">
                                Due in {days_left} days • {assign['due_date']}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No upcoming assignments")
            else:
                st.info("No assignments found")
        
        with col2:
            st.markdown("""
            <div class="card">
                <h3>📈 Quick Stats</h3>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="metric-card">
                <h4>👨‍🎓 Total Students</h4>
               <h2>{sum(len(get_class_students(c['id'])) for c in classes)}</h2>

            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="metric-card">
                <h4>📚 Classes Teaching</h4>
                <h2>{len(classes) if classes else 0}</h2>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="metric-card">
                <h4>📝 Assignments</h4>
                <h2>{len(assignments) if assignments else 0}</h2>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div class="card">
                <h3>📢 Announcements</h3>
                <p>Important updates from administration</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.info("""
            **Upcoming Events:**
            - Faculty meeting: Tomorrow 10am
            - Midterm grading deadline: Nov 20
            - Final exam schedule published
            """)

    elif menu == "📝 Attendance":
        classes = get_teacher_classes(teacher['teacher_id'])
        
        if classes:
            selected_class = st.selectbox(
                "Select Class",
                [(c['id'], f"{c['course_code']} - {c['course_name']}") for c in classes],
                format_func=lambda x: x[1]
            )
            
            if selected_class:
                class_id = selected_class[0]
                selected_class_data = next(c for c in classes if c['id'] == class_id)
                
                # Parse schedule to get class days
                schedule = selected_class_data['schedule']
                class_days = parse_schedule_days(schedule)
                
                # Only allow marking on class days
                today = datetime.now().date()
                if today.weekday() not in class_days:
                    st.warning(f"No class today for {selected_class_data['course_code']}")
                    st.stop()
                
                attendance_date = st.date_input("Attendance Date", datetime.now())
                
                # Check if date matches class schedule
                if attendance_date.weekday() not in class_days:
                    st.error("Selected date is not a scheduled class day")
                    st.stop()
                    
                # Check if attendance already marked for this date
                conn = connect_db()
                if conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT TOP 1 1 FROM attendance 
                            WHERE class_id = ? AND date = ?
                        """, (class_id, attendance_date))
                        if cursor.fetchone():
                            st.warning("Attendance already marked for this date")
                            st.stop()
                    except Exception as e:
                        st.error(f"Error checking attendance: {e}")
                    finally:
                        conn.close()
                
                students = get_class_students(class_id)
                if students:
                    st.subheader(f"Mark Attendance for {selected_class_data['course_code']}")
                    
                    # Use a form for better organization
                    with st.form("attendance_form"):
                        for student in students:
                            # Create two columns for each student
                            col1, col2 = st.columns([3, 2])
                            
                            with col1:
                                st.write(f"**{student['full_name']}**")
                                st.caption(student['cnic'])
                            
                            with col2:
                                status = st.radio(
                                    "Status",
                                    ["Present", "Absent"],
                                    key=f"att_{class_id}_{student['cnic']}",
                                    horizontal=True,
                                    label_visibility="collapsed"
                                )
                        
                        if st.form_submit_button("💾 Save Attendance", use_container_width=True):
                            success_count = 0
                            for student in students:
                                status = st.session_state[f"att_{class_id}_{student['cnic']}"]
                                if mark_attendance(class_id, student['cnic'], attendance_date, status):
                                    success_count += 1
                                else:
                                    st.error(f"Failed to mark attendance for {student['full_name']}")
                            
                            if success_count == len(students):
                                st.success("✅ Attendance marked successfully for all students!")
                                st.balloons()
                                st.rerun()
                else:
                    st.info("No students enrolled in this class")
        else:
            st.info("No classes assigned to you")

    elif menu == "📚 Gradebook":
        classes = get_teacher_classes(teacher['teacher_id'])
        
        if classes:
            selected_class = st.selectbox(
                "Select Class",
                [(c['id'], f"{c['course_code']} - {c['course_name']}") for c in classes],
                format_func=lambda x: x[1]
            )
            
            if selected_class:
                class_id = selected_class[0]
                
                tab1, tab2, tab3 = st.tabs(["📝 Assignments", "📝 Exams", "📊 Final Grades"])
                
                with tab1:
                    st.markdown("""
                    <div class="card">
                        <h3>Manage Assignments</h3>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.expander("➕ Create New Assignment", expanded=False):
                        with st.form("new_assignment"):
                            title = st.text_input("Assignment Title")
                            description = st.text_area("Description")
                            total_marks = st.number_input("Total Marks", min_value=1, max_value=100, value=10)
                            due_date = st.date_input("Due Date", datetime.now() + timedelta(days=7))
                            
                            if st.form_submit_button("Create Assignment"):
                                if create_assignment(class_id, title, description, total_marks, due_date):
                                    st.success("Assignment created successfully!")
                                    st.rerun()
                    
                    assignments = get_class_assignments(class_id)
                    if assignments:
                        for assignment in assignments:
                            with st.expander(f"📝 {assignment['title']} - Due: {assignment['due_date']}"):
                                st.write(f"**Description:** {assignment['description']}")
                                st.write(f"**Total Marks:** {assignment['total_marks']}")
                                
                                students = get_class_students(class_id)
                                if students:
                                    st.subheader("Grade Students")
                                    
                                    for student in students:
                                        st.write(f"**{student['full_name']}**")
                                        
                                        # Show student submission if exists
                                        submission = get_student_assignment_submission(
                                            assignment['id'], student['cnic']
                                        )
                                        if submission:
                                            st.success("✅ Student has submitted")
                                            st.write(f"Submitted on: {submission['submitted_at']}")
                                            st.download_button(
                                                label=f"📥 Download {submission['file_name']}",
                                                data=submission['submission_file'],
                                                file_name=submission['file_name'],
                                                mime=submission['file_type'],
                                                key=f"sub_{assignment['id']}_{student['cnic']}"
                                            )
                                        else:
                                            st.warning("⚠️ No submission yet")
                                        
                                        marks = st.number_input(
                                            "Marks Obtained",
                                            min_value=0.0,
                                            max_value=float(assignment['total_marks']),
                                            step=0.5,
                                            key=f"assgn_{assignment['id']}_{student['cnic']}"
                                        )
                                        feedback = st.text_area(
                                            "Feedback",
                                            key=f"feedback_{assignment['id']}_{student['cnic']}"
                                        )
                                        
                                        if st.button(
                                            "💾 Save Grade",
                                            key=f"save_{assignment['id']}_{student['cnic']}"
                                        ):
                                            if submit_assignment_grade(
                                                assignment['id'], student['cnic'], 
                                                marks, feedback, teacher['teacher_id']
                                            ):
                                                st.success(f"Grade saved for {student['full_name']}")
                                            else:
                                                st.error(f"Failed to save grade for {student['full_name']}")
                    else:
                        st.info("No assignments created yet")
                
                with tab2:
                    st.markdown("""
                    <div class="card">
                        <h3>Manage Exams</h3>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.expander("➕ Create New Exam", expanded=False):
                        with st.form("new_exam"):
                            exam_type = st.selectbox("Exam Type", ["Quiz", "Midterm", "Final"])
                            title = st.text_input("Exam Title")
                            total_marks = st.number_input("Total Marks", min_value=1, max_value=100, value=20)
                            exam_date = st.date_input("Exam Date", datetime.now() + timedelta(days=14))
                            weightage = st.number_input("Weightage (%)", min_value=1, max_value=100, value=20)
                            
                            if st.form_submit_button("Create Exam"):
                                if create_exam(class_id, exam_type, title, total_marks, exam_date, weightage):
                                    st.success("Exam created successfully!")
                                    st.rerun()
                    
                    exams = get_class_exams(class_id)
                    if exams:
                        for exam in exams:
                            with st.expander(f"📝 {exam['exam_type']}: {exam['title']} - {exam['exam_date']}"):
                                st.write(f"**Total Marks:** {exam['total_marks']}")
                                st.write(f"**Weightage:** {exam['weightage']}%")
                                
                                students = get_class_students(class_id)
                                if students:
                                    st.subheader("Grade Students")
                                    
                                    for student in students:
                                        st.write(f"**{student['full_name']}**")
                                        marks = st.number_input(
                                            "Marks Obtained",
                                            min_value=0.0,
                                            max_value=float(exam['total_marks']),
                                            step=0.5,
                                            key=f"exam_{exam['id']}_{student['cnic']}"
                                        )
                                        
                                        if st.button(
                                            "💾 Save Grade",
                                            key=f"save_exam_{exam['id']}_{student['cnic']}"
                                        ):
                                            if submit_exam_grade(
                                                exam['id'], student['cnic'], 
                                                marks, teacher['teacher_id']
                                            ):
                                                st.success(f"Grade saved for {student['full_name']}")
                                            else:
                                                st.error(f"Failed to save grade for {student['full_name']}")
                    else:
                        st.info("No exams created yet")
                
                with tab3:
                    st.markdown("""
                    <div class="card">
                        <h3>Final Grades</h3>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    students = get_class_students(class_id)
                    
                    if students:
                        for student in students:
                            with st.expander(f"👨‍🎓 {student['full_name']}"):
                                # Calculate final grade
                                final_grade = calculate_course_grade(student['cnic'], class_id)
                                
                                if final_grade is not None:
                                    st.metric("Calculated Grade Point", f"{final_grade:.2f}/4.0")
                                    
                                    # Allow teacher to override if needed
                                    override_grade = st.number_input(
                                        "Override Grade (if needed)",
                                        min_value=0.0,
                                        max_value=4.0,
                                        step=0.1,
                                        value=float(final_grade),
                                        key=f"override_{student['cnic']}"
                                    )
                                    
                                    remarks = st.text_area(
                                        "Remarks",
                                        key=f"remarks_{student['cnic']}"
                                    )
                                    
                                    if st.button(
                                        "💾 Submit Final Grade",
                                        key=f"final_{student['cnic']}"
                                    ):
                                        if assign_grade(
                                            student['cnic'], class_id, override_grade, 
                                            remarks, teacher['teacher_id']
                                        ):
                                            st.success("Final grade submitted!")
                                        else:
                                            st.error("Failed to submit final grade")
                                else:
                                    st.warning("Not enough data to calculate final grade")
                    else:
                        st.info("No students in this class")
        else:
            st.info("No classes assigned to you")

    elif menu == "📋 Assignments":
        classes = get_teacher_classes(teacher['teacher_id'])
        
        if classes:
            selected_class = st.selectbox(
                "Select Class",
                [(c['id'], f"{c['course_code']} - {c['course_name']}") for c in classes],
                format_func=lambda x: x[1]
            )
            
            if selected_class:
                class_id = selected_class[0]
                assignments = get_class_assignments(class_id)
                
                if assignments:
                    selected_assignment = st.selectbox(
                        "Select Assignment",
                        [(a['id'], a['title']) for a in assignments],
                        format_func=lambda x: x[1]
                    )
                    
                    if selected_assignment:
                        submissions = get_assignment_submissions(selected_assignment[0])
                        
                        if submissions:
                            st.markdown(f"""
                            <div class="card">
                                <h3>Submissions for {selected_assignment[1]}</h3>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            for submission in submissions:
                                with st.expander(f"📝 {submission['full_name']} - {submission['submitted_at']}"):
                                    st.write(f"**Submitted on:** {submission['submitted_at']}")
                                    st.write(f"**File:** {submission['file_name']}")
                                    
                                    # Download button
                                    file_data = get_submission_file(submission['id'])
                                    if file_data:
                                        st.download_button(
                                            label="📥 Download Submission",
                                            data=file_data['file_data'],
                                            file_name=file_data['file_name'],
                                            mime=file_data['file_type']
                                        )
                                    
                                    # Grade assignment directly from here
                                    st.write("---")
                                    st.subheader("Grade Assignment")
                                    
                                    existing_grade = get_assignment_grade(
                                        selected_assignment[0], submission['student_cnic']
                                    )
                                    
                                    marks = st.number_input(
                                        "Marks Obtained",
                                        min_value=0.0,
                                        max_value=100.0,
                                        value=float(existing_grade['obtained_marks']) if existing_grade else 0.0,
                                        key=f"grade_{submission['id']}"
                                    )
                                    feedback = st.text_area(
                                        "Feedback",
                                        value=existing_grade['feedback'] if existing_grade else "",
                                        key=f"feedback_{submission['id']}"
                                    )
                                    
                                    if st.button(
                                        "💾 Save Grade",
                                        key=f"save_grade_{submission['id']}"
                                    ):
                                        if submit_assignment_grade(
                                            selected_assignment[0],
                                            submission['student_cnic'],
                                            marks,
                                            feedback,
                                            teacher['teacher_id']
                                        ):
                                            st.success("Grade saved successfully!")
                                        else:
                                            st.error("Failed to save grade")
                        else:
                            st.info("No submissions yet for this assignment")
                else:
                    st.info("No assignments created for this class")
        else:
            st.info("No classes assigned to you")

    elif menu == "👥 Classes":
        classes = get_teacher_classes(teacher['teacher_id'])
        
        if classes:
            st.markdown("""
            <div class="card">
                <h3>Your Classes</h3>
            </div>
            """, unsafe_allow_html=True)
            
            df = pd.DataFrame(classes)
            st.dataframe(
                df[['course_code', 'course_name', 'schedule', 'degree_program']],
                column_config={
                    "course_code": "Course Code",
                    "course_name": "Course Name",
                    "schedule": "Schedule",
                    "degree_program": "Degree Program"
                },
                use_container_width=True,
                hide_index=True
            )
            
            # CSV download button
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Class List",
                data=csv,
                file_name='teacher_classes.csv',
                mime='text/csv',
                use_container_width=True
            )
        else:
            st.info("No classes assigned to you")

    elif menu == "⚙️ Profile":
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("""
            <div class="card">
                <h3>Profile Information</h3>
            </div>
            """, unsafe_allow_html=True)
            
            st.write(f"**Name:** {teacher['full_name']}")
            st.write(f"**Teacher ID:** {teacher['teacher_id']}")
            st.write(f"**Email:** {teacher['email']}")
        
        with col2:
            st.markdown("""
            <div class="card">
                <h3>Change Password</h3>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("change_pass"):
                current = st.text_input("Current Password", type="password")
                new = st.text_input("New Password", type="password")
                confirm = st.text_input("Confirm Password", type="password")
                
                if st.form_submit_button("🔒 Update Password", use_container_width=True):
                    if new != confirm:
                        st.error("New passwords don't match!")
                    elif hash_password(current) != teacher['password_hash']:
                        st.error("Current password incorrect")
                    elif update_password("teachers", "teacher_id", teacher['teacher_id'], new):
                        st.success("Password updated successfully!")
                        st.session_state.auth['user_data']['password_hash'] = hash_password(new)
                        st.session_state.auth['user_data']['must_change_pass'] = False
                    else:
                        st.error("Failed to update password")
                    
def render_student_dashboard():
    # Custom CSS styling
    st.markdown("""
    <style>
        .student-header {
            display: flex;
            align-items: center;
            margin-bottom: 1.5rem;
        }
        .student-header h1 {
            margin: 0;
            color: #2c3e50;
        }
        .student-badge {
            background: #e3f2fd;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            display: flex;
            align-items: center;
            margin-left: auto;
        }
        .student-card {
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            padding: 1.5rem;
            background: white;
            margin-bottom: 1rem;
        }
        .sidebar-header {
            padding: 1rem;
            background: linear-gradient(135deg, #4a6fa5, #166088);
            border-radius: 10px;
            color: white;
            margin-bottom: 1.5rem;
        }
        .metric-card {
            background-color: white;
            border-radius: 10px;
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            margin-bottom: 1rem;
        }
        .assignment-card {
            border-left: 4px solid #4a6fa5;
            padding: 1rem;
            margin-bottom: 1rem;
            background: white;
            border-radius: 0 8px 8px 0;
        }
        .success-message {
            color: #28a745;
            padding: 0.5rem;
            border-radius: 0.5rem;
            background-color: #e6f7e6;
            margin: 0.5rem 0;
        }
        .error-message {
            color: #dc3545;
            padding: 0.5rem;
            border-radius: 0.5rem;
            background-color: #f8d7da;
            margin: 0.5rem 0;
        }
        .warning-message {
            color: #ffc107;
            padding: 0.5rem;
            border-radius: 0.5rem;
            background-color: #fff3cd;
            margin: 0.5rem 0;
        }
        .invoice-card {
            border-left: 4px solid #4a6fa5;
            padding: 1rem;
            margin-bottom: 1rem;
            background: white;
            border-radius: 0 8px 8px 0;
        }
    </style>
    """, unsafe_allow_html=True)

    def generate_invoice_pdf(invoice_data, student_data):
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from io import BytesIO
        import textwrap
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Set up styles
        c.setFont("Helvetica-Bold", 16)
        
        # Header
        c.drawString(100, height - 100, "EDUVATE UNIVERSITY")
        c.setFont("Helvetica", 12)
        c.drawString(100, height - 120, "123 Education Street, Learning City")
        c.drawString(100, height - 140, "Phone: (123) 456-7890 | Email: info@eduvate.edu")
        
        # Invoice title
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(width/2, height - 180, "FEE INVOICE")
        
        # Invoice details
        c.setFont("Helvetica", 12)
        c.drawString(100, height - 220, f"Invoice #: {invoice_data['id']}")
        c.drawString(100, height - 240, f"Date Issued: {invoice_data['issue_date']}")
        c.drawString(100, height - 260, f"Due Date: {invoice_data['due_date']}")
        
        # Student info
        c.drawString(350, height - 220, f"Student ID: {student_data['student_id']}")
        c.drawString(350, height - 240, f"Student Name: {student_data['full_name']}")
        c.drawString(350, height - 260, f"Degree Program: {student_data['degree']}")
        
        # Line separator
        c.line(100, height - 280, width - 100, height - 280)
        
        # Invoice items
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, height - 310, "Description")
        c.drawString(400, height - 310, "Amount")
        
        c.setFont("Helvetica", 12)
        c.drawString(100, height - 340, f"Tuition Fee for {student_data['degree']}")
        c.drawString(400, height - 340, f"Rs. {invoice_data['amount']:,.2f}")
        
        # Total
        c.setFont("Helvetica-Bold", 14)
        c.drawString(400, height - 380, f"Total: Rs. {invoice_data['amount']:,.2f}")
        
        # Payment status
        status_y = height - 420
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, status_y, "Payment Status:")
        c.setFont("Helvetica", 12)
        if invoice_data['status'] == "Paid":
            c.drawString(200, status_y, "PAID")
        else:
            c.drawString(200, status_y, "PENDING")
        
        # Footer
        c.setFont("Helvetica", 10)
        footer_text = "Please make payments by the due date to avoid late fees. Payments can be made at the university cashier or through bank transfer to Account #123456789."
        for i, line in enumerate(textwrap.wrap(footer_text, width=100)):
            c.drawString(100, height - 470 - (i * 15), line)
        
        # University stamp
        c.setFont("Helvetica-Oblique", 10)
        c.drawCentredString(width/2, 100, "Official Invoice - Eduvate University")
        
        c.save()
        buffer.seek(0)
        return buffer

    student = st.session_state.auth['user_data']
    
    # Sidebar with student navigation
    with st.sidebar:
        st.markdown(f"""
        <div class="sidebar-header">
            <h3 style="margin:0; color:white;">Student Portal</h3>
            <p style="margin:0; opacity:0.8;">Welcome, {student['full_name']}</p>
        </div>
        """, unsafe_allow_html=True)

        menu = st.radio(
            "Navigation",
            ["📊 Dashboard", "📅 Attendance", "📝 Grades", "📚 Assignments", 
             "📝 Exams", "💰 Invoices", "👤 Profile"],
            label_visibility="collapsed"
        )

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.auth = {
                'logged_in': False,
                'user_type': None,
                'user_data': None
            }
            st.rerun()

    # Main content area
    st.markdown(f"""
    <div class="student-header">
        <h1>{menu.split()[-1]}</h1>
        <div class="student-badge">
            <span style="margin-right: 8px;">🎓</span>
            {student['student_id']}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if menu == "📊 Dashboard":
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Academic Summary
            st.markdown("""
            <div class="student-card">
                <h3>📚 Academic Summary</h3>
            </div>
            """, unsafe_allow_html=True)
            
            grades = get_student_grades_report(student['cnic'])
            if grades:
                total_points = sum(g['grade_point'] for g in grades)
                gpa = total_points / len(grades) if grades else 0
                
                # GPA visualization
                gpa_percent = (gpa / 4.0) * 100
                st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 20px; margin: 1rem 0;">
                    <div style="width: 100px; height: 100px; border-radius: 50%; 
                                background: conic-gradient(#4a6fa5 {gpa_percent}%, #e9ecef 0%); 
                                display: flex; justify-content: center; align-items: center;">
                        <span style="font-size: 1.5rem; font-weight: bold;">{gpa:.2f}</span>
                    </div>
                    <div>
                        <h3 style="margin: 0;">Current GPA</h3>
                        <p style="margin: 0; opacity: 0.7;">Out of 4.0 scale</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Course grades
                with st.expander("View Course Grades"):
                    df = pd.DataFrame([{
                        'Course': g['course_code'],
                        'Grade': g['grade_point'],
                        'Remarks': g['remarks']
                    } for g in grades])
                    st.dataframe(df)
                    
                    # Download grades as CSV
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Grades",
                        data=csv,
                        file_name='my_grades.csv',
                        mime='text/csv',
                        use_container_width=True
                    )
            else:
                st.info("No grades available yet")
            
            # Upcoming Assignments
            st.markdown("""
            <div class="student-card">
                <h3>⏰ Upcoming Deadlines</h3>
            </div>
            """, unsafe_allow_html=True)
            
            assignments = get_student_assignment_grades(student['cnic'])
            if assignments:
                upcoming = [a for a in assignments if a['due_date'] > datetime.now().date()]
                if upcoming:
                    for assign in sorted(upcoming, key=lambda x: x['due_date'])[:3]:
                        days_left = (assign['due_date'] - datetime.now().date()).days
                        status = "✅ Submitted" if assign['obtained_marks'] is not None else "⚠️ Pending"
                        
                        st.markdown(f"""
                        <div class="assignment-card">
                            <div style="display: flex; justify-content: space-between;">
                                <strong>{assign['title']}</strong>
                                <span>{status}</span>
                            </div>
                            <p style="margin: 0.5rem 0 0; font-size: 0.9rem;">
                                {assign['course_code']} • Due in {days_left} days
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No upcoming assignments")
            else:
                st.info("No assignments found")
        
        with col2:
            # Quick Info
            st.markdown("""
            <div class="student-card">
                <h3>ℹ️ Quick Info</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Attendance summary
            attendance = get_student_attendance(student['cnic'])
            if attendance:
                present = len([a for a in attendance if a['status'] == "Present"])
                total = len(attendance)
                percentage = (present / total) * 100 if total > 0 else 0
                
                st.markdown(f"""
                <div style="margin: 1rem 0;">
                    <h4 style="margin: 0 0 0.5rem;">Attendance</h4>
                    <div style="height: 8px; background: #e9ecef; border-radius: 4px;">
                        <div style="width: {percentage}%; height: 100%; 
                                    background: #4a6fa5; border-radius: 4px;"></div>
                    </div>
                    <p style="margin: 0.5rem 0 0; text-align: right;">
                        {present}/{total} ({percentage:.1f}%)
                    </p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("No attendance records")
            
            # Fee status
            invoices = get_student_invoices(student['cnic'])
            if invoices:
                paid = sum(i['amount'] for i in invoices if i['status'] == "Paid")
                unpaid = sum(i['amount'] for i in invoices if i['status'] == "Unpaid")
                
                st.metric("💰 Paid Fees", f"Rs. {paid:,.2f}")
                st.metric("💸 Unpaid Fees", f"Rs. {unpaid:,.2f}")
                
                # Check for overdue invoices
                overdue = [i for i in invoices if i['due_date'] < datetime.now().date() and i['status'] == "Unpaid"]
                if overdue:
                    st.error(f"You have {len(overdue)} overdue invoice(s)")
            else:
                st.info("No invoices found")
            
            # Announcements
            st.markdown("""
            <div class="student-card">
                <h3>📢 Announcements</h3>
                <p>Important updates from your institution</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.info("""
            **Upcoming Events:**
            - Midterm exams: Nov 15-20
            - Last date for course drop: Nov 5
            """)

    elif menu == "📅 Attendance":
        classes = get_student_classes(student['degree'])
        
        if classes:
            selected_class = st.selectbox(
                "Select Class",
                [(c['course_code'], c['course_name']) for c in classes],
                format_func=lambda x: f"{x[0]} - {x[1]}"
            )
            
            if selected_class:
                attendance = get_student_attendance_by_class(student['cnic'], selected_class[0])
                
                if attendance:
                    df = pd.DataFrame(attendance)
                    st.dataframe(df)
                    
                    present = len([a for a in attendance if a['status'] == "Present"])
                    total = len(attendance)
                    percentage = (present / total) * 100 if total > 0 else 0
                    
                    col1, col2 = st.columns(2)
                    col1.metric("Present", present)
                    col2.metric("Attendance Percentage", f"{percentage:.1f}%")
                    
                    # Download attendance as CSV
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Attendance",
                        data=csv,
                        file_name=f'attendance_{selected_class[0]}.csv',
                        mime='text/csv',
                        use_container_width=True
                    )
                else:
                    st.info(f"No attendance records for {selected_class[1]}")
        else:
            st.info("No classes scheduled")

    elif menu == "📝 Grades":
        classes = get_student_classes(student['degree'])
        grades = get_student_grades_report(student['cnic'])
        
        if classes:
            selected_class = st.selectbox(
                "Select Class",
                [(c['course_code'], c['course_name']) for c in classes],
                format_func=lambda x: f"{x[0]} - {x[1]}"
            )
            
            if selected_class:
                # Get class ID
                conn = connect_db()
                if conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT id FROM classes WHERE course_code = ?
                        """, (selected_class[0],))
                        class_id_result = cursor.fetchone()
                        if class_id_result:
                            class_id = class_id_result[0]
                            
                            # Show detailed grade breakdown
                            tab1, tab2, tab3 = st.tabs(["Assignments", "Exams", "Final Grade"])
                            
                            with tab1:
                                assignments = get_student_assignment_grades(student['cnic'], class_id)
                                if assignments:
                                    df = pd.DataFrame([{
                                        'Assignment': a['title'],
                                        'Total Marks': a['total_marks'],
                                        'Obtained': a['obtained_marks'],
                                        'Percentage': (a['obtained_marks'] / a['total_marks']) * 100 if a['obtained_marks'] and a['total_marks'] else 0,
                                        'Feedback': a['feedback']
                                    } for a in assignments])
                                    st.dataframe(df)
                                    
                                    # Download assignment grades
                                    csv = df.to_csv(index=False).encode('utf-8')
                                    st.download_button(
                                        label="📥 Download Assignment Grades",
                                        data=csv,
                                        file_name=f'assignment_grades_{selected_class[0]}.csv',
                                        mime='text/csv',
                                        use_container_width=True
                                    )
                                else:
                                    st.info("No assignment grades available")
                            
                            with tab2:
                                exams = get_student_exam_grades(student['cnic'], class_id)
                                if exams:
                                    df = pd.DataFrame([{
                                        'Exam': f"{e['exam_type']} - {e['title']}",
                                        'Total Marks': e['total_marks'],
                                        'Obtained': e['obtained_marks'],
                                        'Percentage': (e['obtained_marks'] / e['total_marks']) * 100 if e['obtained_marks'] and e['total_marks'] else 0,
                                        'Weightage': f"{e['weightage']}%"
                                    } for e in exams])
                                    st.dataframe(df)
                                    
                                    # Download exam grades
                                    csv = df.to_csv(index=False).encode('utf-8')
                                    st.download_button(
                                        label="📥 Download Exam Grades",
                                        data=csv,
                                        file_name=f'exam_grades_{selected_class[0]}.csv',
                                        mime='text/csv',
                                        use_container_width=True
                                    )
                                else:
                                    st.info("No exam grades available")
                            
                            with tab3:
                                final_grade = next((g for g in grades if g['course_code'] == selected_class[0]), None)
                                if final_grade:
                                    st.metric("Final Grade Point", f"{final_grade['grade_point']:.2f}/4.0")
                                    st.write(f"**Remarks:** {final_grade['remarks']}")
                                    st.write(f"**Instructor:** {final_grade['instructor']}")
                                else:
                                    st.info("Final grade not yet assigned")
                        else:
                            st.error("Class not found")
                    except Exception as e:
                        st.error(f"Error fetching class details: {e}")
                    finally:
                        conn.close()
        else:
            st.info("No classes enrolled")

    elif menu == "📚 Assignments":
        assignments = get_student_assignment_grades(student['cnic'])
        
        if assignments:
            # Group by course
            courses = {}
            for a in assignments:
                if a['course_code'] not in courses:
                    courses[a['course_code']] = []
                courses[a['course_code']].append(a)
            
            for course, assigns in courses.items():
                with st.expander(f"{course} - {assigns[0]['course_name']}"):
                    for assignment in assigns:
                        st.subheader(assignment['title'])
                        st.write(f"**Due Date:** {assignment['due_date']}")
                        st.write(f"**Total Marks:** {assignment['total_marks']}")
                        
                        # Check if assignment is past due
                        is_past_due = datetime.now().date() > assignment['due_date']
                        
                        # Get existing submission if any
                        submission = get_student_assignment_submission(
                            assignment['id'], student['cnic']
                        )
                        
                        if submission:
                            st.markdown("""
                            <div class="success-message">
                                ✅ You have submitted this assignment
                            </div>
                            """, unsafe_allow_html=True)
                            st.write(f"**Submitted on:** {submission['submitted_at']}")
                            
                            # Download button for submitted file
                            st.download_button(
                                label="Download Your Submission",
                                data=submission['submission_file'],
                                file_name=submission['file_name'],
                                mime=submission['file_type'],
                                key=f"download_{assignment['id']}"
                            )
                            
                            if not is_past_due:
                                st.write("You can resubmit until the due date:")
                        else:
                            st.markdown("""
                            <div class="warning-message">
                                ⚠️ You haven't submitted this assignment yet
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Submission form (only show if not past due)
                        if not is_past_due:
                            with st.form(f"submission_form_{assignment['id']}"):
                                uploaded_file = st.file_uploader(
                                    "Upload your assignment",
                                    type=["pdf", "doc", "docx", "txt"],
                                    key=f"file_{assignment['id']}"
                                )
                                
                                if st.form_submit_button("Submit Assignment"):
                                    if uploaded_file is not None:
                                        if submit_assignment(
                                            assignment['id'],
                                            student['cnic'],
                                            uploaded_file.read(),
                                            uploaded_file.name,
                                            uploaded_file.type
                                        ):
                                            st.markdown("""
                                            <div class="success-message">
                                                ✅ Assignment submitted successfully!
                                            </div>
                                            """, unsafe_allow_html=True)
                                            st.rerun()
                                        else:
                                            st.markdown("""
                                            <div class="error-message">
                                                ❌ Failed to submit assignment
                                            </div>
                                            """, unsafe_allow_html=True)
                                    else:
                                        st.markdown("""
                                        <div class="error-message">
                                            ❌ Please select a file to upload
                                        </div>
                                        """, unsafe_allow_html=True)
                        else:
                            st.markdown("""
                            <div class="error-message">
                                ❌ The due date has passed - submissions are closed
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Show grade if available
                        if assignment['obtained_marks'] is not None:
                            st.write("---")
                            st.write(f"**Grade:** {assignment['obtained_marks']}/{assignment['total_marks']}")
                            st.write(f"**Feedback:** {assignment['feedback'] or 'No feedback provided'}")
        else:
            st.info("No assignments found")

    elif menu == "📝 Exams":
        exams = get_student_exam_grades(student['cnic'])
        
        if exams:
            # Group by course
            courses = {}
            for e in exams:
                if e['course_code'] not in courses:
                    courses[e['course_code']] = []
                courses[e['course_code']].append(e)
            
            for course, exms in courses.items():
                with st.expander(f"{course} - {exms[0]['course_name']}"):
                    df = pd.DataFrame([{
                        'Exam': f"{e['exam_type']} - {e['title']}",
                        'Date': e['exam_date'],
                        'Total Marks': e['total_marks'],
                        'Obtained': e['obtained_marks'],
                        'Percentage': (e['obtained_marks'] / e['total_marks']) * 100 if e['obtained_marks'] and e['total_marks'] else 0,
                        'Weightage': f"{e['weightage']}%"
                    } for e in exms])
                    st.dataframe(df)
                    
                    # Download exam grades for this course
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Exam Results",
                        data=csv,
                        file_name=f'exam_results_{course}.csv',
                        mime='text/csv',
                        use_container_width=True
                    )
        else:
            st.info("No exams found")

    elif menu == "💰 Invoices":
        invoices = get_student_invoices(student['cnic'])
        
        if invoices:
            for invoice in invoices:
                with st.expander(f"Invoice #{invoice['id']} - {invoice['status']}"):
                    col1, col2, col3 = st.columns(3)
                    col1.write(f"**Student:** {student['full_name']}")
                    col1.write(f"**Student ID:** {student['student_id']}")
                    col2.write(f"**Amount:** Rs. {invoice['amount']:,.2f}")
                    col2.write(f"**Issue Date:** {str(invoice['issue_date'])}")
                    col3.write(f"**Due Date:** {str(invoice['due_date'])}")
                    col3.write(f"**Status:** {invoice['status']}")
                    
                    # Generate and download PDF
                    pdf_buffer = generate_invoice_pdf(invoice, student)
                    st.download_button(
                        label="📄 Download Invoice (PDF)",
                        data=pdf_buffer,
                        file_name=f"Invoice_{invoice['id']}_{student['student_id']}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                    # Show payment status
                    if invoice['status'] == "Paid":
                        st.markdown("""
                        <div class="success-message">
                            ✅ This invoice has been fully paid
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        days_left = (invoice['due_date'] - datetime.now().date()).days
                        if days_left < 0:
                            st.markdown(f"""
                            <div class="error-message">
                                ❌ Overdue by {-days_left} days
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class="warning-message">
                                ⚠️ Due in {days_left} days
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Show payment history (read-only)
                    payments = get_invoice_payments(invoice['id'])
                    if payments:
                        st.subheader("Payment History")
                        df = pd.DataFrame(payments)
                        st.dataframe(df)
                        
                        # Download payment history
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download Payment History",
                            data=csv,
                            file_name=f'payment_history_{invoice["id"]}.csv',
                            mime='text/csv',
                            use_container_width=True
                        )
                    else:
                        st.info("No payments recorded for this invoice")
        else:
            st.info("No invoices found")

    elif menu == "👤 Profile":
        col1, col2 = st.columns([1, 2])
        
        with col1:
            if student['profile_pic']:
                try:
                    st.image(student['profile_pic'], width=200)
                except:
                    st.warning("Couldn't display profile picture")
            else:
                st.info("No profile picture")
        
        with col2:
            st.write(f"**Name:** {student['full_name']}")
            st.write(f"**CNIC:** {student['cnic']}")
            st.write(f"**Age:** {student['age']}")
            st.write(f"**Degree:** {student['degree']}")
            st.write(f"**Father:** {student['father_name']}")
            st.write(f"**Student ID:** {student['student_id']}")
            
            with st.expander("Change Password"):
                with st.form("change_pass"):
                    current = st.text_input("Current Password", type="password")
                    new = st.text_input("New Password", type="password")
                    confirm = st.text_input("Confirm Password", type="password")
                    
                    if st.form_submit_button("Update Password"):
                        if new != confirm:
                            st.markdown("""
                            <div class="error-message">
                                ❌ New passwords don't match!
                            </div>
                            """, unsafe_allow_html=True)
                        elif hash_password(current) != student['password_hash']:
                            st.markdown("""
                            <div class="error-message">
                                ❌ Current password incorrect
                            </div>
                            """, unsafe_allow_html=True)
                        elif update_password("students", "cnic", student['cnic'], new):
                            st.markdown("""
                            <div class="success-message">
                                ✅ Password updated successfully!
                            </div>
                            """, unsafe_allow_html=True)
                            st.session_state.auth['user_data']['password_hash'] = hash_password(new)
                            st.session_state.auth['user_data']['must_change_pass'] = False
                        else:
                            st.markdown("""
                            <div class="error-message">
                                ❌ Failed to update password
                            </div>
                            """, unsafe_allow_html=True)
def render_admin_dashboard():
    # Custom CSS styling
    st.markdown("""
    <style>
        .admin-header {
            display: flex;
            align-items: center;
            margin-bottom: 1.5rem;
        }
        .admin-header h1 {
            margin: 0;
            color: #2c3e50;
        }
        .admin-badge {
            background: #e3f2fd;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            display: flex;
            align-items: center;
            margin-left: auto;
            font-weight: 500;
        }
        .admin-card {
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            padding: 1.5rem;
            background: white;
            margin-bottom: 1rem;
            border: 1px solid #e0e0e0;
        }
        .sidebar-header {
            padding: 1rem;
            background: linear-gradient(135deg, #4a6fa5, #166088);
            border-radius: 10px;
            color: white;
            margin-bottom: 1.5rem;
        }
        .metric-card {
            background-color: white;
            border-radius: 10px;
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            margin-bottom: 1rem;
            border: 1px solid #e0e0e0;
        }
        .success-message {
            color: #28a745;
            padding: 0.5rem;
            border-radius: 0.5rem;
            background-color: #e6f7e6;
            margin: 0.5rem 0;
        }
        .error-message {
            color: #dc3545;
            padding: 0.5rem;
            border-radius: 0.5rem;
            background-color: #f8d7da;
            margin: 0.5rem 0;
        }
        .warning-message {
            color: #ffc107;
            padding: 0.5rem;
            border-radius: 0.5rem;
            background-color: #fff3cd;
            margin: 0.5rem 0;
        }
        .search-filter {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        .data-table {
            margin-top: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)

    # Helper functions for messages
    def show_success(message):
        st.markdown(f'<div class="success-message">{message}</div>', unsafe_allow_html=True)
    
    def show_error(message):
        st.markdown(f'<div class="error-message">{message}</div>', unsafe_allow_html=True)
    
    def show_warning(message):
        st.markdown(f'<div class="warning-message">{message}</div>', unsafe_allow_html=True)

    # Sidebar with admin navigation
    with st.sidebar:
        st.markdown(f"""
        <div class="sidebar-header">
            <h3 style="margin:0; color:white;">Admin Dashboard</h3>
            <p style="margin:0; opacity:0.8;">Welcome, {st.session_state.auth['user_data']['username']}</p>
        </div>
        """, unsafe_allow_html=True)

        menu = st.radio(
            "Navigation",
            ["📊 Dashboard", "👨‍🏫 Manage Teachers", "👨‍🎓 Manage Students", 
             "📚 Manage Classes", "💰 Fee Management", "⚙️ System Settings"],
            label_visibility="collapsed"
        )

        if st.button("🚪 Logout", use_container_width=True, key="sidebar_logout"):
            st.session_state.auth = {
                'logged_in': False,
                'user_type': None,
                'user_data': None
            }
            st.rerun()

    # Main content area
    st.markdown(f"""
    <div class="admin-header">
        <h1>{menu.split()[-1]}</h1>
        <div class="admin-badge">
            <span style="margin-right: 8px;">👑</span>
            Admin
        </div>
    </div>
    """, unsafe_allow_html=True)

    if menu == "📊 Dashboard":
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="admin-card">
                <h3>📊 System Overview</h3>
                <p>Key metrics and system status</p>
            </div>
            """, unsafe_allow_html=True)
            
            teachers = get_teachers()
            students = get_students()
            classes = get_classes()
            
            st.markdown(f"""
            <div class="metric-card">
                <h4>👨‍🏫 Teachers</h4>
                <h2>{len(teachers)}</h2>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="metric-card">
                <h4>👨‍🎓 Students</h4>
                <h2>{len(students)}</h2>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="metric-card">
                <h4>📚 Classes</h4>
                <h2>{len(classes)}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="admin-card">
                <h3>📅 Recent Activity</h3>
                <p>Latest system events</p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("View Activity Log", expanded=True):
                activities = [
                    {"action": "New student registered", "time": "10 mins ago", "icon": "👨‍🎓"},
                    {"action": "Teacher added assignment", "time": "2 hours ago", "icon": "📝"},
                    {"action": "System backup completed", "time": "5 hours ago", "icon": "💾"},
                    {"action": "Payment received", "time": "1 day ago", "icon": "💰"},
                    {"action": "New class created", "time": "2 days ago", "icon": "📚"}
                ]
                
                for activity in activities:
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                        <span style="font-size: 1.2rem; margin-right: 10px;">{activity['icon']}</span>
                        <div>
                            <strong>{activity['action']}</strong><br>
                            <small>{activity['time']}</small>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="admin-card">
                <h3>⚠️ Alerts</h3>
                <p>Important notifications</p>
            </div>
            """, unsafe_allow_html=True)
            
            overdue = get_overdue_invoices()
            if overdue:
                show_error(f"""
                <div style="display: flex; align-items: center;">
                    <span style="font-size: 1.5rem; margin-right: 10px;">❗</span>
                    <div>
                        <strong>{len(overdue)} Overdue Invoices</strong><br>
                        <small>Require immediate attention</small>
                    </div>
                </div>
                """)
            else:
                show_success("""
                <div style="display: flex; align-items: center;">
                    <span style="font-size: 1.5rem; margin-right: 10px;">✅</span>
                    <div>
                        <strong>No Overdue Invoices</strong><br>
                        <small>All payments up to date</small>
                    </div>
                </div>
                """)
                
            st.markdown("""
            <div class="metric-card">
                <h4>🔄 System Status</h4>
                <div style="display: flex; align-items: center; margin-top: 10px;">
                    <span style="display: inline-block; width: 12px; height: 12px; 
                        background-color: #28a745; border-radius: 50%; margin-right: 8px;"></span>
                    <span>All systems operational</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    elif menu == "👨‍🏫 Manage Teachers":
        tab1, tab2, tab3 = st.tabs(["👥 View Teachers", "➕ Add Teacher", "✏️ Update Teacher"])
        
        with tab1:
            st.markdown("""
            <div class="admin-card">
                <h3>Current Teachers</h3>
                <p>View and manage teacher accounts</p>
            </div>
            """, unsafe_allow_html=True)
            
            teachers = get_teachers()
            
            if teachers:
                st.markdown('<div class="search-filter">', unsafe_allow_html=True)
                search_term = st.text_input("Search teachers", placeholder="Search by name, ID or email")
                st.markdown('</div>', unsafe_allow_html=True)
                
                filtered_teachers = teachers
                if search_term:
                    filtered_teachers = [t for t in teachers 
                                       if (search_term.lower() in t['full_name'].lower() or 
                                           search_term in t['teacher_id'] or 
                                           search_term.lower() in t['email'].lower())]
                
                if filtered_teachers:
                    df = pd.DataFrame(filtered_teachers)
                    st.markdown('<div class="data-table">', unsafe_allow_html=True)
                    st.dataframe(
                        df[['teacher_id', 'full_name', 'email', 'created_at']],
                        column_config={
                            "teacher_id": "Teacher ID",
                            "full_name": "Full Name",
                            "email": "Email",
                            "created_at": "Created At"
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Teachers as CSV",
                        data=csv,
                        file_name='teachers_list.csv',
                        mime='text/csv',
                        use_container_width=True
                    )
                else:
                    st.info("No teachers match your search criteria")
            else:
                st.info("No teachers found in the system")
        
        with tab2:
            st.markdown("""
            <div class="admin-card">
                <h3>Add New Teacher</h3>
                <p>Register a new teacher account</p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("add_teacher_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    name = st.text_input("Full Name", placeholder="John Doe")
                
                with col2:
                    email = st.text_input("Email", placeholder="john@university.edu")
                
                submitted = st.form_submit_button("➕ Add Teacher", use_container_width=True)
                
                if submitted:
                    if name and email:
                        teacher_id = add_teacher(name, email)
                        if teacher_id:
                            show_success(f"Teacher {name} added successfully with ID: {teacher_id}")
                            st.balloons()
                    else:
                        show_error("Please fill all required fields")
        
        with tab3:
            st.markdown("""
            <div class="admin-card">
                <h3>Update Teacher</h3>
                <p>Modify existing teacher information</p>
            </div>
            """, unsafe_allow_html=True)
            
            teachers = get_teachers()
            if teachers:
                teacher_options = [(t['teacher_id'], t['full_name']) for t in teachers]
                selected_teacher = st.selectbox(
                    "Select Teacher to Update",
                    teacher_options,
                    format_func=lambda x: f"{x[0]} - {x[1]}",
                    key="teacher_update_select"
                )
                
                if selected_teacher:
                    teacher_data = next(t for t in teachers if t['teacher_id'] == selected_teacher[0])
                    
                    with st.form("update_teacher_form"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            new_name = st.text_input("Full Name", value=teacher_data['full_name'])
                        
                        with col2:
                            new_email = st.text_input("Email", value=teacher_data['email'])
                        
                        submitted = st.form_submit_button("💾 Update Teacher", use_container_width=True)
                        
                        if submitted:
                            if update_teacher(
                                selected_teacher[0],
                                name=new_name,
                                email=new_email
                            ):
                                show_success("Teacher updated successfully!")
                                st.rerun()
                            else:
                                show_error("Failed to update teacher")
            else:
                st.info("No teachers available to update")

    elif menu == "👨‍🎓 Manage Students":
        tab1, tab2, tab3 = st.tabs(["👥 View Students", "➕ Add Student", "✏️ Update Student"])
        
        with tab1:
            st.markdown("""
            <div class="admin-card">
                <h3>Current Students</h3>
                <p>View and manage student accounts</p>
            </div>
            """, unsafe_allow_html=True)
            
            students = get_students()
            
            if students:
                st.markdown('<div class="search-filter">', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    selected_degree = st.selectbox(
                        "Filter by Degree Program",
                        ["All Programs"] + DEGREE_PROGRAMS,
                        key="degree_filter"
                    )
                with col2:
                    search_term = st.text_input("Search students", placeholder="Search by name, ID or CNIC")
                st.markdown('</div>', unsafe_allow_html=True)
                
                filtered_students = students
                if selected_degree != "All Programs":
                    filtered_students = [s for s in filtered_students if s['degree'] == selected_degree]
                
                if search_term:
                    filtered_students = [s for s in filtered_students 
                                      if (search_term.lower() in s['full_name'].lower() or 
                                          search_term in s.get('student_id', '') or 
                                          search_term in s['cnic'])]
                
                if filtered_students:
                    df = pd.DataFrame(filtered_students)
                    st.markdown('<div class="data-table">', unsafe_allow_html=True)
                    st.dataframe(
                        df[['student_id', 'full_name', 'cnic', 'degree', 'created_at']],
                        column_config={
                            "student_id": "Student ID",
                            "full_name": "Full Name",
                            "cnic": "CNIC",
                            "degree": "Degree Program",
                            "created_at": "Created At"
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Students as CSV",
                        data=csv,
                        file_name='students_list.csv',
                        mime='text/csv',
                        use_container_width=True
                    )
                else:
                    st.info("No students match your search criteria")
            else:
                st.info("No students found in the system")
        
        with tab2:
            st.markdown("""
            <div class="admin-card">
                <h3>Add New Student</h3>
                <p>Register a new student account</p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("add_student_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    cnic = st.text_input("CNIC (without dashes)", max_chars=13, key="cnic_input")
                    name = st.text_input("Full Name")
                    age = st.number_input("Age", min_value=10, max_value=60)
                
                with col2:
                    degree = st.selectbox("Degree Program", DEGREE_PROGRAMS)
                    fee = st.number_input("Fee Amount", min_value=0)
                    father = st.text_input("Father's Name")
                    image = st.file_uploader("Profile Picture", type=["jpg", "png", "jpeg"])
                
                submitted = st.form_submit_button("➕ Add Student", use_container_width=True)
                
                if submitted:
                    if not validate_cnic(cnic):
                        show_error("Invalid CNIC! Must be exactly 13 digits with numbers only")
                    elif not name:
                        show_error("Full name is required")
                    elif not father:
                        show_error("Father's name is required")
                    else:
                        student_id = add_student(cnic, name, age, degree, fee, father, image)
                        if student_id:
                            show_success(f"Student {name} added successfully with ID: {student_id}")
                            st.balloons()
        
        with tab3:
            st.markdown("""
            <div class="admin-card">
                <h3>Update Student</h3>
                <p>Modify existing student information</p>
            </div>
            """, unsafe_allow_html=True)
            
            students = get_students()
            if students:
                student_options = [(s['cnic'], s['full_name']) for s in students]
                selected_student = st.selectbox(
                    "Select Student to Update",
                    student_options,
                    format_func=lambda x: f"{x[0]} - {x[1]}",
                    key="student_update_select"
                )
                
                if selected_student:
                    student_data = next(s for s in students if s['cnic'] == selected_student[0])
                    
                    with st.form("update_student_form"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            new_name = st.text_input("Full Name", value=student_data['full_name'])
                            new_age = st.number_input("Age", min_value=10, max_value=60, value=student_data['age'])
                            new_degree = st.selectbox(
                                "Degree Program", 
                                DEGREE_PROGRAMS, 
                                index=DEGREE_PROGRAMS.index(student_data['degree'])
                            )
                        
                        with col2:
                            new_fee = st.number_input("Fee Amount", min_value=0, value=int(student_data['fee']))
                            new_father = st.text_input("Father's Name", value=student_data['father_name'])
                            new_image = st.file_uploader("New Profile Picture", type=["jpg", "png", "jpeg"])
                        
                        submitted = st.form_submit_button("💾 Update Student", use_container_width=True)
                        
                        if submitted:
                            if update_student(
                                selected_student[0],
                                name=new_name,
                                age=new_age,
                                degree=new_degree,
                                fee=new_fee,
                                father=new_father,
                                image=new_image
                            ):
                                show_success("Student updated successfully!")
                                st.rerun()
                            else:
                                show_error("Failed to update student")
            else:
                st.info("No students available to update")

    elif menu == "📚 Manage Classes":
        tab1, tab2, tab3 = st.tabs(["👥 View Classes", "➕ Add Class", "✏️ Update Class"])
        
        with tab1:
            st.markdown("""
            <div class="admin-card">
                <h3>Current Classes</h3>
                <p>View and manage all classes</p>
            </div>
            """, unsafe_allow_html=True)
            
            classes = get_classes()
            
            if classes:
                st.markdown('<div class="search-filter">', unsafe_allow_html=True)
                selected_degree = st.selectbox(
                    "Filter by Degree Program",
                    ["All Programs"] + DEGREE_PROGRAMS,
                    key="class_degree_filter"
                )
                
                search_term = st.text_input("Search classes", placeholder="Search by code, name or instructor")
                st.markdown('</div>', unsafe_allow_html=True)
                
                filtered_classes = classes
                if selected_degree != "All Programs":
                    filtered_classes = [c for c in filtered_classes if c['degree_program'] == selected_degree]
                
                if search_term:
                    filtered_classes = [c for c in filtered_classes 
                                      if (search_term.lower() in c['course_code'].lower() or 
                                          search_term.lower() in c['course_name'].lower() or 
                                          search_term.lower() in c['instructor'].lower())]
                
                if filtered_classes:
                    df = pd.DataFrame(filtered_classes)
                    st.markdown('<div class="data-table">', unsafe_allow_html=True)
                    st.dataframe(
                        df[['course_code', 'course_name', 'schedule', 'instructor', 'degree_program']],
                        column_config={
                            "course_code": "Course Code",
                            "course_name": "Course Name",
                            "schedule": "Schedule",
                            "instructor": "Instructor",
                            "degree_program": "Degree Program"
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Classes as CSV",
                        data=csv,
                        file_name='classes_list.csv',
                        mime='text/csv',
                        use_container_width=True
                    )
                else:
                    st.info("No classes match your search criteria")
            else:
                st.info("No classes found in the system")
        
        with tab2:
            st.markdown("""
            <div class="admin-card">
                <h3>Add New Class</h3>
                <p>Create a new class/course</p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("add_class_form", clear_on_submit=True):
                teachers = get_teachers()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    course_code = st.text_input("Course Code", placeholder="CS101")
                    course_name = st.text_input("Course Name", placeholder="Introduction to Programming")
                
                with col2:
                    schedule = st.text_input("Schedule", placeholder="Mon/Wed 9-10:30")
                    instructor = st.selectbox(
                        "Instructor",
                        [(t['teacher_id'], t['full_name']) for t in teachers],
                        format_func=lambda x: f"{x[0]} - {x[1]}"
                    )
                    degree = st.selectbox("Degree Program", DEGREE_PROGRAMS)
                
                submitted = st.form_submit_button("➕ Add Class", use_container_width=True)
                
                if submitted:
                    if course_code and course_name and schedule:
                        if add_class(course_code, course_name, schedule, instructor[0], degree):
                            show_success(f"Class {course_code} - {course_name} added successfully!")
                            st.balloons()
                    else:
                        show_error("Please fill all required fields")
        
        with tab3:
            st.markdown("""
            <div class="admin-card">
                <h3>Update Class</h3>
                <p>Modify existing class information</p>
            </div>
            """, unsafe_allow_html=True)
            
            classes = get_classes()
            if classes:
                class_options = [(c['id'], f"{c['course_code']} - {c['course_name']}") for c in classes]
                selected_class = st.selectbox(
                    "Select Class to Update",
                    class_options,
                    format_func=lambda x: x[1],
                    key="class_update_select"
                )
                
                if selected_class:
                    class_data = next(c for c in classes if c['id'] == selected_class[0])
                    teachers = get_teachers()
                    
                    with st.form("update_class_form"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            new_code = st.text_input("Course Code", value=class_data['course_code'])
                            new_name = st.text_input("Course Name", value=class_data['course_name'])
                        
                        with col2:
                            new_schedule = st.text_input("Schedule", value=class_data['schedule'])
                            new_instructor = st.selectbox(
                                "Instructor",
                                [(t['teacher_id'], t['full_name']) for t in teachers],
                                format_func=lambda x: f"{x[0]} - {x[1]}",
                                index=[i for i, t in enumerate(teachers) if t['full_name'] == class_data['instructor']][0]
                            )
                            new_degree = st.selectbox(
                                "Degree Program", 
                                DEGREE_PROGRAMS, 
                                index=DEGREE_PROGRAMS.index(class_data['degree_program'])
                            )
                        
                        submitted = st.form_submit_button("💾 Update Class", use_container_width=True)
                        
                        if submitted:
                            if update_class(
                                selected_class[0],
                                course_code=new_code,
                                course_name=new_name,
                                schedule=new_schedule,
                                instructor_id=new_instructor[0],
                                degree_program=new_degree
                            ):
                                show_success("Class updated successfully!")
                                st.rerun()
                            else:
                                show_error("Failed to update class")
            else:
                st.info("No classes available to update")

    elif menu == "💰 Fee Management":
        tab1, tab2, tab3, tab4 = st.tabs(["💸 Generate Invoices", "💰 Record Payment", "⚠️ Overdue Invoices", "✏️ Update Invoice"])
        
        with tab1:
            st.markdown("""
            <div class="admin-card">
                <h3>Generate Fee Invoices</h3>
                <p>Create new fee invoices for students</p>
            </div>
            """, unsafe_allow_html=True)
            
            students = get_students()
            
            if students:
                with st.form("generate_invoice_form", clear_on_submit=True):
                    student = st.selectbox(
                        "Select Student",
                        [(s['cnic'], s['full_name']) for s in students],
                        format_func=lambda x: f"{x[1]} ({x[0]})"
                    )
                    amount = st.number_input("Amount", min_value=0)
                    due_days = st.number_input("Due Days", min_value=1, value=30)
                    
                    submitted = st.form_submit_button("💸 Generate Invoice", use_container_width=True)
                    
                    if submitted:
                        if generate_fee_invoice(student[0], amount, due_days):
                            show_success("""
                            <div style="display: flex; align-items: center;">
                                <span style="font-size: 1.5rem; margin-right: 10px;">✅</span>
                                <div>
                                    <strong>Invoice generated successfully!</strong>
                                </div>
                            </div>
                            """)
                        else:
                            show_error("Failed to generate invoice")
            else:
                st.info("No students found in the system")
        
        with tab2:
            st.markdown("""
            <div class="admin-card">
                <h3>Record Payment</h3>
                <p>Record student fee payments</p>
            </div>
            """, unsafe_allow_html=True)
            
            conn = connect_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT i.id, s.full_name, s.cnic, i.amount, i.issue_date, 
                               i.due_date, i.status
                        FROM invoices i
                        JOIN students s ON i.student_cnic = s.cnic
                        WHERE i.status = 'Unpaid'
                        ORDER BY i.due_date ASC
                    """)
                    
                    columns = [column[0] for column in cursor.description]
                    invoices = []
                    for row in cursor.fetchall():
                        invoices.append(dict(zip(columns, row)))
                    
                    if invoices:
                        selected_invoice = st.selectbox(
                            "Select Invoice to Pay",
                            [(i['id'], f"#{i['id']} - {i['full_name']} ({i['cnic']}) - Rs.{i['amount']} - Due: {i['due_date']}") for i in invoices],
                            format_func=lambda x: x[1]
                        )
                        
                        if selected_invoice:
                            invoice_data = next(i for i in invoices if i['id'] == selected_invoice[0])
                            
                            st.markdown("""
                            <div class="admin-card">
                                <h4>Invoice Details</h4>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            col1, col2 = st.columns(2)
                            col1.write(f"**Student:** {invoice_data['full_name']}")
                            col1.write(f"**CNIC:** {invoice_data['cnic']}")
                            col2.write(f"**Total Amount:** Rs. {invoice_data['amount']:,.2f}")
                            col2.write(f"**Due Date:** {invoice_data['due_date']}")
                            
                            # Calculate remaining amount
                            cursor.execute("""
                                SELECT COALESCE(SUM(amount), 0) 
                                FROM payments 
                                WHERE invoice_id = ?
                            """, (selected_invoice[0],))
                            total_paid = cursor.fetchone()[0]
                            remaining = invoice_data['amount'] - total_paid
                            
                            st.markdown(f"""
                            <div class="metric-card">
                                <h4>Remaining Balance</h4>
                                <h2>Rs. {remaining:,.2f}</h2>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Payment form
                            with st.form("record_payment_form", clear_on_submit=True):
                                amount = st.number_input(
                                    "Payment Amount",
                                    min_value=0.01,
                                    max_value=float(remaining),
                                    value=float(remaining),
                                    step=100.0
                                )
                                method = st.selectbox(
                                    "Payment Method",
                                    ["Bank Transfer", "Card", "Cash"]
                                )
                                trans_id = st.text_input("Transaction ID (if applicable)")
                                received_by = st.text_input(
                                    "Received By",
                                    value=st.session_state.auth['user_data']['username']
                                )
                                
                                submitted = st.form_submit_button("💰 Record Payment", use_container_width=True)
                                
                                if submitted:
                                    if amount > 0:
                                        if record_payment(
                                            selected_invoice[0], amount, method, trans_id, received_by
                                        ):
                                            show_success("Payment recorded successfully!")
                                            st.balloons()
                                            st.rerun()
                                        else:
                                            show_error("Failed to record payment")
                                    else:
                                        show_error("Payment amount must be greater than 0")
                            
                            # Show payment history
                            payments = get_invoice_payments(selected_invoice[0])
                            if payments:
                                st.markdown("""
                                <div class="admin-card">
                                    <h4>Payment History</h4>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                df = pd.DataFrame(payments)
                                st.dataframe(
                                    df,
                                    column_config={
                                        "amount": "Amount",
                                        "payment_date": "Payment Date",
                                        "payment_method": "Method",
                                        "transaction_id": "Transaction ID",
                                        "received_by": "Received By"
                                    },
                                    use_container_width=True,
                                    hide_index=True
                                )
                                
                                # CSV download button for payment history
                                csv = df.to_csv(index=False).encode('utf-8')
                                st.download_button(
                                    label="📥 Download Payment History",
                                    data=csv,
                                    file_name=f'payment_history_{selected_invoice[0]}.csv',
                                    mime='text/csv',
                                    use_container_width=True
                                )
                            else:
                                st.info("No payments recorded for this invoice")
                    else:
                        st.info("No unpaid invoices found")
                except Exception as e:
                    show_error(f"Error fetching payment records: {e}")
                finally:
                    conn.close()
        
        with tab3:
            st.markdown("""
            <div class="admin-card">
                <h3>Overdue Invoices</h3>
                <p>Invoices past their due date</p>
            </div>
            """, unsafe_allow_html=True)
            
            overdue = get_overdue_invoices()
            
            if overdue:
                show_error(f"""
                <div style="display: flex; align-items: center;">
                    <span style="font-size: 1.5rem; margin-right: 10px;">❗</span>
                    <div>
                        <strong>Found {len(overdue)} overdue invoices</strong>
                    </div>
                </div>
                """)
                
                # Convert to DataFrame for display
                df = pd.DataFrame(overdue)
                
                # Display the data
                st.dataframe(
                    df,
                    column_config={
                        "id": "Invoice ID",
                        "full_name": "Student Name",
                        "cnic": "CNIC",
                        "amount": "Amount",
                        "due_date": "Due Date",
                        "remaining": "Remaining"
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                # CSV download button
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Overdue Invoices",
                    data=csv,
                    file_name='overdue_invoices.csv',
                    mime='text/csv',
                    use_container_width=True
                )
                
                if st.button("📧 Send Reminders to All", use_container_width=True):
                    show_success(f"Reminders sent for {len(overdue)} invoices")
            else:
                show_success("""
                <div style="display: flex; align-items: center;">
                    <span style="font-size: 1.5rem; margin-right: 10px;">✅</span>
                    <div>
                        <strong>No overdue invoices found</strong>
                    </div>
                </div>
                """)
        
        with tab4:
            st.markdown("""
            <div class="admin-card">
                <h3>Update Invoice</h3>
                <p>Modify existing invoice details</p>
            </div>
            """, unsafe_allow_html=True)
            
            conn = connect_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT i.id, s.full_name, s.cnic, i.amount, i.issue_date, 
                               i.due_date, i.status
                        FROM invoices i
                        JOIN students s ON i.student_cnic = s.cnic
                        ORDER BY i.due_date ASC
                    """)
                    
                    columns = [column[0] for column in cursor.description]
                    invoices = []
                    for row in cursor.fetchall():
                        invoices.append(dict(zip(columns, row)))
                    
                    if invoices:
                        selected_invoice = st.selectbox(
                            "Select Invoice to Update",
                            [(i['id'], f"#{i['id']} - {i['full_name']} ({i['cnic']}) - Rs.{i['amount']} - Due: {i['due_date']}") for i in invoices],
                            format_func=lambda x: x[1],
                            key="invoice_update_select"
                        )
                        
                        if selected_invoice:
                            invoice_data = next(i for i in invoices if i['id'] == selected_invoice[0])
                            
                            with st.form("update_invoice_form"):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    new_amount = st.number_input(
                                        "Amount",
                                        min_value=0.01,
                                        value=float(invoice_data['amount']),
                                        step=100.0
                                    )
                                
                                with col2:
                                    new_due_date = st.date_input(
                                        "Due Date",
                                        value=invoice_data['due_date']
                                    )
                                
                                submitted = st.form_submit_button("💾 Update Invoice", use_container_width=True)
                                
                                if submitted:
                                    if update_invoice(
                                        selected_invoice[0],
                                        amount=new_amount,
                                        due_date=new_due_date
                                    ):
                                        show_success("Invoice updated successfully!")
                                        st.rerun()
                                    else:
                                        show_error("Failed to update invoice")
                    else:
                        st.info("No invoices found")
                except Exception as e:
                    show_error(f"Error fetching invoices: {e}")
                finally:
                    conn.close()
                    
    elif menu == "⚙️ System Settings":
        st.markdown("""
        <div class="admin-card">
            <h3>Admin Account Settings</h3>
            <p>Manage system configuration</p>
        </div>
        """, unsafe_allow_html=True)
    
        with st.form("change_password_form"):
            st.subheader("Change Password")
            
            col1, col2 = st.columns(2)
            
            with col1:
                current = st.text_input("Current Password", type="password")
            
            with col2:
                new = st.text_input("New Password", type="password")
                confirm = st.text_input("Confirm Password", type="password")
            
            submitted = st.form_submit_button("🔒 Change Password", use_container_width=True)
            
            if submitted:
                if new != confirm:
                    show_error("New passwords don't match!")
                elif hash_password(current) != st.session_state.auth['user_data']['password_hash']:
                    show_error("Current password incorrect")
                else:
                    conn = connect_db()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE admins 
                                SET password_hash = ?
                                WHERE username = ?
                            """, (hash_password(new), PRESET_ADMIN["username"]))
                            conn.commit()
                            show_success("Password changed successfully!")
                            st.session_state.auth['user_data']['password_hash'] = hash_password(new)
                        except Error as e:
                            show_error(f"Password Update Failed: {e}")
                        finally:
                            conn.close()
    
        st.markdown("""
        <div class="admin-card">
            <h3>System Maintenance</h3>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Refresh Cache", use_container_width=True):
                show_success("System cache refreshed")
        
        with col2:
            if st.button("💾 Backup Database", use_container_width=True):
                show_success("Database backup initiated")
                
                # Generate backup CSV files
                backup_data = {
                    "teachers": pd.DataFrame(get_teachers()),
                    "students": pd.DataFrame(get_students()),
                    "classes": pd.DataFrame(get_classes()),
                    "invoices": pd.DataFrame(get_overdue_invoices())
                }
                
                # Create zip file
                import zipfile
                from io import BytesIO
                
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    for name, df in backup_data.items():
                        csv_data = df.to_csv(index=False).encode('utf-8')
                        zip_file.writestr(f"{name}_backup.csv", csv_data)
                
                # Download button for backup zip
                st.download_button(
                    label="📥 Download System Backup",
                    data=zip_buffer.getvalue(),
                    file_name="system_backup.zip",
                    mime="application/zip",
                    use_container_width=True
                )
def render_auth_screen():
    # Create columns for the split screen layout
    col1, col2 = st.columns(2)
    
    # Left column with background image and content
    with col1:
        st.markdown(f"""
        <style>
            /* Base styles */
            .left-panel {{
                background-image: url('https://images.unsplash.com/photo-1523050854058-8df90110c9f1?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80');
                background-size: cover;
                background-position: center;
                height: 80vh;
                position: relative;
                color: white;
                padding: 4rem;
                display: flex;
                flex-direction: column;
            }}
            
            .left-panel::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(135deg, rgba(22, 96, 136, 0.85) 0%, rgba(12, 66, 96, 0.9) 100%);
            }}
            
            .left-content {{
                position: relative;
                z-index: 1;
                margin-top: auto;
                margin-bottom: auto;
            }}
            
            .logo-left {{
                height: 80px;
                width: auto;
                margin-bottom: 2rem;
                filter: drop-shadow(0 0 10px rgba(255, 255, 255, 0.3));
            }}
            
            .left-content h1 {{
                font-size: 3rem;
                font-weight: 700;
                margin-bottom: 1.5rem;
                text-shadow: 0 2px 4px rgba(0,0,0,0.3);
            }}
            
            .left-content p {{
                font-size: 1.2rem;
                line-height: 1.6;
                margin-bottom: 1rem;
                text-shadow: 0 1px 2px rgba(0,0,0,0.2);
            }}
            
            .left-content ul {{
                font-size: 1.1rem;
                line-height: 2;
                margin-top: 1.5rem;
                padding-left: 1.5rem;
            }}
            
            .left-content li {{
                margin-bottom: 0.5rem;
                position: relative;
            }}
            
            /* Responsive styles */
            @media (max-width: 1200px) {{
                .left-content h1 {{
                    font-size: 2.5rem;
                }}
                
                .left-content p, .left-content ul {{
                    font-size: 1rem;
                }}
                
                .left-panel {{
                    padding: 3rem;
                }}
            }}
            
            @media (max-width: 992px) {{
                .left-panel {{
                    height: auto;
                    min-height: 300px;
                    padding: 2rem;
                }}
                
                .left-content h1 {{
                    font-size: 2rem;
                    margin-bottom: 1rem;
                }}
                
                .logo-left {{
                    height: 60px;
                    margin-bottom: 1rem;
                }}
                
                .left-content ul {{
                    margin-top: 1rem;
                    line-height: 1.8;
                }}
            }}
            
            @media (max-width: 768px) {{
                .left-panel {{
                    height: 70vh;
                    min-height: 30px;
                    padding: -1rem;
                }}
                
                .login-container {{
                    position: relative;
                    height: auto;
                    padding: 2rem 1.5rem;
                    width: calc(100% - 3rem);
                }}
            }}
        </style>
        
        <div class="left-panel">
            <div class="left-content">
                <img class="logo-left" src="https://files.logomakr.com/4qwxLL-LogoMakr.png" alt="EduVATE Logo">
                <h1>Welcome to EduVATE</h1>
                <p>Transform your learning experience with our comprehensive learning management system designed for modern education.</p>
                <ul>
                    <li>📊 Real-time analytics dashboard</li>
                    <li>📚 Centralized digital resources</li>
                    <li>🤝 Collaborative learning tools</li>
                    <li>🎯 Personalized learning paths</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Right column with login tabs
    with col2:
        st.markdown("""
        <style>
           
            .stApp > footer {visibility: hidden;}
            .stApp {background: linear-gradient(to bottom right, #f8fafc 0%, #f1f5f9 100%);}
            
            .login-container {
                
                position: absolute;
                padding: 2rem 3rem;
                height: 80vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
                width: calc(100% - 6rem);
            }
            
            .logo-right-container {
                text-align: center;
                margin-bottom: 2rem;
            }
            
            .logo-right {
                height: 70px;
                width: auto;
                transition: all 0.3s ease;
            }
            
            .logo-right:hover {
                transform: scale(1.05);
            }
            
            .login-header {
                margin-bottom: 2.5rem;
                text-align: center;
            }
            
            .login-header h2 {
                color: #166088;
                font-size: 1.8rem;
                margin-bottom: 0.5rem;
            }
            
            .login-header p {
                color: #666;
                font-size: 1rem;
            }
            
            .stTabs [data-baseweb="tab-list"] {
                gap: 0.5rem;
                margin-bottom: 2rem;
            }
            
            .stTabs [data-baseweb="tab"] {
                height: 2.8rem;
                padding: 0 1.5rem;
                border-radius: 8px 8px 0 0;
                font-weight: 600;
                background-color: #f0f2f6;
                transition: all 0.2s ease;
            }
            
            .stTabs [aria-selected="true"] {
                background-color: #166088 !important;
                color: white !important;
            }
            
            .stTabs [data-baseweb="tab"]:hover:not([aria-selected="true"]) {
                background-color: #e1e5eb;
            }
            
            .stForm {
                border: 1px solid #e1e4e8;
                border-radius: 12px;
                padding: 2rem;
                box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                background: white;
            }
            
            .stTextInput input, .stTextInput input:focus {
                border-radius: 8px !important;
                border: 1px solid #ddd !important;
                box-shadow: none !important;
            }
            
            /* Enhanced login button styles */
            .stButton button {
                background-color: #166088 !important;
                color: white !important;
                border-radius: 8px !important;
                padding: 0.75rem 1.5rem !important;
                font-weight: 600 !important;
                transition: all 0.2s !important;
                border: none !important;
                font-size: 1rem !important;
                width: 100% !important;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
            }
            
            .stButton button:hover {
                background-color: #0f4b6e !important;
                transform: translateY(-2px) !important;
                box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
            }
            
            .stButton button:active {
                transform: translateY(0) !important;
            }
            
            /* Footer links */
            .auth-footer {
                margin-top: 2rem;
                text-align: center;
                font-size: 0.85rem;
                color: #666;
                border-top: 1px solid #eee;
                padding-top: 1rem;
            }
            
            .auth-footer a {
                color: #166088;
                text-decoration: none;
                margin: 0 0.5rem;
                transition: color 0.2s;
            }
            
            .auth-footer a:hover {
                color: #0f4b6e;
                text-decoration: underline;
            }
            
            /* Responsive styles */
            @media (max-width: 1200px) {
                .login-container {
                    padding: 2rem;
                    width: calc(100% - 4rem);
                }
                
                .login-header h2 {
                    font-size: 1.6rem;
                }
                
                .stTabs [data-baseweb="tab"] {
                    padding: 0 1rem;
                    height: 2.5rem;
                    font-size: 0.9rem;
                }
                
                .stForm {
                    padding: 1.5rem;
                }
            }
            
            @media (max-width: 992px) {
                .login-container {
                    height: auto;
                    padding-bottom: 3rem;
                }
                
                .logo-right {
                    height: 60px;
                }
                
                .login-header {
                    margin-bottom: 1.5rem;
                }
                
                .stTabs [data-baseweb="tab-list"] {
                    margin-bottom: 1.5rem;
                }
            }
            
            @media (max-width: 768px) {
                .login-container {
                    position: relative;
                    padding: 1.5rem;
                    width: calc(100% - 3rem);
                }
                
                .logo-right {
                    height: 50px;
                }
                
                .login-header h2 {
                    font-size: 1.4rem;
                }
                
                .stTabs [data-baseweb="tab"] {
                    height: 2.2rem;
                    padding: 0 0.75rem;
                    font-size: 0.8rem;
                }
                
                .stForm {
                    padding: 1rem;
                }
                
                .auth-footer {
                    font-size: 0.8rem;
                }
            }
            
            @media (max-width: 576px) {
                .login-container {
                    
                    padding: 1rem;
                    width: calc(100% - 2rem);
                }
                
                .logo-right-container {
                    margin-bottom: 1rem;
                }
                
                .login-header {
                    margin-bottom: 1rem;
                }
                
                .login-header h2 {
                    font-size: 1.3rem;
                }
                
                .login-header p {
                    font-size: 0.9rem;
                }
                
                .stTabs [data-baseweb="tab-list"] {
                    gap: 0.25rem;
                    margin-bottom: 1rem;
                }
                
                .stTabs [data-baseweb="tab"] {
                    height: 2rem;
                    padding: 0 0.5rem;
                    font-size: 0.75rem;
                }
                
                .auth-footer {
                    margin-top: 1rem;
                    padding-top: 0.75rem;
                }
            }
        </style>
        
        
        """, unsafe_allow_html=True)
        
        # Render login tabs inside the right container
        tab1, tab2, tab3 = st.tabs(["Admin", "Instructor", "Learner"])

        with tab1:
            with st.form("admin_login"):
                st.subheader("Admin Portal")
                user = st.text_input("Username", key="admin_user", placeholder="Enter admin username")
                pwd = st.text_input("Password", type="password", key="admin_pwd", placeholder="••••••••")
                if st.form_submit_button("Login", use_container_width=True, type="primary"):
                    admin = admin_login(user, pwd)
                    if admin:
                        st.session_state.auth = {'logged_in': True, 'user_type': 'admin', 'user_data': admin}
                        st.rerun()
                    else:
                        st.error("Invalid credentials")

        with tab2:
            with st.form("teacher_login"):
                st.subheader("Instructor Access")
                teacher_id = st.text_input("Instructor ID", key="teacher_id", placeholder="Enter your instructor ID")
                pwd = st.text_input("Password", type="password", key="teacher_pwd", placeholder="••••••••")
                if st.form_submit_button("Login", use_container_width=True, type="primary"):
                    teacher = teacher_login(teacher_id, pwd)
                    if teacher:
                        st.session_state.auth = {'logged_in': True, 'user_type': 'teacher', 'user_data': teacher}
                        st.rerun()
                    else:
                        st.error("Invalid credentials")

        with tab3:
            with st.form("student_login"):
                st.subheader("Learner Portal")
                student_user = st.text_input("Username", key="student_user", placeholder="Enter student username")
                pwd = st.text_input("Password", type="password", key="student_pwd", placeholder="••••••••")
                if st.form_submit_button("Login", use_container_width=True, type="primary"):
                    student = student_login(student_user, pwd)
                    if student:
                        st.session_state.auth = {'logged_in': True, 'user_type': 'student', 'user_data': student}
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
        
        # Add footer links
        st.markdown("""
            <div class="auth-footer">
                <a href="#">Privacy Policy</a> • 
                <a href="#">Terms of Service</a> • 
                <a href="#">Help Center</a> • 
                <a href="#">Contact Support</a>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)


def main():
    st.set_page_config(layout="wide")
    
    
    set_custom_style()
    # Initialize database and session
    if not init_db():
        st.error("Failed to initialize database")
        return
    
    if 'auth' not in st.session_state:
        st.session_state.auth = {
            'logged_in': False,
            'user_type': None,  # 'admin', 'teacher', or 'student'
            'user_data': None
        }
    
    # ===== AUTHENTICATION SCREENS =====
    
    if not st.session_state.auth['logged_in']:
        render_auth_screen()
    else:
        if st.session_state.auth['user_type'] == 'admin':
            render_admin_dashboard()
        elif st.session_state.auth['user_type'] == 'teacher':
            render_teacher_dashboard()
        else:
            render_student_dashboard()

if __name__ == "__main__":
    main()
