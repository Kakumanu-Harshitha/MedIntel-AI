# backend/models.py
from sqlalchemy import Column, Integer, String, DateTime, Float, JSON
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "user_accounts"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    otp_secret = Column(String, nullable=True)  # Encrypted TOTP secret
    otp_enabled = Column(Integer, default=0)    # 0 for false, 1 for true
    created_at = Column(DateTime, default=datetime.utcnow)

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Integer, default=0) # 0 for false, 1 for true
    created_at = Column(DateTime, default=datetime.utcnow)

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    weight_kg = Column(Float, nullable=True)
    height_cm = Column(Float, nullable=True)
    allergies = Column(String, nullable=True)
    health_goals = Column(String, nullable=True)
    chronic_diseases = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    log_id = Column(String, unique=True, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    action = Column(String, index=True, nullable=False)
    status = Column(String, nullable=False) # SUCCESS | FAILURE
    source = Column(String, nullable=False) # web | api | system
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    metadata_json = Column(JSON, nullable=True)

class ChangePasswordTOTP(Base):
    __tablename__ = "change_password_totp"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    secret_encrypted = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    verified = Column(Integer, default=0) # 0 for false, 1 for true
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
