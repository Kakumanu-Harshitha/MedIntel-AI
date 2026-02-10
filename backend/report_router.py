# backend/report_router.py
from io import BytesIO
import os
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from fpdf import FPDF

from auth.router import get_current_user
from models import User as SQLUser, Profile
from database import get_db
import mongo_memory
from audit_logger import audit_logger

router = APIRouter(prefix="/report", tags=["Report"])

# TEXT SANITIZER
def sanitize(text: str) -> str:
    if not text:
        return ""
    # Ensure text is string
    if not isinstance(text, str):
        text = str(text)
    return (
        text
        .replace("’", "'").replace("“", '"').replace("”", '"')
        .encode('latin-1', 'replace').decode('latin-1') 
    )

def normalize_report_data(data: dict) -> dict:
    """
    Normalizes all possible report schemas (Health Report, Medical Analysis, Legacy, etc.)
    into a standard format for PDF generation.
    """
    normalized = {
        "summary": "",
        "severity": "UNKNOWN",
        "conditions": [],
        "analysis": "",
        "recommendations": [],
        "food_advice": [],
        "red_flags": [],
        "sources": []
    }

    # 1. NEW STRUCTURE: Health Report (Symptom Shortcut / RAG)
    if data.get("type") == "health_report" or "health_information" in data:
        normalized["summary"] = data.get("health_information", data.get("summary", ""))
        normalized["analysis"] = data.get("reasoning_brief", "")
        normalized["conditions"] = data.get("possible_conditions", [])
        normalized["recommendations"] = [data.get("recommended_next_steps", "")]
        normalized["sources"] = data.get("trusted_sources", [])
        normalized["severity"] = "MODERATE" # Default for symptom reports if not specified

    # 2. NEW STRUCTURE: Medical Report Analysis (Lab Results)
    elif data.get("type") == "medical_report_analysis" or "test_analysis" in data:
        normalized["summary"] = data.get("summary", "Medical report analysis.")
        normalized["severity"] = "UNKNOWN"
        
        # Convert test analysis to analysis text
        test_text = []
        for test in data.get("test_analysis", []):
            test_text.append(f"{test.get('test_name')}: {test.get('value')} ({test.get('status')}) - {test.get('explanation')}")
        normalized["analysis"] = "\n".join(test_text)
        
        normalized["recommendations"] = data.get("general_guidance", [])
        normalized["red_flags"] = data.get("when_to_consult_doctor", [])

    # 3. STRUCTURE: Medical Image Analysis
    elif data.get("input_type") == "medical_image" or "observations" in data:
        normalized["summary"] = "Physical Image Analysis Findings."
        normalized["analysis"] = ", ".join(data.get("observations", []))
        normalized["conditions"] = data.get("possible_conditions", [])
        normalized["recommendations"] = [data.get("general_advice", "")]

    # 4. Handle Nested Schema (General AI Assessment)
    elif "risk_assessment" in data:
        risk = data.get("risk_assessment", {})
        normalized["summary"] = data.get("summary", "")
        normalized["severity"] = risk.get("severity", "UNKNOWN")
        
        explanation = data.get("explanation", {})
        normalized["analysis"] = explanation.get("reasoning", "")
        if explanation.get("history_factor"):
            normalized["analysis"] += f"\n\nHistory Context: {explanation['history_factor']}"
        
        recs = data.get("recommendations", {})
        normalized["recommendations"] = recs.get("lifestyle_advice", [])
        normalized["food_advice"] = recs.get("food_advice", [])
        normalized["sources"] = data.get("knowledge_sources", [])
        
        if recs.get("immediate_action"):
            normalized["red_flags"].append(recs["immediate_action"])
            
        normalized["conditions"] = data.get("possible_causes", [])

        # Specialist Suggestion
        spec = data.get("recommended_specialist", {})
        if spec:
             normalized["specialist"] = {
                 "type": spec.get("type", "General Physician"),
                 "reason": spec.get("reason", "Standard consultation"),
                 "urgency": spec.get("urgency", "Routine")
             }

    # 5. Handle Old Flat Schema / Legacy
    else:
        normalized["summary"] = data.get("summary", data.get("interpretation", "No summary available."))
        normalized["severity"] = data.get("severity", "UNKNOWN")
        normalized["conditions"] = data.get("possible_conditions", data.get("possible_causes", []))
        normalized["analysis"] = data.get("analysis", "")
        
        old_recs = data.get("recommendations", [])
        if isinstance(old_recs, list):
            normalized["recommendations"] = old_recs
        elif isinstance(old_recs, str):
             normalized["recommendations"] = [old_recs]
        elif "recommendation" in data:
             normalized["recommendations"] = [data["recommendation"]]
             
        normalized["food_advice"] = data.get("food_recommendations", [])
        normalized["red_flags"] = data.get("red_flags", [])

    return normalized

    # PDF CLASS WITH MEDICAL GRADE STYLING
class HealthReportPDF(FPDF):
    def __init__(self, metadata=None):
        super().__init__()
        self.metadata = metadata or {}
        self.set_auto_page_break(auto=True, margin=20)
        self.brand_primary = (13, 110, 253)    # Brand Blue
        self.brand_secondary = (108, 117, 125) # Secondary Gray
        self.brand_accent = (25, 135, 84)      # Success Green
        self.brand_danger = (220, 53, 69)      # Danger Red
        self.brand_text = (33, 37, 41)         # Dark text
        self.brand_bg = (248, 249, 250)        # Light background

    def header(self):
        # Draw a subtle background for the header
        self.set_fill_color(255, 255, 255)
        self.rect(0, 0, 210, 45, 'F')
        
        # Brand Logo/Name
        self.set_font("Helvetica", "B", 24)
        self.set_text_color(*self.brand_primary)
        self.set_xy(15, 15)
        self.cell(100, 12, "HealthGuide AI", ln=False)
        
        # Subtitle
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*self.brand_secondary)
        self.set_xy(15, 27)
        self.cell(100, 5, "Personalized Clinical Insight & Assessment", ln=True)

        # Date & Metadata (Right Aligned)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(70, 70, 70)
        self.set_xy(140, 16)
        
        report_date = self.metadata.get("created_at")
        if report_date:
            if isinstance(report_date, str):
                try:
                    report_date = datetime.fromisoformat(report_date.replace('Z', '+00:00'))
                except:
                    report_date = datetime.now()
            date_str = report_date.strftime('%d %b %Y')
        else:
            date_str = datetime.now().strftime('%d %b %Y')
            
        self.cell(55, 5, f"REPORT DATE: {date_str}", align="R", ln=True)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 100, 100)
        self.set_x(140)
        
        ref_id = self.metadata.get("report_id", "LATEST")[:8].upper()
        self.cell(55, 5, f"REF: HGAI-{date_str.replace(' ', '')}-{ref_id}", align="R", ln=True)

        # Gradient separator line
        self.set_draw_color(*self.brand_primary)
        self.set_line_width(1)
        self.line(15, 40, 195, 40)
        self.ln(35)

    def section_title(self, title: str, icon_color=None):
        if not icon_color:
            icon_color = self.brand_primary
            
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*icon_color)
        self.set_fill_color(245, 247, 250)
        
        # Vertical accent line
        self.set_draw_color(*icon_color)
        self.set_line_width(1.5)
        curr_y = self.get_y()
        self.line(15, curr_y, 15, curr_y + 10)
        
        self.set_x(18)
        self.cell(0, 10, f"  {title.upper()}", ln=True, fill=True)
        self.ln(5)

    def content_text(self, text: str):
        self.set_font("Helvetica", "", 11)
        self.set_text_color(*self.brand_text)
        self.set_x(20)
        self.multi_cell(0, 7, sanitize(text))
        self.ln(5)
        
    def profile_section(self, profile: dict, bmi: str, risk: str):
        self.section_title("Patient Information")
        
        # Create a nice rounded box/grid for patient info
        self.set_fill_color(255, 255, 255)
        self.set_draw_color(230, 233, 237)
        self.set_line_width(0.2)
        
        start_x = 18
        start_y = self.get_y()
        self.rect(start_x, start_y, 177, 35, 'D')
        
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*self.brand_secondary)
        
        # Column 1
        self.set_xy(start_x + 5, start_y + 5)
        self.cell(40, 8, "EMAIL ADDRESS")
        self.set_xy(start_x + 5, start_y + 12)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*self.brand_text)
        self.cell(80, 8, sanitize(profile.get('email', 'N/A')))
        
        # Column 2
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*self.brand_secondary)
        self.set_xy(start_x + 90, start_y + 5)
        self.cell(40, 8, "AGE / GENDER")
        self.set_xy(start_x + 90, start_y + 12)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*self.brand_text)
        self.cell(80, 8, f"{profile.get('age', 'N/A')} / {profile.get('gender', 'N/A')}")
        
        # Row 2
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*self.brand_secondary)
        self.set_xy(start_x + 5, start_y + 22)
        self.cell(40, 8, "VITAL STATS")
        self.set_xy(start_x + 5, start_y + 28)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*self.brand_text)
        self.cell(80, 8, f"{profile.get('height_cm', 'N/A')}cm | {profile.get('weight_kg', 'N/A')}kg | BMI: {bmi}")
        
        # Risk Rating (Right Aligned in the box)
        risk_upper = risk.upper()
        if any(kw in risk_upper for kw in ["HIGH", "EMERGENCY", "SEVERE"]):
            badge_color = self.brand_danger
            badge_text = "HIGH RISK"
        elif any(kw in risk_upper for kw in ["MODERATE", "MEDIUM"]):
            badge_color = (255, 152, 0) # Amber
            badge_text = "MODERATE RISK"
        else:
            badge_color = self.brand_accent
            badge_text = "LOW RISK"
            
        self.set_fill_color(*badge_color)
        self.set_text_color(255, 255, 255)
        self.set_xy(start_x + 135, start_y + 22)
        self.cell(35, 8, badge_text, border=0, fill=True, align="C")
        
        self.set_xy(15, start_y + 40)
        self.ln(5)

    def footer(self):
        self.set_y(-30)
        # Background for footer
        self.set_fill_color(248, 249, 250)
        self.rect(0, 267, 210, 30, 'F')
        
        self.set_draw_color(220, 220, 220)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(4)
        
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.set_x(15)
        self.multi_cell(180, 4, "NOTICE: This AI-generated report provides clinical decision support and preliminary insights. It is NOT a substitute for professional medical advice, diagnosis, or treatment. Confidential medical data.", align="C")
        
        self.set_y(-10)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"PAGE {self.page_no()} | HEALTHGUIDE AI - PROPRIETARY", align="C")

# REPORT ENDPOINT
@router.get("/user/{email}")
async def generate_user_report(
    email: str,
    request: Request,
    report_id: str = None,
    current_user: SQLUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if email != current_user.email:
        await audit_logger.log_event(
            action="REPORT_DOWNLOAD",
            status="FAILURE",
            user_id=current_user.id,
            request=request,
            metadata={"target_email": email, "reason": "Unauthorized access attempt"}
        )
        raise HTTPException(status_code=403, detail="Unauthorized")

    # 1. Fetch Profile
    profile_obj = db.query(Profile).filter(Profile.email == email).first()
    profile_data = {
        "email": email,
        "age": str(profile_obj.age) if profile_obj and profile_obj.age else "N/A",
        "gender": profile_obj.gender if profile_obj and profile_obj.gender else "N/A",
        "height_cm": str(profile_obj.height_cm) if profile_obj and profile_obj.height_cm else "N/A",
        "weight_kg": str(profile_obj.weight_kg) if profile_obj and profile_obj.weight_kg else "N/A",
    }
    
    # Calculate BMI
    bmi = "N/A"
    if profile_obj and profile_obj.height_cm and profile_obj.weight_kg:
        try:
            h_m = profile_obj.height_cm / 100
            bmi_val = profile_obj.weight_kg / (h_m * h_m)
            bmi = f"{bmi_val:.1f}"
        except:
            pass

    # 2. Fetch Report (Specific or Latest)
    raw_report = None
    report_metadata = {}
    if report_id:
        # Try to fetch the specific report by ID
        # We need the full doc to get metadata like created_at
        report_doc = mongo_memory.memory_collection.find_one({
            "user_id": str(current_user.id),
            "report_id": report_id
        })
        if report_doc:
            try:
                raw_report = json.loads(report_doc["content"])
                report_metadata = {
                    "created_at": report_doc.get("timestamp"),
                    "report_type": report_doc.get("report_type"),
                    "report_id": report_id
                }
            except:
                pass
        
        if not raw_report:
            print(f"⚠️ Report ID {report_id} not found. Falling back to latest.")

    if not raw_report:
        # Fetch Latest Report from History as fallback
        full_history = mongo_memory.get_full_history_for_dashboard(str(current_user.id), limit=50)
        
        if full_history:
            # Search from Newest to Oldest to find the most recent report
            for msg in reversed(full_history):
                if msg.get("role") == "assistant":
                    try:
                        content = msg.get("content", "")
                        parsed = json.loads(content)
                        # Heuristic to check if it's a report (Strict Eligibility)
                        report_type_field = parsed.get("type") or parsed.get("input_type")
                        is_report = report_type_field in ["health_report", "medical_report_analysis", "medical_image"]
                        
                        if is_report:
                            raw_report = parsed
                            report_metadata = {
                                "created_at": msg.get("timestamp"),
                                "report_type": msg.get("report_type"),
                                "report_id": msg.get("report_id")
                            }
                            break
                    except:
                        continue
    
    if not raw_report:
        raw_report = {"summary": "No report found."}

    # 3. Normalize Data
    report = normalize_report_data(raw_report)

    # 4. Generate PDF
    pdf = HealthReportPDF(metadata=report_metadata)
    pdf.add_page()
    
    await audit_logger.log_event(
        action="REPORT_DOWNLOAD",
        status="SUCCESS",
        user_id=current_user.id,
        request=request,
        metadata={"email": email, "severity": report["severity"]}
    )

    # Profile Section
    pdf.profile_section(profile_data, bmi, report["severity"])
    
    # Quick Summary
    pdf.section_title("Quick Health Summary")
    pdf.content_text(report["summary"])
    
    # AI Insights
    pdf.section_title("AI Insights & Analysis")
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 6, "Note: These are potential possibilities based on symptoms, NOT a diagnosis.", ln=True)
    pdf.ln(2)
    
    # Conditions
    if report["conditions"]:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, "Possible Conditions:", ln=True)
        pdf.set_font("Helvetica", "", 11)
        for cond in report["conditions"]:
             pdf.cell(5) 
             pdf.cell(0, 6, f"- {sanitize(cond)}", ln=True)
        pdf.ln(2)
        
    # Detailed Analysis
    if report["analysis"]:
        pdf.content_text(report["analysis"])

    # Specialist Suggestion (New Feature)
    if report.get("specialist"):
        spec = report["specialist"]
        pdf.ln(4)
        pdf.set_fill_color(232, 248, 245) # Teal/Mint Light
        pdf.set_text_color(22, 160, 133)   # Teal Dark
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, f"  CONSULTATION: {sanitize(spec['type'])}", ln=True, fill=True)
        
        pdf.set_text_color(50, 50, 50)
        pdf.set_font("Helvetica", "I", 11)
        pdf.cell(5)
        pdf.cell(0, 8, f"Urgency: {spec['urgency']}", ln=True)
        
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(5)
        pdf.multi_cell(0, 6, f"Reason: {sanitize(spec['reason'])}")
        pdf.ln(4)

    # Recommendations
    pdf.section_title("Clinical Recommendations")
    if report["recommendations"]:
        for rec in report["recommendations"]:
            pdf.set_x(20)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*pdf.brand_primary)
            pdf.cell(5, 7, chr(149), ln=0) # Bullet
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(*pdf.brand_text)
            pdf.multi_cell(0, 7, sanitize(str(rec)))
            pdf.ln(2)
    
    # Food & Diet
    if report["food_advice"]:
        pdf.section_title("Nutrition & Dietary Guide", icon_color=(255, 152, 0))
        for item in report["food_advice"]:
            pdf.set_x(20)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(255, 152, 0)
            pdf.cell(5, 7, chr(149), ln=0)
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(*pdf.brand_text)
            pdf.multi_cell(0, 7, sanitize(str(item)))
            pdf.ln(2)
    
    # Trusted Sources
    if report.get("sources"):
        pdf.ln(5)
        pdf.section_title("Verified Clinical Sources")
        for src in report["sources"]:
            # Handle both dict (new schema) and string (fallback)
            if isinstance(src, dict):
                source_name = src.get("source", "Unknown Source")
                desc = src.get("description", "")
            else:
                source_name = "Source"
                desc = str(src)

            pdf.set_x(20)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*pdf.brand_primary)
            pdf.cell(0, 6, f"{sanitize(source_name)}", ln=True)
            
            pdf.set_x(25)
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(0, 5, f"{sanitize(desc)}")
            pdf.ln(3)

    # Red Flags / Immediate Action
    if report["red_flags"]:
        pdf.ln(5)
        pdf.set_fill_color(*pdf.brand_danger)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_x(15)
        pdf.cell(180, 10, "  IMMEDIATE CLINICAL ATTENTION REQUIRED", ln=True, fill=True)
        pdf.set_text_color(*pdf.brand_danger)
        pdf.set_font("Helvetica", "B", 11)
        for flag in report["red_flags"]:
            pdf.set_x(20)
            pdf.multi_cell(0, 7, f">> {sanitize(str(flag))}")
        pdf.ln(5)
        
    # Output
    try:
        # FPDF output(dest='S') returns a byte-string in latin-1 or a string depending on version/config.
        # We need to ensure it's handled as bytes for the StreamingResponse.
        pdf_output = pdf.output(dest='S')
        
        # If output is a string, encode it to bytes. If it's already bytes, use as is.
        if isinstance(pdf_output, str):
            pdf_content = pdf_output.encode('latin-1')
        else:
            pdf_content = pdf_output
            
        pdf_buffer = BytesIO(pdf_content)
        
        # Determine filename based on metadata
        report_date = report_metadata.get("created_at")
        if report_date:
            if isinstance(report_date, str):
                try:
                    report_date = datetime.fromisoformat(report_date.replace('Z', '+00:00'))
                except:
                    report_date = datetime.now()
            date_str = report_date.strftime('%Y%m%d')
        else:
            date_str = datetime.now().strftime('%Y%m%d')
            
        report_type = report_metadata.get("report_type", "health").lower()
        filename = f"HealthReport_{report_type}_{date_str}.pdf"
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        print(f"❌ PDF Generation Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")
