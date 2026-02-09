# backend/main.py
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback
import os
import time
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .database import engine, Base
from .auth import router as auth_router
from .profile_router import router as profile_router
from .report_router import router as report_router
from .security_router import router as security_router
from .feedback_router import router as feedback_router
from .owner_router import router as owner_router
from .audit_logger import audit_logger
from . import query_service, dashboard_service, models, database
from .debug_utils import log_debug_error

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="AI Health Assistant API")

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log the full traceback for debugging
    log_debug_error(f"GlobalHandler:{request.url.path}", exc)
    
    # Log to audit logger
    await audit_logger.log_event(
        action="SYSTEM_ERROR",
        status="FAILURE",
        request=request,
        metadata={
            "path": request.url.path,
            "method": request.method,
            "error": str(exc),
            "traceback": traceback.format_exc()
        }
    )
    
    # Return 500 with CORS headers
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error. Please check logs."},
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Credentials": "true",
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Credentials": "true",
        }
    )

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Create tables
try:
    print("🔄 Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables initialized successfully.")
except Exception as e:
    log_debug_error("DB_Initialization", e)
    print(f"❌ Database Initialization Error: {str(e)}")

# Mount static directory for audio
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include origins from .env if available
frontend_url = os.getenv("FRONTEND_URL")
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://[::1]:3000",
    "http://[::1]:5173",
    "http://[::1]:3001",
]
if frontend_url and frontend_url not in origins:
    origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Audit Logging Middleware
@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    if response.status_code >= 400:
        # Avoid logging common 404s or 401s if they are already handled in routers
        # but capture 500s and other critical errors
        if response.status_code >= 500:
            await audit_logger.log_event(
                action="SYSTEM_ERROR",
                status="FAILURE",
                request=request,
                metadata={
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "process_time_ms": round(process_time * 1000, 2)
                }
            )
            
    return response

# Include routers
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(report_router)
app.include_router(security_router)
app.include_router(feedback_router)
app.include_router(owner_router)
app.include_router(query_service.router)
app.include_router(dashboard_service.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Health Assistant API"}
