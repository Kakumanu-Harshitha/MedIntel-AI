
import sys
import os
from sqlalchemy.orm import Session
from passlib.context import CryptContext

# Add the project root to sys.path so we can import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal
from backend.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def setup_admin():
    db = SessionLocal()
    try:
        admin_email = "harshithakakumanu2006@gmail.com"
        admin_password = "Honey@123"
        
        # Check if user already exists
        user = db.query(User).filter(User.email == admin_email).first()
        
        hashed_password = pwd_context.hash(admin_password)
        
        if user:
            print(f"User {admin_email} already exists. Updating to OWNER role...")
            user.role = "OWNER"
            user.password = hashed_password
        else:
            print(f"Creating new admin user: {admin_email}")
            user = User(
                email=admin_email,
                password=hashed_password,
                role="OWNER"
            )
            db.add(user)
        
        db.commit()
        print("✅ Admin user setup successfully!")
    except Exception as e:
        print(f"❌ Error setting up admin: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    setup_admin()
