import json
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, Request
from typing import Optional, List
from PIL import Image
import open_clip
import torch
from sqlalchemy.orm import Session
import mongo_memory
import llm_service
import speech_service
from report_processor import report_processor
from auth.router import get_current_user
from models import User, Profile
from database import get_db
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# --- Router Setup ---
router = APIRouter(prefix="/query", tags=["Query Service"])

# --- Load MediCLIP (BiomedCLIP) Model Globally ---
# Using microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224 via open_clip
# This model aligns medical images with medical text using PubMedBERT.
MEDICLIP_MODEL_ID = "hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224"

try:
    # Load model and transforms using open_clip
    model, _, preprocess = open_clip.create_model_and_transforms(MEDICLIP_MODEL_ID)
    tokenizer = open_clip.get_tokenizer(MEDICLIP_MODEL_ID)
    print("✅ MediCLIP (BiomedCLIP) model loaded successfully via open_clip.")
    
    # Pre-defined medical concepts for Zero-Shot Classification / Feature Extraction
    CANDIDATE_LABELS = [
        "Chest X-ray", "Chest Radiograph", "MRI Scan", "CT Scan", 
        "Dermatology Skin Condition", "Skin Rash", "Skin Lesion",
        "Eye Ophthalmology", "Retina Scan", "Red Eye", "Ocular Condition",
        "Medical Document", "Prescription", "Lab Report", "Chart or Graph",
        "Ultrasound", "Microscope Slide", "Healthy Human Tissue",
        "Bone X-ray", "Fracture", "Pneumonia", "Lung Inflammation"
    ]
    
except Exception as e:
    processor = None # Not used with open_clip, but keeping for safety if referenced elsewhere (unlikely)
    preprocess = None
    tokenizer = None
    model = None
    CANDIDATE_LABELS = []
    print(f"⚠️ WARNING: Could not load MediCLIP model. Image functionality will be disabled. Error: {e}")

def analyze_image_with_mediclip(image: Image.Image) -> str:
    """
    Uses MediCLIP to analyze the image via Zero-Shot Classification.
    Returns a text description of the most likely labels.
    """
    if not model or not preprocess or not tokenizer:
        return "[Image Analysis Unavailable]"

    try:
        # 1. Preprocess Image
        image_input = preprocess(image).unsqueeze(0) # Add batch dimension
        
        # 2. Tokenize Text Labels
        text_tokens = tokenizer(CANDIDATE_LABELS)
        
        # 3. Inference
        with torch.no_grad():
            image_features = model.encode_image(image_input)
            text_features = model.encode_text(text_tokens)
            
            # Normalize features
            image_features /= image_features.norm(dim=-1, keepdim=True)
            text_features /= text_features.norm(dim=-1, keepdim=True)
            
            # Calculate probabilities (Image-Text Similarity)
            text_probs = (100.0 * image_features @ text_features.T).softmax(dim=-1)

        # Get top 3 matches
        top_k = 3
        values, indices = text_probs[0].topk(top_k)
        
        findings = []
        for i in range(top_k):
            score = values[i].item()
            label = CANDIDATE_LABELS[indices[i].item()]
            findings.append(f"{label} ({score:.4f})")
        
        if not findings:
            return "Unclear medical image. Confidence low."
            
        return "MediCLIP Analysis: " + ", ".join(findings)

    except Exception as e:
        print(f"❌ MediCLIP Error: {e}")
        return "[Error analyzing image]"


# --- NEW UNIFIED MULTIMODAL ENDPOINT ---
@router.post("/multimodal")
@limiter.limit("10/minute")
async def handle_multimodal_query(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    text_query: str = Form(""),
    audio_file: Optional[UploadFile] = File(None),
    image_file: Optional[UploadFile] = File(None),
    report_file: Optional[UploadFile] = File(None),
    user_confirmation: str = Form("skip") # yes, no, skip
):
    """
    Handles any combination of text, voice, and image inputs in a single request.
    """
    user_id_str = str(current_user.id)
    transcribed_text = None
    image_caption = None
    report_text = None
    prompt_parts = []

    # 1. Process Voice Input (if provided)
    if audio_file:
        print(f"🎤 Processing audio file: {audio_file.filename}")
        # Seek to start to ensure it's readable
        audio_file.file.seek(0)
        transcribed_text = speech_service.speech_to_text(audio_file)
        if transcribed_text.startswith("[stt_error]"):
            raise HTTPException(status_code=500, detail=f"Speech-to-Text failed: {transcribed_text}")
        prompt_parts.append(f"The user said: '{transcribed_text}'")

    # 2. Process Image Input (if provided)
    image_text = None
    if image_file:
        print(f"📷 Processing image file: {image_file.filename}")
        if not model or not preprocess or not tokenizer:
            raise HTTPException(status_code=503, detail="Image processing service is currently unavailable.")
        
        # Seek to start of file to ensure it's readable
        image_file.file.seek(0)
        file_bytes = await image_file.read()
        
        # 2a. Run MediCLIP for visual classification
        import io
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        image_caption = analyze_image_with_mediclip(image)
        print(f"📷 Image analysis result: {image_caption}")
        
        # 2b. Run OCR to see if it's a medical document
        # Reset pointer for OCR if it uses file_bytes
        image_text = report_processor.extract_text_from_image(file_bytes)
        if image_text:
            print(f"📷 OCR extracted text from image ({len(image_text)} chars)")
            prompt_parts.append(f"They also typed/uploaded text: '{image_text[:500]}'")
        
        prompt_parts.append(f"The user uploaded an image that looks like: {image_caption}")

    # 3. Process Medical Report Input (if provided)
    if report_file:
        print(f"📄 Processing report: {report_file.filename}")
        # Seek to start to ensure it's readable
        report_file.file.seek(0)
        file_bytes = await report_file.read()
        report_data = report_processor.process_report(file_bytes, report_file.filename)
        
        if report_data["type"] == "error":
            # If there's an error processing the report, we should let the user know directly
            # rather than letting the LLM try to interpret the error message.
            return {
                "text_response": json.dumps({
                    "summary": "Report Analysis Failed",
                    "severity": "UNKNOWN",
                    "analysis": report_data["content"],
                    "recommendations": ["Please upload a clearer image or the original PDF file."],
                    "disclaimer": "Medical Report Parsing Error"
                }),
                "report_id": None
            }
            
        report_text = report_data["content"]
        print(f"📄 Report processing complete: {len(report_text)} chars extracted.")
        
        # Ensure report_text is never empty if a file was provided
        if not report_text or not report_text.strip():
            report_text = f"[Medical Report Content Missing: {report_file.filename}]"
            
        prompt_parts.append(f"The user uploaded a medical report containing: {report_text}")

    # 4. Process Text Input (if provided)
    if text_query.strip():
        prompt_parts.append(f"The user's text query is: '{text_query}'")
        
    # 5. Check if any input was provided
    if not prompt_parts:
        raise HTTPException(status_code=400, detail="No input provided. Please provide text, voice, or an image.")

    # 6. Fetch User Profile
    profile_record = db.query(Profile).filter(Profile.email == current_user.email).first()
    profile_dict = {}
    if profile_record:
        profile_dict = {
            "user_id": str(current_user.id),
            "age": profile_record.age,
            "gender": profile_record.gender,
            "weight_kg": profile_record.weight_kg,
            "height_cm": profile_record.height_cm,
            "chronic_diseases": profile_record.chronic_diseases,
            "allergies": profile_record.allergies
        }
    else:
        profile_dict = {"user_id": str(current_user.id)}

    # 7. Assemble Inputs and get LLM response
    final_prompt = " ".join(prompt_parts) # Still used for storing simple history
    history = mongo_memory.get_user_memory(user_id_str)
    
    inputs = {
        "text_query": text_query,
        "transcribed_text": transcribed_text,
        "image_caption": image_caption,
        "image_text": image_text,
        "report_text": report_text,
        "user_confirmation": user_confirmation
    }
    
    # Call the new Google-Level pipeline
    text_response = await llm_service.run_clinical_analysis(profile_dict, history, inputs, request)

    # 7. Generate Voice Response (TTS) - Google Level Feature
    audio_filename = None
    audio_url = None
    
    # Heuristic: If user used voice OR explicitly asked, generate audio.
    # For now, let's always generate it if the response is valid JSON, to show off the feature.
    try:
        response_data = json.loads(text_response)
        text_to_speak = ""
        
        if response_data.get("type") == "clarification_questions":
            # Speak the context + questions
            text_to_speak = response_data.get("context", "") + " " + " ".join(response_data.get("questions", []))
            
        elif response_data.get("type") == "health_report":
            # Speak the health information + disclaimer
            text_to_speak = response_data.get("health_information", "") + " " + response_data.get("disclaimer", "")
            
        elif response_data.get("type") == "medical_report_analysis":
            # Speak the summary + disclaimer
            text_to_speak = response_data.get("summary", "") + " " + response_data.get("disclaimer", "")
            
        elif response_data.get("input_type") == "medical_report":
            # Speak the interpretation + disclaimer
            text_to_speak = response_data.get("interpretation", "") + " " + response_data.get("disclaimer", "")

        elif response_data.get("input_type") == "medical_image":
            # Speak the observations summary + disclaimer
            obs = ", ".join(response_data.get("observations", []))
            text_to_speak = f"Based on the image, I observe: {obs}. " + response_data.get("disclaimer", "")
            
        elif "health_information" in response_data:
             text_to_speak = response_data["health_information"]

        if text_to_speak:
            audio_filename = speech_service.text_to_speech(text_to_speak)
            if audio_filename:
                # Construct full URL (assuming localhost for now, ideally use env var for base URL)
                audio_url = f"/static/audio/{audio_filename}"
                
    except Exception as e:
        print(f"⚠️ TTS Generation failed: {e}")

    # 8. Store the conversation
    # Use full JSON response for dashboard consistency (styling)
    # The mongo_memory.get_user_memory will clean it for LLM context
    mongo_memory.store_message(user_id_str, "user", final_prompt)
    
    # Extract report type for metadata storage
    report_type = "general"
    is_force_report = bool(report_file or image_file) # If file was uploaded, it's a report
    
    try:
        resp_parsed = json.loads(text_response)
        report_type = resp_parsed.get("type") or resp_parsed.get("input_type") or "general"
        
        # DEBUG: Verify if report detection logic in mongo_memory will pick this up
        print(f"DEBUG: Storing assistant message. Keys: {list(resp_parsed.keys())}, ForceReport: {is_force_report}")
    except:
        pass
        
    report_id = mongo_memory.store_message(
        user_id_str, 
        "assistant", 
        text_response,
        report_type=report_type,
        force_report=is_force_report
    )

    # 9. Return all relevant data to the frontend
    return {
        "text_response": text_response,
        "transcribed_text": transcribed_text,
        "image_caption": image_caption,
        "audio_url": audio_url,
        "report_id": report_id
    }


