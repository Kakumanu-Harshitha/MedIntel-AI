import os
import sys

# Ensure the backend directory is in the python path for local imports
# Since this file is in backend/auth/, we need to add the parent of its parent
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User
from .jwt_handler import verify_token
from .oauth_config import oauth2_scheme, oauth2_scheme_optional
from audit_logger import audit_logger
from fastapi import Request

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Extract and validate current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = verify_token(token)
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_owner(current_user: User = Depends(get_current_user)):
    """Ensure current user has OWNER role."""
    if current_user.role != "OWNER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Owner access required."
        )
    return current_user

def get_current_user_optional(token: str = Depends(oauth2_scheme_optional), db: Session = Depends(get_db)):
    """Extract user from JWT token if present, return None otherwise."""
    if not token:
        return None
    
    try:
        payload = verify_token(token)
        email: str = payload.get("sub")
        if email is None:
            return None
    except Exception:
        return None
    
    return db.query(User).filter(User.email == email).first()