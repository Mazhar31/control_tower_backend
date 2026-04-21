import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User, Assessment
from schemas import AdminCreateUserRequest, AdminUserResponse
from auth import hash_password
from routes.deps import get_current_user
from typing import List

DEFAULT_PASSWORD = "Qwerty@123"

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/users", response_model=List[AdminUserResponse])
def list_users(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return db.query(User).filter(User.role == "user").all()


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id, User.role == "user").first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()


@router.post("/users", response_model=AdminUserResponse, status_code=201)
def create_user(
    body: AdminCreateUserRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        name=body.name,
        email=body.email,
        hashed_password=hash_password(DEFAULT_PASSWORD),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/assessments")
def list_assessments(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    rows = (
        db.query(Assessment, User.name, User.email)
        .join(User, Assessment.user_id == User.id)
        .order_by(Assessment.id.desc())
        .all()
    )
    result = []
    for assessment, user_name, user_email in rows:
        report_url = None
        if assessment.response_json:
            try:
                report_url = json.loads(assessment.response_json).get("report_url")
            except Exception:
                pass
        result.append({
            "id": assessment.id,
            "user_name": user_name,
            "user_email": user_email,
            "company_name": assessment.company_name,
            "system_name": assessment.system_name,
            "assessment_date": assessment.assessment_date,
            "risk_tier": assessment.risk_tier,
            "created_at": assessment.created_at.isoformat() if assessment.created_at else None,
            "report_url": report_url,
        })
    return result
