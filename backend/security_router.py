from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from .database import get_db
from .models import User, ChangePasswordTOTP
from .auth import get_current_user, pwd_context
from .totp_utils import TOTPUtility
from .schemas import TOTPInitOut, TOTPVerifyIn, PasswordChangeIn
from .audit_logger import audit_logger
import re

router = APIRouter(prefix="/security", tags=["Security"])

TOTP_EXPIRY_MINUTES = 10

def validate_password_strength(password: str):
    """Basic password strength validation."""
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long.")
    if not re.search("[a-z]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter.")
    if not re.search("[A-Z]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter.")
    if not re.search("[0-9]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one digit.")

@router.post("/change-password/init", response_model=TOTPInitOut)
async def initiate_change_password(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 1: Initiate change password flow.
    Reuses existing secret if valid, otherwise generates a new one.
    If OTP is already setup, does not show QR code.
    """
    # If user already has OTP enabled, we don't show QR code
    if current_user.otp_enabled:
        # We still need a TOTP entry to track verification state for the password change flow
        db.query(ChangePasswordTOTP).filter(ChangePasswordTOTP.user_id == current_user.id).delete()
        
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=TOTP_EXPIRY_MINUTES)
        totp_entry = ChangePasswordTOTP(
            user_id=current_user.id,
            secret_encrypted=current_user.otp_secret, # Reuse the permanent secret
            expires_at=expires_at
        )
        db.add(totp_entry)
        db.commit()
        
        await audit_logger.log_event(
            action="CHANGE_PASSWORD_INITIATED",
            status="SUCCESS",
            user_id=current_user.id,
            request=request,
            metadata={"otp_already_enabled": True}
        )
        return {"qr_code": None, "otp_enabled": True, "expires_at": expires_at}

    # Check for an existing unverified request that hasn't expired
    existing_entry = db.query(ChangePasswordTOTP).filter(
        ChangePasswordTOTP.user_id == current_user.id,
        ChangePasswordTOTP.verified == 0,
        ChangePasswordTOTP.expires_at > datetime.now(timezone.utc)
    ).first()
    
    if existing_entry:
        # Reuse existing secret
        secret = TOTPUtility.decrypt_secret(existing_entry.secret_encrypted)
        expires_at = existing_entry.expires_at
    else:
        # Delete any old/expired/verified entries for this user to start fresh
        db.query(ChangePasswordTOTP).filter(ChangePasswordTOTP.user_id == current_user.id).delete()
        
        secret = TOTPUtility.generate_secret()
        encrypted_secret = TOTPUtility.encrypt_secret(secret)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=TOTP_EXPIRY_MINUTES)
        
        totp_entry = ChangePasswordTOTP(
            user_id=current_user.id,
            secret_encrypted=encrypted_secret,
            expires_at=expires_at
        )
        db.add(totp_entry)
        db.commit()
    
    uri = TOTPUtility.get_provisioning_uri(secret, current_user.email)
    qr_base64 = TOTPUtility.generate_qr_base64(uri)
    
    await audit_logger.log_event(
        action="CHANGE_PASSWORD_INITIATED",
        status="SUCCESS",
        user_id=current_user.id,
        request=request,
        metadata={"reused": existing_entry is not None, "otp_already_enabled": False}
    )
    
    return {"qr_code": qr_base64, "otp_enabled": False, "expires_at": expires_at}

@router.post("/change-password/verify")
async def verify_password_change_otp(
    payload: TOTPVerifyIn,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 2: Verify the 6-digit OTP from Microsoft Authenticator.
    """
    totp_entry = db.query(ChangePasswordTOTP).filter(
        ChangePasswordTOTP.user_id == current_user.id,
        ChangePasswordTOTP.verified == 0
    ).first()
    
    if not totp_entry:
        raise HTTPException(status_code=400, detail="No active change password request found.")
    
    if datetime.now(timezone.utc) > totp_entry.expires_at:
        db.delete(totp_entry)
        db.commit()
        await audit_logger.log_event(
            action="OTP_VERIFICATION",
            status="FAILURE",
            user_id=current_user.id,
            request=request,
            metadata={"reason": "OTP request expired"}
        )
        raise HTTPException(status_code=400, detail="Request expired. Please start over.")
    
    secret = TOTPUtility.decrypt_secret(totp_entry.secret_encrypted)
    if TOTPUtility.verify_otp(secret, payload.otp):
        totp_entry.verified = 1
        
        # If this was the first time setup, enable OTP for the user permanently
        if not current_user.otp_enabled:
            current_user.otp_secret = totp_entry.secret_encrypted
            current_user.otp_enabled = 1
        
        db.commit()
        
        await audit_logger.log_event(
            action="OTP_VERIFICATION",
            status="SUCCESS",
            user_id=current_user.id,
            request=request
        )
        return {"message": "OTP verified successfully. You can now change your password."}
    else:
        totp_entry.attempts += 1
        db.commit()
        
        await audit_logger.log_event(
            action="OTP_VERIFICATION",
            status="FAILURE",
            user_id=current_user.id,
            request=request,
            metadata={"attempts": totp_entry.attempts}
        )
        raise HTTPException(status_code=400, detail="Invalid OTP. Please try again.")

@router.post("/change-password/complete")
async def complete_password_change(
    payload: PasswordChangeIn,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 3: Update the password in the database.
    Only works if OTP was previously verified.
    """
    totp_entry = db.query(ChangePasswordTOTP).filter(
        ChangePasswordTOTP.user_id == current_user.id,
        ChangePasswordTOTP.verified == 1
    ).first()
    
    if not totp_entry:
        raise HTTPException(status_code=400, detail="OTP not verified or request expired.")
    
    if datetime.now(timezone.utc) > totp_entry.expires_at:
        db.delete(totp_entry)
        db.commit()
        raise HTTPException(status_code=400, detail="Request expired. Please start over.")
    
    # Validate and update password
    validate_password_strength(payload.new_password)
    
    hashed_password = pwd_context.hash(payload.new_password)
    current_user.password = hashed_password
    
    # Delete the TOTP request after success
    db.delete(totp_entry)
    db.commit()
    
    await audit_logger.log_event(
        action="PASSWORD_CHANGED",
        status="SUCCESS",
        user_id=current_user.id,
        request=request
    )
    
    return {"message": "Password updated successfully."}
