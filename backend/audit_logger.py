
import uuid
import json
import hashlib
import asyncio
from datetime import datetime
from typing import Optional, Any, Dict
from sqlalchemy.orm import Session
from fastapi import Request
from models import AuditLog
from database import SessionLocal

class AuditLogger:
    @staticmethod
    def mask_ip(ip: Optional[str]) -> str:
        if not ip:
            return "unknown"
        # Mask the last part of the IP for privacy
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.xxx"
        return "masked"

    @staticmethod
    async def log_event(
        action: str,
        status: str,
        user_id: Optional[int] = None,
        source: str = "api",
        request: Optional[Request] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Logs an audit event asynchronously to avoid blocking the main thread.
        """
        # Prepare log data
        log_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        ip_address = "unknown"
        user_agent = "unknown"
        
        if request:
            # Get IP from request
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                ip_address = AuditLogger.mask_ip(forwarded.split(",")[0])
            else:
                ip_address = AuditLogger.mask_ip(request.client.host if request.client else None)
            
            user_agent = request.headers.get("User-Agent", "unknown")

        # Run the database insertion in a separate thread to be non-blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, AuditLogger._save_to_db, log_id, timestamp, user_id, action, status, source, ip_address, user_agent, metadata)

    @staticmethod
    def _save_to_db(log_id, timestamp, user_id, action, status, source, ip_address, user_agent, metadata):
        db = SessionLocal()
        try:
            new_log = AuditLog(
                log_id=log_id,
                timestamp=timestamp,
                user_id=user_id,
                action=action,
                status=status,
                source=source,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata_json=metadata
            )
            db.add(new_log)
            db.commit()
        except Exception as e:
            print(f"❌ Audit Logging Error: {str(e)}")
            db.rollback()
        finally:
            db.close()

audit_logger = AuditLogger()
