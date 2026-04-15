import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Assessment, UserFramework
from routes.deps import get_current_user

router = APIRouter(prefix="/analyze", tags=["analyze"])

# Mock HAIG gap data — structured for multi-framework mapping
MOCK_GAPS = [
    {
        "id": "GAP-001", "title": "Missing AI Risk Policy",
        "severity": "HIGH", "domain": "AI Governance",
        "frameworks": ["EU AI Act", "ISO 42001", "NIST AI RMF"],
        "required_action": "Draft and approve an AI Risk Management Policy covering risk identification, assessment, and mitigation procedures.",
        "template": "AI Governance Policy Template",
        "status": "open", "evidence": "Missing",
    },
    {
        "id": "GAP-002", "title": "No Bias Testing Framework",
        "severity": "HIGH", "domain": "Model Fairness",
        "frameworks": ["EU AI Act", "ISO 42001", "NIST AI RMF", "NIST CSF"],
        "required_action": "Implement a bias detection and testing process for all AI models before deployment.",
        "template": "AI Fairness & Bias Testing Template",
        "status": "open", "evidence": "Missing",
    },
    {
        "id": "GAP-003", "title": "Incomplete Data Lineage Documentation",
        "severity": "MEDIUM", "domain": "Data Management",
        "frameworks": ["GDPR", "ISO 42001", "HIPAA"],
        "required_action": "Document full data lineage including sources, transformations, and storage for all training datasets.",
        "template": "Data Governance & Lineage Template",
        "status": "open", "evidence": "Partial",
    },
    {
        "id": "GAP-004", "title": "Lack of Explainability Documentation",
        "severity": "MEDIUM", "domain": "Transparency",
        "frameworks": ["EU AI Act", "GDPR", "AIHCS"],
        "required_action": "Produce model explainability reports for all high-risk AI systems.",
        "template": "AI Transparency & Explainability Template",
        "status": "open", "evidence": "Partial",
    },
    {
        "id": "GAP-005", "title": "No Human Oversight Process",
        "severity": "HIGH", "domain": "AI Governance",
        "frameworks": ["EU AI Act", "NIST AI RMF", "AIHCS"],
        "required_action": "Define and implement human-in-the-loop oversight procedures for high-risk AI decisions.",
        "template": "Human Oversight & Control Template",
        "status": "open", "evidence": "Missing",
    },
    {
        "id": "GAP-006", "title": "Missing Model Cards",
        "severity": "MEDIUM", "domain": "Documentation",
        "frameworks": ["ISO 42001", "NIST AI RMF", "EU AI Act"],
        "required_action": "Create model cards for all deployed AI models documenting purpose, performance, and limitations.",
        "template": "Model Documentation Template",
        "status": "open", "evidence": "Missing",
    },
    {
        "id": "GAP-007", "title": "Unvalidated Third-Party Models",
        "severity": "HIGH", "domain": "Supply Chain",
        "frameworks": ["ISO 42001", "NIST CSF", "SOC 2"],
        "required_action": "Establish a third-party AI model validation and vendor risk assessment process.",
        "template": "Third-Party AI Risk Template",
        "status": "open", "evidence": "Missing",
    },
    {
        "id": "GAP-008", "title": "No Incident Response Plan for AI",
        "severity": "HIGH", "domain": "Risk Management",
        "frameworks": ["ISO 27001", "NIST CSF", "SOC 2", "HIPAA"],
        "required_action": "Develop an AI-specific incident response plan covering detection, containment, and recovery.",
        "template": "AI Incident Response Template",
        "status": "open", "evidence": "Missing",
    },
    {
        "id": "GAP-009", "title": "Insufficient Access Controls on AI Systems",
        "severity": "LOW", "domain": "Security",
        "frameworks": ["ISO 27001", "SOC 2", "PCI DSS", "NIST CSF"],
        "required_action": "Implement role-based access controls and audit logging for all AI system interfaces.",
        "template": "Access Control & Security Template",
        "status": "open", "evidence": "Partial",
    },
    {
        "id": "GAP-010", "title": "Outdated Privacy Impact Assessment",
        "severity": "LOW", "domain": "Privacy",
        "frameworks": ["GDPR", "HIPAA", "US State AI and Privacy Regulations"],
        "required_action": "Conduct and update Privacy Impact Assessments for all AI systems processing personal data.",
        "template": "Privacy Impact Assessment Template",
        "status": "open", "evidence": "Partial",
    },
]


def build_framework_scores(gaps: list, selected_frameworks: list) -> list:
    result = []
    for fw in selected_frameworks:
        fw_gaps = [g for g in gaps if fw in g["frameworks"]]
        high = sum(1 for g in fw_gaps if g["severity"] == "HIGH")
        medium = sum(1 for g in fw_gaps if g["severity"] == "MEDIUM")
        low = sum(1 for g in fw_gaps if g["severity"] == "LOW")
        total = len(fw_gaps)
        score = max(0, 100 - (high * 15 + medium * 8 + low * 3))
        status = "critical" if high > 0 else "warning" if medium > 0 else "good"
        result.append({
            "framework": fw, "score": score,
            "gap_count": total, "high": high, "medium": medium, "low": low,
            "status": status,
        })
    return result


@router.post("")
def analyze(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = int(user["sub"])

    # Always return dummy data regardless of file content
    assessment = db.query(Assessment).filter(
        Assessment.user_id == user_id
    ).order_by(Assessment.id.desc()).first()

    selected = [
        r.framework_name for r in
        db.query(UserFramework).filter(UserFramework.user_id == user_id).all()
    ]
    if not selected:
        selected = ["EU AI Act", "ISO 42001", "NIST AI RMF"]

    # Filter gaps to only those relevant to selected frameworks
    relevant_gaps = [g for g in MOCK_GAPS if any(f in selected for f in g["frameworks"])]
    # Trim frameworks on each gap to only selected ones
    filtered_gaps = [
        {**g, "frameworks": [f for f in g["frameworks"] if f in selected]}
        for g in relevant_gaps
    ]

    high_count = sum(1 for g in filtered_gaps if g["severity"] == "HIGH")
    medium_count = sum(1 for g in filtered_gaps if g["severity"] == "MEDIUM")
    low_count = sum(1 for g in filtered_gaps if g["severity"] == "LOW")
    overall_score = max(0, 100 - (high_count * 12 + medium_count * 6 + low_count * 2))

    result = {
        "overall_score": overall_score,
        "total_gaps": len(filtered_gaps),
        "high": high_count,
        "medium": medium_count,
        "low": low_count,
        "selected_frameworks": selected,
        "framework_scores": build_framework_scores(filtered_gaps, selected),
        "gaps": filtered_gaps,
    }

    if assessment:
        assessment.response_json = json.dumps(result)
        db.commit()

    return {"assessment_id": assessment.id if assessment else 0, "result": result}
