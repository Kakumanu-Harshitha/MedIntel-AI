# backend/schemas.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# --- Auth schemas ---
class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user_id: int
    email: str
    role: str

class RefreshTokenIn(BaseModel):
    refresh_token: str

class UserCreate(BaseModel):
    email: str
    password: str
    patient_name: Optional[str] = None

# --- Profile schemas ---
class ProfileIn(BaseModel):
    patient_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    allergies: Optional[str] = None
    health_goals: Optional[str] = None
    chronic_diseases: Optional[str] = None

class ProfileOut(ProfileIn):
    email: str
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- LLM / Report Schemas ---
from typing import List, Dict, Any

class ClarificationQuestions(BaseModel):
    type: str = "clarification_questions"
    context: str
    questions: List[str]

class RiskAssessment(BaseModel):
    severity: str  # LOW, MEDIUM, HIGH, EMERGENCY, UNKNOWN
    confidence_score: float  # 0.0 to 1.0
    uncertainty_reason: Optional[str] = None

class Explanation(BaseModel):
    reasoning: str
    history_factor: Optional[str] = None
    profile_factor: Optional[str] = None

class RecommendedSpecialist(BaseModel):
    type: str
    reason: str
    urgency: str  # Routine | Soon | Urgent

class Recommendations(BaseModel):
    immediate_action: str
    lifestyle_advice: List[str]
    food_advice: List[str]

class KnowledgeSource(BaseModel):
    source: str
    description: str

class HealthReport(BaseModel):
    summary: str
    possible_causes: List[str]
    risk_assessment: RiskAssessment
    explanation: Explanation
    recommended_specialist: Optional[RecommendedSpecialist] = None
    recommendations: Recommendations
    knowledge_sources: List[KnowledgeSource] = []
    disclaimer: str

# --- TOTP / Password Change Schemas ---
class TOTPInitOut(BaseModel):
    qr_code: Optional[str] = None # Base64 encoded PNG
    otp_enabled: bool
    expires_at: Optional[datetime] = None

class TOTPVerifyIn(BaseModel):
    otp: str

class PasswordChangeIn(BaseModel):
    new_password: str

# --- Forgot Password Schemas ---
class ForgotPasswordRequest(BaseModel):
    email: str

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
