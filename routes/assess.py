import json
import os
import shutil
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
from database import get_db
from models import Assessment
from schemas import AssessmentSummary
from routes.deps import get_current_user
from leash_service import run_assessment
import httpx

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
ALLOWED_EXTS = {".pdf", ".docx"}

# ---------------------------------------------------------------------------
# Mock response for local dev fallback
# ---------------------------------------------------------------------------
USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"

MOCK_RESPONSE = {
    "session_id": "mock-session-001",
    "company_name": "Test Company",
    "system_name": "Customer Analytics AI",
    "assessment_date": "2026-01-01",
    "risk_tier": "High",
    "frameworks_triggered": ["EU AI Act", "ISO 42001"],
    "critical_count": 2,
    "high_count": 3,
    "medium_count": 4,
    "low_count": 1,
    "gap_findings": [
        {
            "finding_id": "GAP-001",
            "category": "AI Governance",
            "title": "No AI Governance Framework",
            "description": "No formal AI governance policy or accountability structure exists.",
            "severity": "Critical",
            "current_state": "No governance framework, policy, or AI Officer identified.",
            "required_state": "EU AI Act Art. 17 requires documented risk management system.",
            "remediation": "Implement HAIG AI Governance Charter.",
            "remediation_template": "AI Governance/HAIG AI Governance Charter.docx",
            "framework_map": {
                "EU AI Act": ["Art. 9", "Art. 17"],
                "ISO 42001": ["5.1", "6.1"],
            },
        },
        {
            "finding_id": "GAP-002",
            "category": "Model Fairness",
            "title": "No Bias Testing Framework",
            "description": "No bias detection or testing process exists for AI models.",
            "severity": "High",
            "current_state": "No bias testing in place.",
            "required_state": "ISO 42001 requires fairness evaluation.",
            "remediation": "Implement bias testing pipeline.",
            "remediation_template": "Model Fairness/HAIG Bias Testing Template.docx",
            "framework_map": {
                "EU AI Act": ["Art. 10"],
                "ISO 42001": ["8.4"],
            },
        },
        {
            "finding_id": "GAP-003",
            "category": "Transparency",
            "title": "Missing Model Cards",
            "description": "No model cards exist for deployed AI models.",
            "severity": "Medium",
            "current_state": "No documentation.",
            "required_state": "ISO 42001 requires model documentation.",
            "remediation": "Create model cards.",
            "remediation_template": "Documentation/HAIG Model Card Template.docx",
            "framework_map": {
                "ISO 42001": ["8.6"],
                "EU AI Act": ["Art. 13"],
            },
        },
    ],
    "framework_coverage": {
        "EU AI Act": {"gaps": 3, "pct_compliant": 42},
        "ISO 42001": {"gaps": 3, "pct_compliant": 55},
    },
    "shelby_controls": {
        "has_ai_usage_policy": False,
        "employee_ai_training": False,
        "ai_output_review_process": True,
        "dependency_risk_assessed": False,
    },
    "report_url": "https://example.com/mock-report.pdf",
}

router = APIRouter(prefix="/assess", tags=["assess"])


@router.post("")
async def submit_assessment(
    companyName: str = Form(...),
    systemName: str = Form(...),
    systemDescription: str = Form(...),
    industry: str = Form(...),
    geography: str = Form(...),
    usStates: str = Form(""),           # comma-separated
    selectedFrameworks: str = Form(...),  # comma-separated
    aihcsResponse: str = Form(...),
    deploymentStage: str = Form(...),
    dataTypes: str = Form(""),
    additionalContext: str = Form(""),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = int(user["sub"])

    # Handle optional file upload
    uploaded_file_name = None
    uploaded_file_path = None
    if file and file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTS:
            raise HTTPException(status_code=400, detail="Only PDF and DOCX files are accepted")
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        dest = os.path.join(UPLOAD_DIR, f"user{user_id}_{file.filename}")
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
        uploaded_file_name = file.filename
        uploaded_file_path = dest

    # Build intake payload
    intake_data = {
        "companyName": companyName,
        "systemName": systemName,
        "systemDescription": systemDescription,
        "industry": industry,
        "geography": geography,
        "usStates": [s.strip() for s in usStates.split(",") if s.strip()],
        "selectedFrameworks": ["EU AI Act", "ISO 42001", "HIPAA", "NIST AI RMF"],
        "aihcsResponse": aihcsResponse,
        "deploymentStage": deploymentStage,
        "dataTypes": dataTypes,
        "additionalContext": additionalContext,
    }

    # Call The Leash (or mock)
    if USE_MOCK:
        logger.info("[MOCK] Returning mock response — set USE_MOCK=false to call real API")
        result = MOCK_RESPONSE
    else:
        logger.info("[LEASH] Calling real API for user=%s company=%s system=%s", user_id, companyName, systemName)
        logger.info("[LEASH] Payload: %s", json.dumps(intake_data, indent=2))
        try:
            raw = await run_assessment(intake_data)
            # Real response wraps findings inside taiga_token — unwrap and merge
            taiga_token = raw.get("taiga_token", {})
            result = {
                **taiga_token,
                "report_url": raw.get("report_url", ""),
                "report_s3_key": raw.get("report_s3_key", ""),
                "total_findings": raw.get("total_findings", len(taiga_token.get("gap_findings", []))),
                "audit_summary": raw.get("audit_summary", {}),
            }
            logger.info("[LEASH] Success — session_id=%s risk_tier=%s findings=%s",
                result.get("session_id"), result.get("risk_tier"),
                len(result.get("gap_findings", [])))
        except httpx.TimeoutException:
            logger.error("[LEASH] Timed out after %ss", 420)
            raise HTTPException(status_code=504, detail="Assessment timed out. Please try again.")
        except Exception as e:
            logger.error("[LEASH] Failed: %s", str(e))
            raise HTTPException(status_code=502, detail=f"Assessment service error: {str(e)}")

    # Persist to DB
    assessment = Assessment(
        user_id=user_id,
        session_id=result.get("session_id"),
        company_name=result.get("company_name"),
        system_name=result.get("system_name"),
        assessment_date=result.get("assessment_date"),
        risk_tier=result.get("risk_tier"),
        response_json=json.dumps(result),
        uploaded_file_name=uploaded_file_name,
        uploaded_file_path=uploaded_file_path,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    return {"assessment_id": assessment.id, "result": result}


@router.get("/history")
def get_history(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = (
        db.query(Assessment)
        .filter(Assessment.user_id == int(user["sub"]))
        .order_by(Assessment.id.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "company_name": r.company_name,
            "system_name": r.system_name,
            "assessment_date": r.assessment_date,
            "risk_tier": r.risk_tier,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/{assessment_id}")
def get_assessment(assessment_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = db.query(Assessment).filter(
        Assessment.id == assessment_id,
        Assessment.user_id == int(user["sub"]),
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return {"assessment_id": row.id, "result": json.loads(row.response_json)}
