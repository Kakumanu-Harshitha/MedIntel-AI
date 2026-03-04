# backend/profile_router.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional
from database import get_db
from models import Profile, User as SQLUser  # for typing
from auth.router import get_current_user
from audit_logger import audit_logger
from schemas import ProfileIn, ProfileOut, TokenOut

router = APIRouter(prefix="/profile", tags=["Profile"])

@router.get("/status")
def get_auth_status(current_user: SQLUser = Depends(get_current_user)):
    """Quick check for OTP status without fetching full profile."""
    return {"otp_enabled": bool(current_user.otp_enabled)}

@router.post("/", response_model=ProfileOut, response_model_exclude_none=True)
async def create_or_update_profile(
    request: Request,
    profile_in: ProfileIn,
    current_user: SQLUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    email = current_user.email
    profile = db.query(Profile).filter(Profile.email == email).first()

    # Create new profile if not exists
    if not profile:
        profile = Profile(email=email)

    # Update only provided fields
    updated_fields = profile_in.dict(exclude_none=True)
    for key, value in updated_fields.items():
        setattr(profile, key, value)

    profile.updated_at = datetime.utcnow()

    db.add(profile)
    db.commit()
    db.refresh(profile)

    await audit_logger.log_event(
        action="PROFILE_UPDATE",
        status="SUCCESS",
        user_id=current_user.id,
        request=request,
        metadata={"updated_fields": list(updated_fields.keys())}
    )

    return profile  


@router.get("/", response_model=ProfileOut, response_model_exclude_none=True)
def get_profile(
    current_user: SQLUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        email = current_user.email
        profile = db.query(Profile).filter(Profile.email == email).first()
        
        if not profile:
            # Return a default profile dict that matches ProfileOut
            return {
                "email": email,
                "patient_name": "Patient",
                "age": None,
                "gender": None,
                "weight_kg": None,
                "height_cm": None,
                "allergies": None,
                "health_goals": None,
                "chronic_diseases": None
            }

        return profile
    except Exception as e:
        print(f"[get_profile error] {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
