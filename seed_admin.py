"""
Run this once to create the admin user:
  cd backend
  python3 seed_admin.py
"""
from database import Base, engine, SessionLocal
from models import User
from auth import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    if db.query(User).filter(User.email == "admin@taiga.com").first():
        print("Admin already exists.")
    else:
        db.add(User(
            name="Admin",
            email="admin@taiga.com",
            hashed_password=hash_password("Admin@123"),
            role="admin",
        ))
        db.commit()
        print("Admin created.")
        print("  Email:    admin@taiga.com")
        print("  Password: Admin@123")
finally:
    db.close()
