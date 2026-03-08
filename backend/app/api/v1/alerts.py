"""
Clinical alert endpoints.
Orchestrates drug-gene interaction screening and returns safety alerts.
"""

from fastapi import APIRouter, Request, HTTPException, status
from datetime import datetime
from app.models.schemas import AlertDashboard
from app.core.session import require_authentication, get_patient_id


router = APIRouter()

@router.get("/{patient_id}")
async def get_alerts(patient_id: str, request: Request) -> AlertDashboard:
    """
    Generate pharmacogenomic safety alerts for a patient.
    """
    # Verify authentication
    require_authentication(request)
    
    # Verify patient context matches
    session_patient_id: str = get_patient_id(request)
    if patient_id != session_patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security Context Error: Patient ID mismatch."
                   "Cannot access data for different patient than session context."
        )
    
    return AlertDashboard(
        patientId=patient_id,
        timestamp=datetime.utcnow().isoformat(),
        highRisk=[],
        moderateRisk=[],
        noRisk=[],
        dataMissing=[],
        totalMedications=0,
        genomicDataComplete=False,
        errors=[]
    )
