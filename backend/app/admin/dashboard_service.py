# backend/dashboard_service.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from app.database.mongo_memory import get_full_history_for_dashboard, get_reports_history, clear_user_memory
from app.auth.logic.auth import get_current_user
from app.models.models import User, AuditLog, Profile
from app.database.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import desc

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/audit-logs")
def get_audit_logs(
    limit: int = 50,
    offset: int = 0,
    action: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetch audit logs for monitoring and debugging.
    In a production app, this should be restricted to 'admin' role.
    """
    query = db.query(AuditLog)
    
    if action:
        query = query.filter(AuditLog.action == action)
        
    logs = query.order_by(desc(AuditLog.timestamp)).offset(offset).limit(limit).all()
    
    return logs

@router.get("/history", response_model=List[Dict[str, Any]])
def get_user_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        history = get_full_history_for_dashboard(str(current_user.id), limit=100)
        
        # Get patient name from profile
        profile = db.query(Profile).filter(Profile.email == current_user.email).first()
        patient_name = profile.patient_name if (profile and profile.patient_name) else "Patient"
        
        # Inject patient name into history
        if history:
            for msg in history:
                if isinstance(msg, dict):
                    msg["patient_name"] = patient_name
            
        return history
    except Exception as e:
        print(f"❌ Error in get_user_history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("/reports", response_model=List[Dict[str, Any]])
def get_user_reports(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Returns only messages that are qualified as reports.
    """
    try:
        reports = get_reports_history(str(current_user.id), limit=100)
        
        # Get patient name from profile
        profile = db.query(Profile).filter(Profile.email == current_user.email).first()
        patient_name = profile.patient_name if (profile and profile.patient_name) else "Patient"
        
        # Inject patient name into reports
        if reports:
            for report in reports:
                if isinstance(report, dict):
                    report["patient_name"] = patient_name
            
        return reports
    except Exception as e:
        print(f"❌ Error in get_user_reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.delete("/history")
def clear_history(current_user: User = Depends(get_current_user)):
    clear_user_memory(str(current_user.id))
    return {"message": "Chat history cleared successfully"}
def extract_recent_symptoms(history: List[Dict[str, Any]]) -> str:
    """
    Extracts only recent USER symptom text (last 3 messages).
    """
    symptoms = [
        h["content"]
        for h in history
        if h.get("role") == "user"
    ]
    return " ".join(symptoms[-3:])
