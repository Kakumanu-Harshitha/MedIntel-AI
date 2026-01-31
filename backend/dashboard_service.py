# backend/dashboard_service.py
import os
import sys

# Ensure the backend directory is in the python path for local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from mongo_memory import get_full_history_for_dashboard, clear_user_memory
from auth import get_current_user
from models import User, AuditLog
from database import get_db
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
def get_user_history(current_user: User = Depends(get_current_user)):
    return get_full_history_for_dashboard(str(current_user.id), limit=100)

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
