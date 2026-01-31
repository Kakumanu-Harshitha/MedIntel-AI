from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)