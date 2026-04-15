from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, server_default="user")  # "user" | "admin"
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Assessment(Base):
    __tablename__ = "assessments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    system_name = Column(String, nullable=True)
    assessment_date = Column(String, nullable=True)
    risk_tier = Column(String, nullable=True)
    response_json = Column(Text, nullable=True)
    uploaded_file_name = Column(String, nullable=True)
    uploaded_file_path = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
