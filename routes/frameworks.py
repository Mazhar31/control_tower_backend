from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import UserFramework
from schemas import FrameworkSelectRequest, FrameworkListResponse
from routes.deps import get_current_user

VALID_FRAMEWORKS = {
    "EU AI Act", "ISO 42001", "NIST AI RMF", "NIST CSF", "ISO 27001",
    "SOC 2", "PCI DSS", "ISO 9001", "21 CFR Part 11", "GDPR",
    "HIPAA", "US State AI and Privacy Regulations", "AIHCS",
}

router = APIRouter(prefix="/frameworks", tags=["frameworks"])


@router.post("/select")
def select_frameworks(
    body: FrameworkSelectRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    invalid = [f for f in body.frameworks if f not in VALID_FRAMEWORKS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown frameworks: {invalid}")

    db.query(UserFramework).filter(UserFramework.user_id == int(user["sub"])).delete()
    for name in body.frameworks:
        db.add(UserFramework(user_id=int(user["sub"]), framework_name=name))
    db.commit()
    return {"message": "Frameworks saved", "count": len(body.frameworks)}


@router.get("/user", response_model=FrameworkListResponse)
def get_user_frameworks(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    rows = db.query(UserFramework).filter(UserFramework.user_id == int(user["sub"])).all()
    return FrameworkListResponse(frameworks=[r.framework_name for r in rows])
