from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from models import db, Teacher, Student, Attendance, Notification
from auth import bcrypt, encode_auth_token, token_required
from datetime import datetime, date, timezone
import os

app = Flask(__name__)
CORS(app)

# Database Configuration
# Uses PostgreSQL in production (DATABASE_URL env var), SQLite locally
database_url = os.environ.get('DATABASE_URL', 'sqlite:///attendance.db')
# Render gives postgres:// but SQLAlchemy needs postgresql://
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
bcrypt.init_app(app)

# Create tables
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')  # serves from templates/index.html

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Username and password required'}), 400

    teacher = Teacher.query.filter_by(username=data.get('username')).first()
    if teacher and bcrypt.check_password_hash(teacher.password, data.get('password')):
        token = encode_auth_token(teacher.id)
        return jsonify({
            'token': token,
            'teacher': {
                'id': teacher.id,
                'name': teacher.name,
                'department': teacher.department,
                'username': teacher.username,
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

    subject = data.get('subject', '').strip()
    lecture_num = data.get('lecture_number')
    attendance_date_str = data.get('date', '').strip()

    if not subject:
        return jsonify({'message': 'Subject is required'}), 400
    if not lecture_num:
        return jsonify({'message': 'Lecture number is required'}), 400
    if not attendance_date_str:
        return jsonify({'message': 'Date is required'}), 400

    try:
        lecture_num = int(lecture_num)
    except (ValueError, TypeError):
        return jsonify({'message': 'Lecture number must be an integer'}), 400

    try:
        attendance_date = datetime.strptime(attendance_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'message': 'Invalid date format. Use YYYY-MM-DD'}), 400

    raw_absent = data.get('absent_rolls', '')
    if not isinstance(raw_absent, str):
        raw_absent = ''
    absent_roll_numbers = [r.strip() for r in raw_absent.split(',') if r.strip()]

    all_students = Student.query.all()
    notifications_created = []

    new_records = {}
    for student in all_students:
        status = 'Absent' if student.roll_number in absent_roll_numbers else 'Present'
        new_attendance = Attendance(
            student_id=student.id,
            subject=subject,
            lecture_number=lecture_num,
            date=attendance_date,
            status=status
        )
        db.session.add(new_attendance)
        new_records[student.id] = status

    db.session.flush()

    for student in all_students:
        status = new_records[student.id]

        if status == 'Absent':
            msg = (f"Alert: Your child {student.name} (Roll: {student.roll_number}) "
                   f"was ABSENT for {subject} (Lec {lecture_num}) on {attendance_date}.")
            notif = Notification(student_id=student.id, type='Alert', message=msg)
            db.session.add(notif)
            notifications_created.append({'roll': student.roll_number, 'msg': msg})

            subject_absences = Attendance.query.filter_by(
                student_id=student.id, subject=subject, status='Absent'
            ).count()
            if subject_absences >= 2:
                msg_warning = (f"Warning: {student.name} has missed {subject} "
                               f"{subject_absences} times. Please ensure regular attendance.")
                db.session.add(Notification(student_id=student.id, type='Subject Warning', message=msg_warning))

            daily_absences = Attendance.query.filter_by(
                student_id=student.id, date=attendance_date, status='Absent'
            ).count()
            if daily_absences >= 4:
                msg_critical = (f"CRITICAL: {student.name} has missed {daily_absences} "
                                f"lectures today! Immediate action required.")
                db.session.add(Notification(student_id=student.id, type='Critical', message=msg_critical))

        total_lectures = Attendance.query.filter_by(student_id=student.id).count()
        total_present = Attendance.query.filter_by(student_id=student.id, status='Present').count()

        if total_lectures > 5:
            percentage = (total_present / total_lectures) * 100
            if percentage < 75:
                msg_low = (f"Low Attendance Warning: {student.name}'s attendance is "
                           f"{percentage:.2f}%, which is below the required 75%.")
                existing = Notification.query.filter(
                    Notification.student_id == student.id,
                    Notification.type == 'Low Attendance',
                    db.func.date(Notification.date) == attendance_date
                ).first()
                if not existing:
                    db.session.add(Notification(student_id=student.id, type='Low Attendance', message=msg_low))

    db.session.commit()
    return jsonify({'message': 'Attendance marked successfully', 'notifications': notifications_created})


@app.route('/api/analytics', methods=['GET'])
@token_required
def get_analytics(current_user_id):
    absent_data = (
        db.session.query(Student.name, db.func.count(Attendance.id))
        .join(Attendance)
        .filter(Attendance.status == 'Absent')
        .group_by(Student.id)
        .order_by(db.func.count(Attendance.id).desc())
        .limit(5)
        .all()
    )

    subject_data = (
        db.session.query(Attendance.subject, db.func.count(Attendance.id))
        .filter(Attendance.status == 'Present')
        .group_by(Attendance.subject)
        .all()
    )

    total_students = Student.query.count()
    total_notifications = Notification.query.count()

    attendance_agg = (
        db.session.query(
            Student.id,
            Student.name,
            Student.roll_number,
            db.func.count(Attendance.id).label('total'),
            db.func.sum(
                db.case((Attendance.status == 'Present', 1), else_=0)
            ).label('present')
        )
        .outerjoin(Attendance, Attendance.student_id == Student.id)
        .group_by(Student.id)
        .all()
    )

    risky_students = []
    total_present_all = 0
    total_lectures_all = 0

    for row in attendance_agg:
        total = row.total or 0
        present = row.present or 0
        total_present_all += present
        total_lectures_all += total
        if total > 0:
            perc = (present / total) * 100
            if perc < 75:
                risky_students.append({
                    'name': row.name,
                    'roll': row.roll_number,
                    'percentage': round(perc, 2)
                })

    avg_attendance = (
        round((total_present_all / total_lectures_all) * 100, 1)
        if total_lectures_all > 0 else 0
    )

    return jsonify({
        'most_absent': [{'name': r[0], 'count': r[1]} for r in absent_data],
        'subject_stats': [{'subject': r[0], 'presents': r[1]} for r in subject_data],
        'total_students': total_students,
        'total_notifications': total_notifications,
        'risky_students': risky_students[:10],
        'avg_attendance': avg_attendance
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


@app.route('/api/notify_parent', methods=['POST'])
@token_required
def notify_parent(current_user_id):
    data = request.get_json()
    roll_number = data.get('roll_number', '').strip()
    if not roll_number:
        return jsonify({'message': 'roll_number is required'}), 400

    student = Student.query.filter_by(roll_number=roll_number).first()
    if not student:
        return jsonify({'message': 'Student not found'}), 404

    total = Attendance.query.filter_by(student_id=student.id).count()
    present = Attendance.query.filter_by(student_id=student.id, status='Present').count()
    perc = round((present / total) * 100, 2) if total > 0 else 0

    msg = (f"Manual Alert: Parent of {student.name} (Roll: {student.roll_number}) has been "
           f"notified. Current attendance: {perc}%. Please contact the college if needed.")
    notif = Notification(student_id=student.id, type='Manual Alert', message=msg)
    db.session.add(notif)
    db.session.commit()

    return jsonify({'message': f'Parent of {student.name} notified successfully.', 'mobile': student.parent_mobile})


if __name__ == '__main__':
    # Step 3 fix: read PORT from environment for Render/Railway/etc.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
