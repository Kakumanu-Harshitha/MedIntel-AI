# backend/auth.py
import os
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from dotenv import load_dotenv
load_dotenv()
from ..database import get_db
from ..models import User, Profile
from ..schemas import TokenOut, UserCreate, RefreshTokenIn, ForgotPasswordRequest, PasswordResetConfirm
from ..audit_logger import audit_logger
from ..email_service import email_service
from ..models import PasswordResetToken
from .jwt_handler import create_access_token, create_refresh_token, verify_token, SECRET_KEY, ALGORITHM
from .user_auth import get_current_user
from .oauth_config import oauth2_scheme
import secrets
import hashlib

router = APIRouter(prefix="/auth", tags=["Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/signup", response_model=TokenOut)
async def signup(payload: UserCreate, request: Request, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        await audit_logger.log_event(
            action="USER_SIGNUP",
            status="FAILURE",
            request=request,
            metadata={"email": payload.email, "reason": "Email already exists"}
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
    
    hashed_password = pwd_context.hash(payload.password)
    user = User(email=payload.email, password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create profile with patient name
    profile = Profile(email=user.email, patient_name=payload.patient_name)
    db.add(profile)
    db.commit()
    
    await audit_logger.log_event(
        action="USER_SIGNUP",
        status="SUCCESS",
        user_id=user.id,
        request=request,
        metadata={"email": user.email}
    )
    
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    return {
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "token_type": "bearer", 
        "user_id": user.id, 
        "email": user.email,
        "role": user.role
    }

@router.post("/login", response_model=TokenOut)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not pwd_context.verify(form_data.password, user.password):
        await audit_logger.log_event(
            action="USER_LOGIN",
            status="FAILURE",
            request=request,
            metadata={"email": form_data.username, "reason": "Incorrect email or password"}
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    
    await audit_logger.log_event(
        action="USER_LOGIN",
        status="SUCCESS",
        user_id=user.id,
        request=request,
        metadata={"email": user.email}
    )
    
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    return {
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "token_type": "bearer", 
        "user_id": user.id, 
        "email": user.email, 
        "role": user.role
    }

@router.post("/refresh", response_model=TokenOut)
async def refresh_token(payload: RefreshTokenIn, request: Request, db: Session = Depends(get_db)):
    try:
        decoded_payload = verify_token(payload.refresh_token, token_type="refresh")
        email: str = decoded_payload.get("sub")
    except HTTPException as e:
        await audit_logger.log_event(
            action="TOKEN_REFRESH",
            status="FAILURE",
            request=request,
            metadata={"reason": str(e.detail)}
        )
        raise e
        
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        await audit_logger.log_event(
            action="TOKEN_REFRESH",
            status="FAILURE",
            request=request,
            metadata={"email": email, "reason": "User not found"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="User not found", 
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    await audit_logger.log_event(
        action="TOKEN_REFRESH",
        status="SUCCESS",
        user_id=user.id,
        request=request,
        metadata={"email": user.email}
    )
    
    new_access_token = create_access_token(data={"sub": user.email})
    new_refresh_token = create_refresh_token(data={"sub": user.email})
    
    return {
        "access_token": new_access_token, 
        "refresh_token": new_refresh_token,
        "token_type": "bearer", 
        "user_id": user.id, 
        "email": user.email,
        "role": user.role
    }

@router.post("/logout")
async def logout(request: Request, current_user: User = Depends(get_current_user)):
    """
    Log a user logout event. 
    In stateless JWT, actual 'logout' happens on client side by deleting the token.
    """
    await audit_logger.log_event(
        action="USER_LOGOUT",
        status="SUCCESS",
        user_id=current_user.id,
        request=request,
        metadata={"email": current_user.email}
    )
    return {"message": "Logged out successfully"}

@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """
    Generate a secure reset token and send it via Gmail SMTP.
    Follows security best practices by not revealing if an email exists.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    
    if user:
        # 1. Generate secure random token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        
        # 2. Set expiry (15 minutes)
        expiry = datetime.now(timezone.utc) + timedelta(minutes=15)
        
        # 3. Store hashed token
        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expiry
        )
        db.add(reset_token)
        db.commit()
        
        # 4. Send email (Async or background task would be better, but direct is fine for MVP)
        email_sent = email_service.send_password_reset_email(user.email, raw_token)
        
        await audit_logger.log_event(
            action="FORGOT_PASSWORD_REQUEST",
            status="SUCCESS" if email_sent else "FAILURE",
            user_id=user.id,
            request=request,
            metadata={"email": user.email, "email_sent": email_sent}
        )
    else:
        # Generic response for security
        await audit_logger.log_event(
            action="FORGOT_PASSWORD_REQUEST",
            status="FAILURE",
            request=request,
            metadata={"email": payload.email, "reason": "User not found"}
        )

    return {"message": "If the account exists, a reset email has been sent."}

@router.post("/reset-password")
async def reset_password(payload: PasswordResetConfirm, request: Request, db: Session = Depends(get_db)):
    """
    Verify reset token hash, check expiry, and update password.
    """
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    
    # 1. Find valid, unused token
    reset_entry = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.used == 0,
        PasswordResetToken.expires_at > datetime.now(timezone.utc)
    ).first()
    
    if not reset_entry:
        await audit_logger.log_event(
            action="PASSWORD_RESET_CONFIRM",
            status="FAILURE",
            request=request,
            metadata={"reason": "Invalid, used, or expired token"}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token."
        )
    
    # 2. Get user and update password
    user = db.query(User).filter(User.id == reset_entry.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    
    # 3. Securely hash and update
    user.password = pwd_context.hash(payload.new_password)
    
    # 4. Mark token as used
    reset_entry.used = 1
    
    db.commit()
    
    await audit_logger.log_event(
        action="PASSWORD_RESET_CONFIRM",
        status="SUCCESS",
        user_id=user.id,
        request=request,
        metadata={"email": user.email}
    )
    
    return {"message": "Password updated successfully. You can now login with your new password."}
