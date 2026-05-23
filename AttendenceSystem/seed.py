from app import app, db, Teacher, Student, bcrypt

with app.app_context():
    # Clear existing data
    db.drop_all()
    db.create_all()

    # Create Teacher
    hashed_pw = bcrypt.generate_password_hash('password123').decode('utf-8')
    admin_teacher = Teacher(username='admin', password=hashed_pw, name='Prof. Sharma', department='Computer Science')
    db.session.add(admin_teacher)

    # Create Students
    students_data = [
        ('101', 'Aarav Patel', '9876543210', 'Computer Science', 4),
        ('102', 'Ishita Iyer', '9876543211', 'Computer Science', 4),
        ('103', 'Kabir Khan', '9876543212', 'Computer Science', 4),
        ('104', 'Meera Reddy', '9876543213', 'Computer Science', 4),
        ('105', 'Vivaan Singh', '9876543214', 'Information Technology', 4),
        ('106', 'Ananya Gupta', '9876543215', 'Information Technology', 4),
        ('107', 'Rohan Das', '9876543216', 'Electrical Eng', 4),
        ('108', 'Sanya Malhotra', '9876543217', 'Electrical Eng', 4),
        ('109', 'Aditya Verma', '9876543218', 'Mechanical Eng', 4),
        ('110', 'Zoya Ahmed', '9876543219', 'Mechanical Eng', 4),
    ]

    for roll, name, mob, dept, sem in students_data:
        s = Student(roll_number=roll, name=name, parent_mobile=mob, department=dept, semester=sem)
        db.session.add(s)

    db.session.commit()
    print("Database seeded successfully!")
