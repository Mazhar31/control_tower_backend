import os
import shutil
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Assessment
from routes.deps import get_current_user

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
ALLOWED_TYPES = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"}
ALLOWED_EXTS = {".pdf", ".docx", ".txt"}

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT files are accepted")

    dest = os.path.join(UPLOAD_DIR, f"user{user['sub']}_{file.filename}")
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    assessment = Assessment(user_id=int(user["sub"]), file_path=dest)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    return {"message": "File uploaded", "assessment_id": assessment.id, "filename": file.filename}
