
import sys
import os
from sqlalchemy import text

# Updated path to reach project root from backend/scripts/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.database import engine

def fix_table():
    with engine.connect() as conn:
        print("🔍 Checking user_feedback table...")
        try:
            # Check if columns exist
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'user_feedback'"))
            columns = [row[0] for row in result]
            print(f"Current columns: {columns}")
            
            if 'query_text' not in columns:
                print("Adding missing column 'query_text'...")
                conn.execute(text("ALTER TABLE user_feedback ADD COLUMN query_text VARCHAR"))
            
            if 'response_text' not in columns:
                print("Adding missing column 'response_text'...")
                conn.execute(text("ALTER TABLE user_feedback ADD COLUMN response_text VARCHAR"))
                
            conn.commit()
            print("✅ Table fixed successfully.")
        except Exception as e:
            print(f"❌ Error fixing table: {e}")

if __name__ == "__main__":
    fix_table()
