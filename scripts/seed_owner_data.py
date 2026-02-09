
import sys
import os
import uuid
import random
from datetime import datetime, timedelta
from passlib.context import CryptContext

# Add the project root to sys.path so we can import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal, engine, Base
from backend.models import User, UserFeedback, AuditLog, SystemConfig

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def seed_data():
    db = SessionLocal()
    try:
        print("🌱 Starting data seeding for Owner Dashboard verification...")

        # 1. Create Test Users
        test_users_data = [
            {"email": "test_user1@example.com", "role": "USER"},
            {"email": "test_user2@example.com", "role": "USER"},
            {"email": "test_user3@example.com", "role": "USER"},
            {"email": "test_user4@example.com", "role": "USER"},
            {"email": "test_user5@example.com", "role": "USER"},
        ]
        
        created_users = []
        for u_data in test_users_data:
            user = db.query(User).filter(User.email == u_data["email"]).first()
            if not user:
                user = User(
                    email=u_data["email"],
                    password=pwd_context.hash("TestPass123!"),
                    role=u_data["role"],
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
                )
                db.add(user)
                db.flush() # Get user.id
            created_users.append(user)
        
        print(f"✅ Created {len(created_users)} test users.")

        # 2. Create System Config (Toggles)
        toggles = [
            {"key": "maintenance_mode", "value": "OFF"},
            {"key": "hitl_enabled", "value": "ON"},
            {"key": "debug_logs", "value": "OFF"},
        ]
        for t in toggles:
            config = db.query(SystemConfig).filter(SystemConfig.key == t["key"]).first()
            if not config:
                config = SystemConfig(key=t["key"], value=t["value"])
                db.add(config)
        
        print("✅ Initialized system toggles.")

        # 3. Create Audit Logs (For health, security, and HITL metrics)
        actions = [
            "USER_LOGIN", "AI_QUERY", "IMAGE_MODALITY_DETECTION", 
            "HITL_ESCALATION", "PASSWORD_RESET", "SYSTEM_TOGGLE_UPDATE"
        ]
        
        for _ in range(100):
            action = random.choice(actions)
            user = random.choice(created_users)
            status = "SUCCESS" if random.random() > 0.1 else "FAILURE"
            
            # Metadata based on action
            metadata = {}
            if action == "AI_QUERY":
                metadata = {"query": "What is healthy eating?", "model": random.choice(["llama-3.3-70b-versatile", "llama-3.1-8b-instant"])}
            elif action == "IMAGE_MODALITY_DETECTION":
                escalated = random.choice([True, False])
                metadata = {"modality": "ECG", "confidence": random.random(), "escalated": str(escalated).lower()}
            
            log = AuditLog(
                log_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow() - timedelta(hours=random.randint(0, 168)), # Last 7 days
                user_id=user.id,
                action=action,
                status=status,
                source="web",
                ip_address=f"192.168.1.{random.randint(1, 254)}",
                metadata_json=metadata
            )
            db.add(log)
            
        print("✅ Generated 100 random audit logs.")

        # 4. Create User Feedback (For satisfaction and model metrics)
        models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "fallback-static"]
        reasons = ["Inaccurate", "Too slow", "Hard to understand", "Not helpful", "Incorrect formatting"]
        
        for _ in range(50):
            helpful = 1 if random.random() > 0.3 else 0
            user = random.choice(created_users)
            
            feedback = UserFeedback(
                user_id=user.id,
                query_text="How to reduce stress?",
                response_text="Meditation and exercise are great ways...",
                helpful=helpful,
                reason=random.choice(reasons) if helpful == 0 else None,
                confidence_score=random.uniform(0.6, 0.99),
                model_used=random.choice(models),
                timestamp=datetime.utcnow() - timedelta(days=random.randint(0, 14))
            )
            db.add(feedback)

        print("✅ Generated 50 feedback entries.")

        db.commit()
        print("🚀 Data seeding completed successfully! The owner dashboard should now show rich data.")

    except Exception as e:
        print(f"❌ Error during seeding: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
