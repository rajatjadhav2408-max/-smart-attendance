from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# DATABASE CONFIG
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# INITIALIZE
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# ---------------- MODELS ---------------- #
class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    department = db.Column(db.String(100))
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roll_number = db.Column(db.String(20), unique=True)
    name = db.Column(db.String(100))
    department = db.Column(db.String(100))
    semester = db.Column(db.String(20))
    parent_mobile = db.Column(db.String(20))

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer)
    subject = db.Column(db.String(100))
    lecture_number = db.Column(db.Integer)
    date = db.Column(db.Date)
    status = db.Column(db.String(20))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer)
    type = db.Column(db.String(50))
    message = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.utcnow)

# CREATE DATABASE TABLES
with app.app_context():
    db.create_all()

# ---------------- ROUTES ---------------- #
@app.route('/')
def home():
    return render_template('index.html')

# LOGIN
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    teacher = Teacher.query.filter_by(username=username).first()
    if teacher and bcrypt.check_password_hash(teacher.password, password):
        return jsonify({
            "message": "Login successful",
            "teacher": teacher.name
        })
    return jsonify({"message": "Invalid credentials"}), 401

# GET STUDENTS
@app.route('/api/students', methods=['GET'])
def get_students():
    students = Student.query.all()
    return jsonify([
        {
            "id": s.id,
            "roll_number": s.roll_number,
            "name": s.name,
            "department": s.department,
            "semester": s.semester
        }
        for s in students
    ])

# MARK ATTENDANCE
@app.route('/api/attendance', methods=['POST'])
def mark_attendance():
    data = request.get_json()
    subject = data.get('subject')
    lecture_number = data.get('lecture_number')
    absent_rolls = data.get('absent_rolls', '')
    absent_roll_numbers = [r.strip() for r in absent_rolls.split(',') if r.strip()]
    
    students = Student.query.all()
    for student in students:
        status = "Absent" if student.roll_number in absent_roll_numbers else "Present"
        attendance = Attendance(
            student_id=student.id,
            subject=subject,
            lecture_number=lecture_number,
            date=datetime.now().date(),
            status=status
        )
        db.session.add(attendance)
    db.session.commit()
    return jsonify({"message": "Attendance marked successfully"})

# GET NOTIFICATIONS
@app.route('/api/notifications', methods=['GET'])
def notifications():
    notifs = Notification.query.all()
    return jsonify([
        {
            "id": n.id,
            "message": n.message,
            "type": n.type
        }
        for n in notifs
    ])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
