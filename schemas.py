from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class SignupResponse(BaseModel):
    message: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    name: str
    role: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class AdminCreateUserRequest(BaseModel):
    name: str
    email: EmailStr


class AdminUserResponse(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class IntakeRequest(BaseModel):
    companyName: str
    systemName: str
    systemDescription: str
    industry: str
    geography: str
    usStates: List[str] = []
    selectedFrameworks: List[str]
    aihcsResponse: str
    deploymentStage: str
    dataTypes: str = ""
    additionalContext: str = ""


class AssessmentSummary(BaseModel):
    id: int
    company_name: Optional[str]
    system_name: Optional[str]
    assessment_date: Optional[str]
    risk_tier: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
