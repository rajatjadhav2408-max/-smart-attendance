from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from models import db, Teacher, Student, Attendance, Notification
from auth import bcrypt, encode_auth_token, token_required
from datetime import datetime, date
import os

app = Flask(__name__)
CORS(app)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
bcrypt.init_app(app)

# Create tables
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    teacher = Teacher.query.filter_by(username=data.get('username')).first()
    if teacher and bcrypt.check_password_hash(teacher.password, data.get('password')):
        token = encode_auth_token(teacher.id)
        return jsonify({
            'token': token,
            'teacher': {
                'id': teacher.id,
                'name': teacher.name,
                'department': teacher.department
            }
        })
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/api/students', methods=['GET'])
@token_required
def get_students(current_user_id):
    students = Student.query.all()
    return jsonify([{
        'id': s.id,
        'roll_number': s.roll_number,
        'name': s.name,
        'department': s.department,
        'semester': s.semester,
        'parent_mobile': s.parent_mobile
    } for s in students])

@app.route('/api/attendance', methods=['POST'])
@token_required
def mark_attendance(current_user_id):
    data = request.get_json()
    subject = data.get('subject')
    lecture_num = data.get('lecture_number')
    attendance_date_str = data.get('date') # Expected YYYY-MM-DD
    absent_roll_numbers = [r.strip() for r in str(data.get('absent_rolls')).split(',') if r.strip()]
    
    attendance_date = datetime.strptime(attendance_date_str, '%Y-%m-%d').date()
    
    all_students = Student.query.all()
    notifications_created = []

    for student in all_students:
        status = 'Absent' if student.roll_number in absent_roll_numbers else 'Present'
        
        # Save attendance record
        new_attendance = Attendance(
            student_id=student.id,
            subject=subject,
            lecture_number=lecture_num,
            date=attendance_date,
            status=status
        )
        db.session.add(new_attendance)
        
        if status == 'Absent':
            # Logic 4: Automatic Parent Alert
            msg = f"Alert: Your child {student.name} (Roll: {student.roll_number}) was ABSENT for {subject} (Lec {lecture_num}) on {attendance_date}."
            notif = Notification(student_id=student.id, type='Alert', message=msg)
            db.session.add(notif)
            notifications_created.append({'roll': student.roll_number, 'msg': msg})

            # Logic 5a: Same subject 2+ absences
            subject_absences = Attendance.query.filter_by(student_id=student.id, subject=subject, status='Absent').count()
            if subject_absences >= 2:
                msg_warning = f"Warning: {student.name} has missed {subject} {subject_absences} times. Please ensure regular attendance."
                db.session.add(Notification(student_id=student.id, type='Subject Warning', message=msg_warning))

            # Logic 5b: > 4 lectures in one day
            daily_absences = Attendance.query.filter_by(student_id=student.id, date=attendance_date, status='Absent').count()
            if daily_absences >= 4:
                msg_critical = f"CRITICAL: {student.name} has missed {daily_absences} lectures today! Immediate action required."
                db.session.add(Notification(student_id=student.id, type='Critical', message=msg_critical))

        # Logic 5c: Attendance < 75%
        total_lectures = Attendance.query.filter_by(student_id=student.id).count()
        total_present = Attendance.query.filter_by(student_id=student.id, status='Present').count()
        if total_lectures > 5: # Start checking after a few lectures
            percentage = (total_present / total_lectures) * 100
            if percentage < 75:
                msg_low = f"Low Attendance Warning: {student.name}'s attendance is {percentage:.2f}%, which is below the required 75%."
                # Avoid duplicate low attendance notifs for same day
                existing = Notification.query.filter(Notification.student_id == student.id, Notification.type == 'Low Attendance', db.func.date(Notification.date) == date.today()).first()
                if not existing:
                    db.session.add(Notification(student_id=student.id, type='Low Attendance', message=msg_low))

    db.session.commit()
    return jsonify({'message': 'Attendance marked successfully', 'notifications': notifications_created})

@app.route('/api/analytics', methods=['GET'])
@token_required
def get_analytics(current_user_id):
    # Most absent students
    absent_data = db.session.query(Student.name, db.func.count(Attendance.id)).join(Attendance).filter(Attendance.status == 'Absent').group_by(Student.id).order_by(db.func.count(Attendance.id).desc()).limit(5).all()
    
    # Subject-wise attendance (avg)
    subject_data = db.session.query(Attendance.subject, db.func.count(Attendance.id)).filter(Attendance.status == 'Present').group_by(Attendance.subject).all()
    
    # Total stats
    total_students = Student.query.count()
    total_notifications = Notification.query.count()
    
    # Risky students (< 75%)
    risky_students = []
    all_students = Student.query.all()
    for s in all_students:
        total = Attendance.query.filter_by(student_id=s.id).count()
        present = Attendance.query.filter_by(student_id=s.id, status='Present').count()
        if total > 0:
            perc = (present / total) * 100
            if perc < 75:
                risky_students.append({'name': s.name, 'roll': s.roll_number, 'percentage': round(perc, 2)})

    return jsonify({
        'most_absent': [{'name': r[0], 'count': r[1]} for r in absent_data],
        'subject_stats': [{'subject': r[0], 'presents': r[1]} for r in subject_data],
        'total_students': total_students,
        'total_notifications': total_notifications,
        'risky_students': risky_students[:10]
    })

@app.route('/api/notifications', methods=['GET'])
@token_required
def get_notifications(current_user_id):
    notifs = Notification.query.order_by(Notification.date.desc()).limit(50).all()
    return jsonify([{
        'id': n.id,
        'student_name': n.student.name,
        'roll_number': n.student.roll_number,
        'type': n.type,
        'message': n.message,
        'date': n.date.strftime('%Y-%m-%d %H:%M')
    } for n in notifs])

if __name__ == '__main__':
    app.run(debug=True, port=5000)
