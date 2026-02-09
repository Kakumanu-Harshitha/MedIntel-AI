
import sys
import os

# Updated path to reach project root from backend/scripts/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.database import SessionLocal
from backend.models import SystemConfig

def add_toggles():
    db = SessionLocal()
    try:
        print("🛠️ Adding recommended system toggles...")
        
        recommended_toggles = [
            # Feature Accessibility
            {"key": "audio_query_enabled", "value": "ON"},
            {"key": "image_analysis_enabled", "value": "ON"},
            {"key": "report_parsing_enabled", "value": "ON"},
            
            # AI & Model Governance
            {"key": "llm_fallback_enabled", "value": "ON"},
            {"key": "strict_safety_filter", "value": "OFF"},
            {"key": "auto_escalation_mode", "value": "OFF"},
            
            # Security & Operations
            {"key": "public_signup_enabled", "value": "ON"},
            {"key": "two_factor_required", "value": "OFF"},
            {"key": "pii_masking_enabled", "value": "ON"},
            
            # Maintenance & Performance
            {"key": "global_maintenance_mode", "value": "OFF"},
            {"key": "verbose_audit_logging", "value": "OFF"},
            {"key": "cache_ai_responses", "value": "ON"},
        ]
        
        added_count = 0
        updated_count = 0
        
        for t in recommended_toggles:
            config = db.query(SystemConfig).filter(SystemConfig.key == t["key"]).first()
            if not config:
                config = SystemConfig(key=t["key"], value=t["value"])
                db.add(config)
                added_count += 1
            else:
                # We don't overwrite existing values to avoid resetting user preferences
                # but we print that they exist
                pass
        
        db.commit()
        print(f"✅ Finished! Added {added_count} new toggles.")
        if added_count == 0:
            print("ℹ️ All recommended toggles already exist in the database.")

    except Exception as e:
        print(f"❌ Error adding toggles: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_toggles()
