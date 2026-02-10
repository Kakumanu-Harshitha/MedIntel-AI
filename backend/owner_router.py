from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, String
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from database import get_db
from models import User, UserFeedback, AuditLog, SystemConfig
from auth.user_auth import get_current_owner
from audit_logger import audit_logger
import mongo_memory

router = APIRouter(prefix="/owner", tags=["Owner Dashboard"])

@router.get("/health-metrics")
async def get_health_metrics(db: Session = Depends(get_db), owner: User = Depends(get_current_owner)):
    """
    Returns high-level system health metrics.
    """
    try:
        # 1. Total Users
        total_users = db.query(User).count()
        
        # 2. Active Users (Today)
        today = datetime.now(timezone.utc).date()
        # Using cast for better compatibility with different DBs
        from sqlalchemy import cast, Date
        active_today = db.query(func.count(func.distinct(AuditLog.user_id)))\
            .filter(cast(AuditLog.timestamp, Date) == today).scalar()
            
        # 3. Active Users (Last 7 Days)
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        active_week = db.query(func.count(func.distinct(AuditLog.user_id)))\
            .filter(AuditLog.timestamp >= week_ago).scalar()
            
        # 4. Total Queries (Last 24h)
        day_ago = datetime.now(timezone.utc) - timedelta(days=1)
        total_queries = db.query(AuditLog).filter(
            AuditLog.timestamp >= day_ago,
            AuditLog.action == "AI_QUERY"
        ).count()
        
        # 5. Error Rate (Last 24h)
        errors = db.query(AuditLog).filter(
            AuditLog.timestamp >= day_ago,
            AuditLog.status == "FAILURE"
        ).count()
        error_rate = (errors / total_queries * 100) if total_queries > 0 else 0
        
        # 6. HITL Escalations (Total)
        hitl_escalations = db.query(AuditLog).filter(
            AuditLog.action == "HITL_ESCALATION"
        ).count()

        return {
            "total_users": total_users,
            "active_today": active_today or 0,
            "active_week": active_week or 0,
            "total_queries": total_queries,
            "error_rate": round(error_rate, 2),
            "hitl_escalations": hitl_escalations
        }
    except Exception as e:
        print(f"❌ Health Metrics Error: {str(e)}")
        # Return partial data or empty metrics instead of 500
        return {
            "total_users": 0,
            "active_today": 0,
            "active_week": 0,
            "total_queries": 0,
            "error_rate": 0,
            "hitl_escalations": 0,
            "db_error": str(e)
        }

@router.get("/satisfaction-metrics")
async def get_satisfaction_metrics(db: Session = Depends(get_db), owner: User = Depends(get_current_owner)):
    """
    Returns user satisfaction insights based on feedback.
    Prioritizes MongoDB feedback if available, otherwise falls back to SQL.
    """
    # Try MongoDB first
    if mongo_memory.feedback_collection is not None:
        metrics = mongo_memory.get_feedback_metrics()
        return {
            "helpfulness_rate": metrics["helpfulness_rate"],
            "total_feedback": metrics["total_feedback"],
            "reasons_breakdown": metrics["reasons_breakdown"],
            "recent_feedback": metrics["recent_feedback"],
            "avg_confidence": {
                "helpful": 0,
                "not_helpful": 0
            },
            "source": "mongodb"
        }

    # Fallback to SQL (Legacy)
    total_feedback = db.query(UserFeedback).count()
    helpful_count = db.query(UserFeedback).filter(UserFeedback.helpful == 1).count()
    helpfulness_rate = (helpful_count / total_feedback * 100) if total_feedback > 0 else 0
    
    # Negative feedback by reason
    reasons = db.query(UserFeedback.reason, func.count(UserFeedback.id)).filter(UserFeedback.helpful == 0).group_by(UserFeedback.reason).all()
    reasons_breakdown = {r[0]: r[1] for r in reasons}
    
    # Satisfaction vs Confidence (Average confidence score for helpful vs non-helpful)
    avg_conf_helpful = db.query(func.avg(UserFeedback.confidence_score)).filter(UserFeedback.helpful == 1).scalar() or 0
    avg_conf_not_helpful = db.query(func.avg(UserFeedback.confidence_score)).filter(UserFeedback.helpful == 0).scalar() or 0

    return {
        "helpfulness_rate": round(helpfulness_rate, 2),
        "total_feedback": total_feedback,
        "reasons_breakdown": reasons_breakdown,
        "avg_confidence": {
            "helpful": round(avg_conf_helpful, 4),
            "not_helpful": round(avg_conf_not_helpful, 4)
        }
    }

@router.get("/model-metrics")
async def get_model_metrics(db: Session = Depends(get_db), owner: User = Depends(get_current_owner)):
    """
    Returns model usage and routing transparency.
    """
    # Group by model_used in UserFeedback
    model_usage = db.query(UserFeedback.model_used, func.count(UserFeedback.id)).group_by(UserFeedback.model_used).all()
    model_counts = {m[0] or "unknown": m[1] for m in model_usage}
    
    # Fallback frequency (where action was IMAGE_MODALITY_DETECTION or HITL_ESCALATION)
    total_detections = db.query(AuditLog).filter(AuditLog.action.in_(["IMAGE_MODALITY_DETECTION", "AI_QUERY"])).count()
    
    fallbacks = db.query(AuditLog).filter(
        or_(
            and_(
                AuditLog.action == "IMAGE_MODALITY_DETECTION",
                func.cast(AuditLog.metadata_json["escalated"], String) == '"true"'
            ),
            AuditLog.action == "HITL_ESCALATION"
        )
    ).count()
    
    fallback_rate = (fallbacks / total_detections * 100) if total_detections > 0 else 0

    return {
        "model_counts": model_counts,
        "fallback_rate": round(fallback_rate, 2),
        "total_detections": total_detections
    }

@router.get("/security-metrics")
async def get_security_metrics(db: Session = Depends(get_db), owner: User = Depends(get_current_owner)):
    """
    Returns security and auth event metrics.
    """
    password_resets = db.query(AuditLog).filter(AuditLog.action.in_(["PASSWORD_RESET_CONFIRM", "PASSWORD_RESET"]), AuditLog.status == "SUCCESS").count()
    failed_logins = db.query(AuditLog).filter(AuditLog.action.in_(["USER_LOGIN", "LOGIN"]), AuditLog.status == "FAILURE").count()
    otp_failures = db.query(AuditLog).filter(AuditLog.action.in_(["TOTP_VERIFICATION", "OTP_VERIFY"]), AuditLog.status == "FAILURE").count()
    
    # Suspicious spikes (more than 10 failed logins in the last hour)
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_failed_logins = db.query(AuditLog).filter(
        AuditLog.action.in_(["USER_LOGIN", "LOGIN"]),
        AuditLog.status == "FAILURE",
        AuditLog.timestamp >= one_hour_ago
    ).count()

    return {
        "password_resets": password_resets,
        "failed_logins": failed_logins,
        "otp_failures": otp_failures,
        "recent_failed_logins_1h": recent_failed_logins,
        "suspicious_activity": recent_failed_logins > 10
    }

@router.get("/hitl-metrics")
async def get_hitl_metrics(db: Session = Depends(get_db), owner: User = Depends(get_current_owner)):
    """
    Returns detailed HITL (Human-in-the-loop) monitoring metrics.
    """
    total_detections = db.query(AuditLog).filter(AuditLog.action.in_(["IMAGE_MODALITY_DETECTION", "AI_QUERY"])).count()
    
    # Escalations are either IMAGE_MODALITY_DETECTION with escalated:true OR HITL_ESCALATION
    total_escalations = db.query(AuditLog).filter(
        or_(
            and_(
                AuditLog.action == "IMAGE_MODALITY_DETECTION",
                func.cast(AuditLog.metadata_json["escalated"], String) == '"true"'
            ),
            AuditLog.action == "HITL_ESCALATION"
        )
    ).count()
    
    escalation_rate = (total_escalations / total_detections * 100) if total_detections > 0 else 0
    
    # Recent escalations (last 10)
    recent_escalations = db.query(AuditLog).filter(
        or_(
            and_(
                AuditLog.action == "IMAGE_MODALITY_DETECTION",
                func.cast(AuditLog.metadata_json["escalated"], String) == '"true"'
            ),
            AuditLog.action == "HITL_ESCALATION"
        )
    ).order_by(desc(AuditLog.timestamp)).limit(10).all()
    
    # Breakdown by reason
    reasons_query = db.query(
        AuditLog.metadata_json
    ).filter(
        or_(
            and_(
                AuditLog.action == "IMAGE_MODALITY_DETECTION",
                func.cast(AuditLog.metadata_json["escalated"], String) == '"true"'
            ),
            AuditLog.action == "HITL_ESCALATION"
        )
    ).all()
    
    reasons_breakdown = {}
    for log in reasons_query:
        reason = log[0].get("reason", "Unknown") if log[0] else "Unknown"
        reasons_breakdown[reason] = reasons_breakdown.get(reason, 0) + 1

    return {
        "total_detections": total_detections,
        "total_escalations": total_escalations,
        "escalation_rate": round(escalation_rate, 2),
        "recent_escalations": [
            {
                "id": e.id,
                "timestamp": e.timestamp,
                "reason": e.metadata_json.get("reason", "Unknown") if e.metadata_json else "Unknown",
                "user_id": e.user_id,
                "metadata": e.metadata_json
            } for e in recent_escalations
        ],
        "reasons_breakdown": reasons_breakdown
    }

@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = 50,
    offset: int = 0,
    action: str = None,
    status: str = None,
    db: Session = Depends(get_db),
    owner: User = Depends(get_current_owner)
):
    """
    Enterprise-grade audit log viewer.
    """
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if status:
        query = query.filter(AuditLog.status == status)
        
    logs = query.order_by(desc(AuditLog.timestamp)).offset(offset).limit(limit).all()
    total = query.count()
    
    return {
        "logs": logs,
        "total": total
    }

@router.get("/toggles")
async def get_feature_toggles(db: Session = Depends(get_db), owner: User = Depends(get_current_owner)):
    """
    Returns all system feature toggles.
    """
    toggles = db.query(SystemConfig).all()
    return toggles

@router.post("/toggles")
async def update_feature_toggle(
    key: str,
    value: str,
    request: Request,
    db: Session = Depends(get_db),
    owner: User = Depends(get_current_owner)
):
    """
    Updates or creates a feature toggle with audit logging.
    """
    if value not in ["ON", "OFF"]:
        raise HTTPException(status_code=400, detail="Value must be 'ON' or 'OFF'")
        
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    old_value = config.value if config else "NONE"
    
    if config:
        config.value = value
    else:
        config = SystemConfig(key=key, value=value)
        db.add(config)
    
    db.commit()

    # Log the action
    await audit_logger.log_event(
        action="SYSTEM_TOGGLE_UPDATE",
        status="SUCCESS",
        user_id=owner.id,
        request=request,
        metadata={
            "toggle_key": key,
            "old_value": old_value,
            "new_value": value
        }
    )
    
    return {"status": "success", "key": key, "value": value}
