from app import app, Teacher, bcrypt
with app.app_context():
    t = Teacher.query.filter_by(username='admin').first()
    if t:
        print(f"User: {t.username}")
        print(f"Hash in DB: {t.password}")
        is_match = bcrypt.check_password_hash(t.password, 'password123')
        print(f"Password 'password123' match: {is_match}")
    else:
        print("User not found")
