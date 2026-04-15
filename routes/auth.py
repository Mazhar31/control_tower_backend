from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import SignupRequest, SignupResponse, LoginRequest, TokenResponse, ChangePasswordRequest
from auth import hash_password, verify_password, create_access_token
from routes.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(name=body.name, email=body.email, hashed_password=hash_password(body.password), role="user")
    db.add(user)
    db.commit()
    return SignupResponse(message="Account created successfully. Please log in.")


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    return TokenResponse(access_token=token, name=user.name, role=user.role)


@router.put("/change-password")
def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == int(current_user["sub"])).first()
    if not user or not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.hashed_password = hash_password(body.new_password)
    db.commit()
    return {"message": "Password updated successfully"}
