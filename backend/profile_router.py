# backend/profile_router.py
import os
import sys

# Ensure the backend directory is in the python path for local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from database import get_db
from models import Profile
from schemas import ProfileIn, ProfileOut
from auth import get_current_user
from models import User as SQLUser  # for typing
from audit_logger import audit_logger

router = APIRouter(prefix="/profile", tags=["Profile"])
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
    email = current_user.email
    profile = db.query(Profile).filter(Profile.email == email).first()
    if not profile:
        return {"email": email}

    return profile  