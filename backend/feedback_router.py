from fastapi import APIRouter, Depends, HTTPException, Body, Request
from models import User, UserFeedback
from database import get_db
from sqlalchemy.orm import Session
from audit_logger import audit_logger
from schemas import FeedbackIn
from typing import Optional
from jose import jwt, JWTError
import os

router = APIRouter(prefix="/feedback", tags=["Feedback"])

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

async def get_optional_user(request: Request, db: Session = Depends(get_db)):
    """
    Optional user dependency for feedback.
    If no token or invalid token, returns None (guest).
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        user = db.query(User).filter(User.email == email).first()
        return user
    except (JWTError, Exception):
        return None

@router.post("/")
async def submit_feedback(
    request: Request,
    feedback: FeedbackIn,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Submit manual feedback for AI responses.
    Stores minimal metadata for internal improvement.
    """
    # Check for existing feedback to prevent duplicates if query_id is provided
    if feedback.query_id:
        existing = db.query(UserFeedback).filter(UserFeedback.query_id == feedback.query_id).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Feedback already exists for this query."
            )

    try:
        new_feedback = UserFeedback(
            query_id=feedback.query_id,
            user_id=current_user.id if current_user else None,
            helpful=1 if feedback.helpful else 0,
            reason=feedback.reason,
            comment=feedback.comment,
            model_used=feedback.model_used,
            confidence_score=feedback.confidence_score
        )
        db.add(new_feedback)
        db.commit()
        
        await audit_logger.log_event(
            action="USER_FEEDBACK",
            status="SUCCESS",
            user_id=current_user.id if current_user else None,
            request=request,
            metadata={
                "helpful": feedback.helpful,
                "reason": feedback.reason,
                "has_comment": bool(feedback.comment)
            }
        )
        
        return {"status": "success", "message": "Thank you for your valuable feedback."}
    except Exception as e:
        print(f"❌ Feedback Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to store feedback.")
