# backend/llm_service.py
import os
import json
import groq
from typing import Any
from groq import AsyncGroq
from dotenv import load_dotenv
from fastapi import Request
from schemas import RiskAssessment, Explanation, Recommendations, HealthReport
import mongo_memory
from rag_service import rag_service
from structured_memory import structured_memory
from rag_router import rag_router, QueryIntent, DatasetType
from audit_logger import audit_logger

load_dotenv()

# --- Configuration ---
PRIMARY_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama-3.1-8b-instant"  # Faster, higher rate limits
LLM_MODEL = PRIMARY_MODEL

client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY")) if os.getenv("GROQ_API_KEY") else None

if client:
    print(f"✅ Async Groq client for LLM initialized. Primary: {PRIMARY_MODEL}, Fallback: {FALLBACK_MODEL}")
else:
    print("⚠️ WARNING: GROQ_API_KEY not found! LLM service disabled.")

async def call_llm_with_fallback(messages: list[dict], response_format: dict | None = None, use_primary: bool = True) -> str:
    """
    Calls Groq LLM with automatic fallback to a smaller model if rate limited.
    """
    if not client:
        return json.dumps({"summary": "Service Unavailable", "disclaimer": "Check API Keys"})

    # Determine which model to start with
    current_model = PRIMARY_MODEL if use_primary else FALLBACK_MODEL
    
    try:
        # Attempt 1
        print(f"🤖 Calling LLM ({current_model})...")
        response = await client.chat.completions.create(
            messages=messages,
            model=current_model,
            response_format=response_format
        )
        return response.choices[0].message.content
    except groq.RateLimitError as e:
        # If we already tried the fallback or if we were using the primary and it failed
        if current_model == PRIMARY_MODEL:
            print(f"⚠️ Rate limit reached for {PRIMARY_MODEL}. Falling back to {FALLBACK_MODEL}...")
            try:
                # Attempt 2 with fallback model
                response = await client.chat.completions.create(
                    messages=messages,
                    model=FALLBACK_MODEL,
                    response_format=response_format
                )
                return response.choices[0].message.content
            except Exception as fallback_error:
                print(f"❌ Fallback model also failed: {fallback_error}")
                raise fallback_error
        else:
            print(f"❌ Rate limit reached for {current_model}. No further fallback available.")
            raise e
    except Exception as e:
        print(f"❌ LLM Error ({current_model}): {e}")
        raise e

async def get_streaming_llm_response(system_prompt: str):
    """
    Yields chunks from a streaming LLM response.
    """
    if not client:
        yield "LLM service is unavailable."
        return

    messages = [{"role": "system", "content": system_prompt}]
    try:
        stream = await client.chat.completions.create(
            messages=messages,
            model=LLM_MODEL,
            stream=True
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except Exception as e:
        print(f"❌ Streaming LLM Error: {e}")
        yield "An error occurred while generating the response."


# --- Symptom Fallback Dictionary (CRITICAL SAFETY FEATURE) ---
# This ensures symptom queries NEVER fail, even if RAG is down or data is missing
SYMPTOM_FALLBACKS = {
    "nausea": "Nausea is a feeling of sickness with an urge to vomit. Common causes include food poisoning, motion sickness, pregnancy, medications, viral infections, or digestive issues. Stay hydrated with small sips of water or clear fluids. Avoid strong smells and greasy foods. Rest in a comfortable position. See a doctor if nausea persists beyond 24-48 hours, is accompanied by severe abdominal pain, or if you cannot keep fluids down.",
    
    "headache": "Headaches are pain or discomfort in the head or face area. Common types include tension headaches (from stress or muscle tension), migraines (often with sensitivity to light/sound), and cluster headaches. Causes range from dehydration, stress, lack of sleep, eye strain, to underlying conditions. Rest in a quiet, dark room, stay hydrated, and over-the-counter pain relievers may help. Seek immediate medical attention for sudden severe headaches, headaches after head injury, or headaches with fever, stiff neck, confusion, or vision changes.",
    
    "bloating": "Bloating is a feeling of fullness, tightness, or swelling in the abdomen. Common causes include overeating, eating too quickly, gas buildup, constipation, food intolerances (like lactose or gluten), or swallowing air. Eating slowly, chewing thoroughly, avoiding carbonated drinks, regular exercise, and staying hydrated may help. Consult a doctor if bloating is persistent, severe, accompanied by weight loss, or if you notice changes in bowel habits.",
    
    "stomach pain": "Stomach pain (abdominal pain) can range from mild discomfort to severe cramping. Common causes include indigestion, gas, constipation, food poisoning, stomach flu, menstrual cramps, or stress. The location and type of pain can provide clues. Rest, staying hydrated, and avoiding irritating foods may help. Seek medical attention if pain is severe, persistent, accompanied by fever, vomiting blood, bloody stools, or if you're pregnant.",
    
    "dizziness": "Dizziness is a feeling of lightheadedness, unsteadiness, or a spinning sensation (vertigo). Common causes include dehydration, low blood sugar, sudden position changes (standing up quickly), inner ear problems, medications, or anxiety. Sit or lie down immediately if you feel dizzy. Stay hydrated and avoid sudden movements. See a doctor if dizziness is frequent, severe, accompanied by chest pain, difficulty breathing, fainting, or if it affects your daily activities.",
    
    "fever": "Fever is a temporary increase in body temperature, often due to an infection. Normal body temperature is around 98.6°F (37°C); fever is generally considered 100.4°F (38°C) or higher. Common causes include viral or bacterial infections, heat exhaustion, or inflammatory conditions. Rest, stay hydrated, and over-the-counter fever reducers may help. Seek medical attention for fever above 103°F (39.4°C), fever lasting more than 3 days, fever in infants under 3 months, or if accompanied by severe headache, rash, difficulty breathing, or confusion.",
    
    "fatigue": "Fatigue is persistent tiredness or exhaustion that doesn't improve with rest. Common causes include lack of sleep, stress, poor diet, dehydration, anemia, thyroid problems, depression, or chronic conditions. Ensure adequate sleep (7-9 hours), maintain a balanced diet, exercise regularly, manage stress, and stay hydrated. Consult a doctor if fatigue is severe, persistent for weeks, unexplained, or accompanied by other symptoms like weight changes, pain, or mood changes.",
    
    "cough": "A cough is a reflex that helps clear the airways of mucus, irritants, or foreign particles. Common causes include viral infections (common cold, flu), allergies, asthma, acid reflux, or environmental irritants. Dry coughs produce no mucus; wet coughs produce phlegm. Stay hydrated, use a humidifier, avoid irritants, and throat lozenges may help. See a doctor if cough persists beyond 3 weeks, produces blood, is accompanied by high fever, difficulty breathing, or chest pain.",
    
    "shortness of breath": "Shortness of breath (dyspnea) is difficulty breathing or feeling like you can't get enough air. Common causes include physical exertion, anxiety, asthma, allergies, respiratory infections, or heart conditions. Sit upright, try slow deep breathing, and stay calm. Seek immediate medical attention if shortness of breath is sudden and severe, accompanied by chest pain, bluish lips or face, or if you have a history of heart or lung disease.",
    
    "chest pain": "Chest pain can range from sharp stabbing to dull aching sensations. While many causes are not heart-related (muscle strain, acid reflux, anxiety), chest pain can also indicate serious conditions. Common non-cardiac causes include heartburn, muscle strain, costochondritis, or anxiety. SEEK IMMEDIATE EMERGENCY CARE (call 911) if chest pain is severe, crushing, accompanied by shortness of breath, sweating, nausea, pain radiating to arm/jaw, or if you have risk factors for heart disease.",
    
    "joint pain": "Joint pain (arthralgia) is discomfort, aching, or soreness in any joint. Common causes include arthritis (osteoarthritis, rheumatoid arthritis), injuries, overuse, gout, or infections. Rest the affected joint, apply ice for acute pain or heat for chronic stiffness, gentle stretching, and over-the-counter pain relievers may help. See a doctor if joint pain is severe, accompanied by swelling, redness, warmth, fever, or if it limits your daily activities.",
    
    "muscle ache": "Muscle aches (myalgia) are soreness or pain in muscles. Common causes include overexertion, tension, stress, minor injuries, viral infections (flu), or dehydration. Rest, gentle stretching, massage, warm baths, and staying hydrated may help. Over-the-counter pain relievers can provide relief. Consult a doctor if muscle pain is severe, persistent, not related to activity, accompanied by fever, rash, or if you have difficulty breathing or swallowing.",
    
    "diarrhea": "Diarrhea is loose, watery stools occurring more frequently than normal. Common causes include viral or bacterial infections, food poisoning, food intolerances, medications, or stress. Stay hydrated with water, clear broths, or oral rehydration solutions. Avoid dairy, fatty, or spicy foods temporarily. See a doctor if diarrhea persists beyond 2 days, is accompanied by high fever, severe abdominal pain, blood in stools, signs of dehydration, or if you have recently traveled.",
    
    "constipation": "Constipation is infrequent bowel movements or difficulty passing stools. Common causes include low fiber diet, inadequate water intake, lack of physical activity, medications, or ignoring the urge to go. Increase fiber intake (fruits, vegetables, whole grains), drink plenty of water, exercise regularly, and establish a regular bathroom routine. Consult a doctor if constipation is severe, persistent, accompanied by blood in stools, severe abdominal pain, or unexplained weight loss.",
    
    "insomnia": "Insomnia is difficulty falling asleep, staying asleep, or waking too early. Common causes include stress, anxiety, poor sleep habits, caffeine or alcohol, medications, or underlying health conditions. Maintain a regular sleep schedule, create a relaxing bedtime routine, avoid screens before bed, keep the bedroom dark and cool, and limit caffeine. See a doctor if insomnia persists for weeks, affects your daily functioning, or if you suspect an underlying medical condition.",
    
    "rash": "A rash is a change in skin color, texture, or appearance, often with redness, bumps, or itching. Common causes include allergic reactions, eczema, contact dermatitis, viral infections, heat rash, or insect bites. Keep the area clean and dry, avoid scratching, use gentle moisturizers, and over-the-counter anti-itch creams may help. Seek medical attention if rash is widespread, accompanied by fever, difficulty breathing, swelling of face/throat, or if it doesn't improve within a few days.",
    
    "back pain": "Back pain can affect the lower, middle, or upper back. Common causes include muscle strain, poor posture, lifting heavy objects incorrectly, herniated discs, or arthritis. Rest, gentle stretching, applying heat or ice, maintaining good posture, and over-the-counter pain relievers may help. See a doctor if pain is severe, radiates down the legs, accompanied by numbness or weakness, follows an injury, or persists beyond a few weeks.",
    
    "sore throat": "A sore throat is pain, scratchiness, or irritation of the throat. Common causes include viral infections (common cold, flu), bacterial infections (strep throat), allergies, dry air, or irritants. Gargle with warm salt water, stay hydrated, use throat lozenges, and rest your voice. See a doctor if sore throat is severe, lasts more than a week, accompanied by high fever, difficulty swallowing or breathing, or if you notice white patches in the throat.",
    
    "runny nose": "A runny nose (rhinorrhea) is excess drainage from the nasal passages. Common causes include common cold, allergies, sinus infections, cold weather, or irritants. Stay hydrated, use a humidifier, saline nasal sprays, and rest. Over-the-counter decongestants may provide relief. Consult a doctor if symptoms persist beyond 10 days, accompanied by high fever, severe headache, facial pain, or if nasal discharge is thick and colored.",
    
    "vomiting": "Vomiting is forcefully expelling stomach contents through the mouth. Common causes include viral gastroenteritis (stomach flu), food poisoning, motion sickness, pregnancy, medications, or migraines. Avoid solid foods initially, sip clear fluids slowly, rest, and gradually reintroduce bland foods. Seek medical attention if vomiting persists beyond 24 hours, you cannot keep fluids down, there's blood in vomit, severe abdominal pain, or signs of dehydration.",
    
    "sweating": "Excessive sweating (hyperhidrosis) is sweating more than necessary for temperature regulation. Common causes include physical activity, hot weather, anxiety, fever, menopause, medications, or hyperthyroidism. Stay cool, wear breathable fabrics, stay hydrated, and use antiperspirants. See a doctor if sweating is excessive, unexplained, occurs at night, accompanied by weight loss, fever, or if it interferes with daily activities.",
    
    "chills": "Chills are feeling cold with shivering, often occurring with fever. Common causes include infections (viral or bacterial), exposure to cold, low blood sugar, or hypothyroidism. Dress warmly, stay hydrated, and rest. Monitor body temperature. Seek medical attention if chills are accompanied by high fever, severe symptoms, confusion, difficulty breathing, or if you have a weakened immune system.",
    
    "swelling": "Swelling (edema) is enlargement of body parts due to fluid buildup. Common causes include injury, inflammation, prolonged sitting/standing, pregnancy, medications, or underlying conditions (heart, kidney, liver problems). Elevate the affected area, reduce salt intake, stay active, and wear compression garments if recommended. See a doctor if swelling is sudden, severe, one-sided, accompanied by pain, redness, warmth, shortness of breath, or if you have a history of heart or kidney disease.",
    
    "itching": "Itching (pruritus) is an irritating sensation that makes you want to scratch. Common causes include dry skin, allergic reactions, insect bites, eczema, psoriasis, or infections. Keep skin moisturized, avoid hot showers, use gentle soaps, wear soft fabrics, and over-the-counter anti-itch creams may help. Consult a doctor if itching is severe, widespread, persistent, accompanied by rash, fever, or if it affects your sleep.",
    
    "numbness": "Numbness is loss of sensation or tingling feeling. Common causes include pressure on nerves (sitting in one position), poor circulation, nerve damage, vitamin deficiencies, or anxiety. Change position, move around, and gentle massage may help. Seek immediate medical attention if numbness is sudden, affects one side of the body, accompanied by weakness, difficulty speaking, vision changes, or severe headache (possible stroke).",
    
    "weakness": "Weakness is lack of physical strength or energy. Common causes include fatigue, lack of sleep, dehydration, poor nutrition, anemia, infections, or chronic conditions. Ensure adequate rest, balanced diet, hydration, and regular exercise. See a doctor if weakness is sudden, severe, progressive, affects one side of the body, accompanied by other symptoms, or if it significantly impacts daily activities.",
    
    "loss of appetite": "Loss of appetite is reduced desire to eat. Common causes include stress, anxiety, depression, infections, medications, digestive issues, or chronic illnesses. Eat small frequent meals, choose nutrient-dense foods, stay hydrated, and address underlying stress. Consult a doctor if loss of appetite persists, accompanied by weight loss, nausea, abdominal pain, or if you have difficulty swallowing.",
    
    "weight loss": "Unintentional weight loss is losing weight without trying. Common causes include stress, increased physical activity, hyperthyroidism, diabetes, digestive disorders, or chronic illnesses. Track your eating and activity patterns. See a doctor if you lose more than 5% of body weight in 6-12 months without trying, especially if accompanied by fatigue, changes in appetite, or other symptoms.",
    
    "anxiety": "Anxiety is feelings of worry, nervousness, or unease. Common causes include stress, major life changes, trauma, caffeine, or underlying anxiety disorders. Practice relaxation techniques (deep breathing, meditation), regular exercise, adequate sleep, limit caffeine, and talk to someone you trust. Seek professional help if anxiety is severe, persistent, interferes with daily life, or if you experience panic attacks.",
    
    "confusion": "Confusion is difficulty thinking clearly, concentrating, or making decisions. Common causes include dehydration, low blood sugar, medications, infections, sleep deprivation, or serious conditions. Ensure hydration, check blood sugar if diabetic, and rest. SEEK IMMEDIATE MEDICAL ATTENTION if confusion is sudden, severe, accompanied by fever, headache, stiff neck, difficulty breathing, chest pain, or if the person is elderly or has chronic conditions."
}

def get_symptom_fallback(query: str) -> str:
    """
    Returns a safe, general symptom explanation if the query matches a known symptom.
    Improved matching to handle multi-word variations and word boundaries.
    """
    query_lower = query.lower()
    
    # 1. Normalize query: remove extra spaces, punctuation
    import re
    normalized_query = re.sub(r'[^\w\s]', '', query_lower)
    
    # Special case: "head ache" -> "headache"
    normalized_query = normalized_query.replace("head ache", "headache")
    normalized_query = normalized_query.replace("stomach ache", "stomach pain")
    normalized_query = normalized_query.replace("back ache", "back pain")

    # 2. Check for exact or partial matches with word boundaries
    for symptom, explanation in SYMPTOM_FALLBACKS.items():
        # Check if symptom is in the normalized query as a whole word
        pattern = rf"\b{re.escape(symptom)}\b"
        if re.search(pattern, normalized_query):
            return explanation
    
    return None

# --- Helper Functions ---
def calculate_bmi(weight, height):
    if weight and height:
        try:
            bmi = weight / ((height / 100) ** 2)
            if bmi < 18.5: return f"{bmi:.1f} (Underweight)"
            if bmi < 25: return f"{bmi:.1f} (Normal)"
            if bmi < 30: return f"{bmi:.1f} (Overweight)"
            return f"{bmi:.1f} (Obese)"
        except:
            return "Unknown"
    return "Unknown"

# --- Safety Layer (Guardrails) ---
class Guardrails:
    CRITICAL_KEYWORDS = ["suicide", "kill myself", "chest pain", "heart attack", "stroke", "difficulty breathing", "unconscious"]
    
    @staticmethod
    def check_safety(text: str) -> dict[str, Any]:
        """
        Deterministic safety check.
        Returns None if safe, or a predefined Error Response if unsafe.
        """
        text_lower = text.lower()
        
        # 1. Emergency Detection
        for keyword in Guardrails.CRITICAL_KEYWORDS:
            if keyword in text_lower:
                return {
                    "is_safe": False,
                    "response": {
                        "summary": "🚨 CRITICAL SAFETY ALERT",
                        "possible_causes": ["Potential Medical Emergency"],
                        "risk_assessment": {
                            "severity": "EMERGENCY",
                            "confidence_score": 1.0,
                            "uncertainty_reason": "Keyword detected: " + keyword
                        },
                        "explanation": {
                            "reasoning": f"You mentioned '{keyword}', which requires immediate medical attention.",
                            "history_factor": "Safety Override Triggered",
                            "profile_factor": "N/A"
                        },
                        "recommendations": {
                            "immediate_action": "CALL EMERGENCY SERVICES (911) IMMEDIATELY.",
                            "lifestyle_advice": ["Do not wait.", "Seek professional help now."],
                            "food_advice": []
                        },
                        "disclaimer": "This system cannot handle emergencies. Please contact local authorities."
                    }
                }
        return {"is_safe": True}

guardrails = Guardrails()

# --- History Layer (Analysis) ---
def analyze_history_trends(history: list[dict], current_symptoms: str) -> str:
    """
    Analyzes past messages to detect patterns like worsening symptoms or repetition.
    """
    if not history:
        return "No previous history."
    
    recent_symptoms = [msg['content'] for msg in history if msg['role'] == 'user'][-3:]
    if not recent_symptoms:
        return "No recent user symptoms found in history."

    # Simple heuristic: Check if last 3 messages contain similar keywords to current
    current_words = set(current_symptoms.lower().split())
    repeated_count = 0
    
    for prev in recent_symptoms:
        prev_words = set(prev.lower().split())
        # Check for meaningful overlap (ignoring common stop words would be better, but this is a start)
        overlap = current_words.intersection(prev_words)
        if len(overlap) >= 2: # At least 2 matching words
            repeated_count += 1
            
    if repeated_count > 0:
        return f"⚠️ RECURRING ISSUE: User has reported similar symptoms in {repeated_count} of the last 3 interactions. Evaluate for worsening condition."
    
    return "New symptom presentation."

# --- 7-Core Assessment Pipeline Prompts ---

PROMPT_INTENT_CLASSIFIER = """
You are an intent classifier for a medical AI assistant.

Classify the user's message into EXACTLY ONE of:
  MEDICAL  → user mentions symptoms, health issues, medical questions, or body-related concerns
  GENERAL  → casual conversation, greetings, jokes, or anything unrelated to health

EXAMPLES:
  MEDICAL: "I have fever", "headache for 2 days", "feeling nausea", "what is diabetes"
  GENERAL: "hi", "tell me a joke", "what are you doing", "who are you"

USER MESSAGE:
"{message}"

OUTPUT: (one word only, no punctuation)
"""

# Strict fallback for non-medical inputs — no chatbot behaviour
HEALTH_ONLY_REDIRECT = (
    "I am an AI Health Assistant. "
    "I can help with symptoms, conditions, and medical guidance. "
    "Please describe your health concern."
)

PROMPT_CONTROLLER = """
You are a medical assessment controller. Your goal is to decide if a query needs a follow-up question for a better clinical assessment.

Your task is to:
1. Determine whether the user query is informational (e.g., "What is Wilson disease?") or symptom-based (e.g., "I have a headache").
2. Decide whether clarification is HELPFUL to provide a more accurate and safe assessment.

🚨 CLINICAL INTERVIEW RULES:

1. You SHOULD ask follow-up questions if:
   - The user provides a symptom without duration (e.g., "I have a cough" vs "I've had a cough for 3 days").
   - The user provides a symptom without severity or triggers.
   - The input is vague (e.g., "I feel sick").
   - Knowing 1-2 more details would significantly change the potential advice.

2. You should NOT ask follow-up questions for:
   - General informational queries about diseases or drugs.
   - Queries that already contain rich context (duration, severity, location).
   - "Symptoms of [disease]" queries.

3. Follow-up Guidelines:
-   Ask EXACTLY 1 targeted question.
-   Prefer duration if missing (e.g., "How long has this been happening?"). Otherwise ask for one missing key symptom detail.

OUTPUT FORMAT (JSON):
{
  "is_informational": boolean,
  "needs_clarification": boolean,
  "questions": ["One short targeted question"] (only if needs_clarification is true),
  "detected_intent": "informational" | "symptom_based"
}
"""

PROMPT_MEMORY_SELECTOR = """
You are responsible for selecting relevant user history.
Use past user data ONLY IF:
1. The current topic matches previous topics.
2. The user explicitly confirmed relevance (User Confirmation: "yes").

If the user selected "No" or "Skip", do not include past data.

Current User Input: {user_input}
User Confirmation: {user_confirmation}
Past Data: {past_data}

Output either:
"Relevant memory included: [Summary of relevant past data]"
OR "No relevant memory used"
"""

PROMPT_MEDICAL_RAG = """
You are a Medical AI Assistant specializing in accurate, evidence-based health information.

TASK:
1. Provide a detailed, clear explanation for the user's health-related query.
2. If the user asks about a specific disease (like Dengue, Malaria, Eczema, Hives, etc.), you MUST provide a comprehensive explanation including:
   - What the condition is (definition).
   - Common symptoms and how they present.
   - Typical causes or triggers.
   - General care, management, and prevention methods.
3. Use the RETRIEVED MEDICAL KNOWLEDGE provided below to ground your answer. This is your primary source of truth.
4. If the retrieved knowledge is insufficient for a specific disease, use your internal medical knowledge base to provide a comprehensive answer, but always maintain a helpful and cautious tone.
5. ALWAYS include a disclaimer that this is not a medical diagnosis.

🚨 CRITICAL: You MUST include the "health_information" field in your JSON output. This field should contain the detailed explanation of the condition, symptoms, and prevention as described in Task 2.

OUTPUT FORMAT (JSON):
{{
  "type": "health_report",
  "health_information": "Detailed, comprehensive explanation of the condition, including definition, symptoms, causes, and prevention.",
  "possible_conditions": ["Condition 1", "Condition 2"],
  "reasoning_brief": "Brief reasoning for the analysis.",
  "recommended_next_steps": "Advice on what to do next (e.g., stay hydrated, see a doctor).",
  "ai_confidence": "Confidence level (Low/Medium/High)",
  "trusted_sources": ["Source 1", "Source 2"],
  "disclaimer": "This is for informational purposes and not a diagnosis. Please consult a healthcare professional."
}}

CURRENT USER QUERY:
{user_query}

CONFIRMED USER CONTEXT:
{user_context}

RETRIEVED MEDICAL KNOWLEDGE:
{rag_data}
"""

PROMPT_FEEDBACK_REFINER = """
The user has indicated whether the response was helpful. 
Feedback: {feedback_rating}
Comment: {feedback_comment}

If feedback is "negative":
1. Identify which part was unclear or insufficient based on the previous response and user comment.
2. Suggest what additional clarification or data is needed.
3. Adjust strategy for future queries.

Do not change medical facts. Improve clarity and questioning.
"""

# --- PROMPT: Medical Report Analysis ---
PROMPT_REPORT_ANALYZER = """
You are a Medical Lab Result Expert. Your role is to analyze and explain medical reports directly to the user.

TASK:
1. Explain what each lab test or marker means in simple terms.
2. Analyze the user's values against normal ranges.
3. Provide a summary of the findings.
4. If the report indicates a specific condition, provide a detailed explanation of that condition (definition, symptoms, causes, management).
5. DO NOT provide a medical diagnosis.

🚨 CRITICAL: You MUST include BOTH the "summary" field AND the "health_information" field in your JSON output. 
- The "summary" field should contain a concise but thorough overview of the entire report findings.
- The "health_information" field MUST contain the detailed explanation of any conditions, symptoms, and general medical knowledge relevant to the report.

INPUT DATA:
- EXTRACTED LAB DATA: {report_text}
- USER CONTEXT: {user_context}
- MEDICAL REFERENCE DATA (RAG): {rag_data}

OUTPUT FORMAT (JSON):
{{
  "type": "medical_report_analysis",
  "summary": "MANDATORY: General overview of the report, including key findings and overall health status.",
  "health_information": "MANDATORY: Detailed explanation of any identified conditions, symptoms, causes, and general medical care information.",
  "test_analysis": [
    {{
      "test_name": "Name",
      "value": "User's value",
      "normal_range": "Reference range",
      "status": "Low/Normal/High",
      "explanation": "Simple explanation of this result."
    }}
  ],
  "general_guidance": ["List of suggestions"],
  "when_to_consult_doctor": ["Specific signs to watch for"],
  "ai_confidence": "Confidence level",
  "disclaimer": "This is for informational purposes only."
}}
"""

# --- PROMPT: Medical Image Analysis (Router & Specialists) ---
PROMPT_MODALITY_DETECTOR = """
You are a Medical Image Modality Detector. Your task is to classify an image analysis caption into one of the following modalities:
- radiology (Internal scans: X-ray, MRI, CT, Ultrasound, Bone scans)
- dermatology (External skin: Rash, lesion, skin condition, skin infection)
- ophthalmology (Eye related: Retina, Red eye, eye surface, ocular condition)
- medical_document (Text-based: Lab report, prescription, chart, graph, paper document)
- unknown (Ambiguous or non-medical content)

INPUT CAPTION: {image_caption}

🚨 CLASSIFICATION RULES:
1. If the caption mentions "Eye", "Retina", "Ocular", or "Red Eye", classify as 'ophthalmology'.
2. If the caption mentions "Skin", "Rash", "Dermatology", or "Lesion", classify as 'dermatology'.
3. If the caption mentions "X-ray", "Radiograph", "MRI", "CT", or "Ultrasound", classify as 'radiology'.
4. If the caption mentions "Document", "Prescription", "Report", or "Chart", classify as 'medical_document'.
5. Look at the confidence scores in parentheses. If multiple modalities are mentioned, pick the one with the highest total score, BUT prioritize 'ophthalmology' and 'dermatology' for external photos and 'radiology' for internal scans.

OUTPUT FORMAT (JSON):
{{
  "modality": "radiology" | "dermatology" | "ophthalmology" | "medical_document" | "unknown",
  "confidence": float (0.0 to 1.0),
  "reason": "Brief explanation for the classification"
}}
"""

PROMPT_RADIOLOGY_SPECIALIST = """
You are a Radiology Expert. Your task is to analyze the observations from a medical scan (X-ray, MRI, CT, Ultrasound) and provide a clear, detailed explanation for the user.

TASK:
1. Summarize the visual observations from the scan.
2. For each possible condition identified, provide a clear, detailed explanation of what it is, common causes, and typical management.
3. Use the RETRIEVED MEDICAL KNOWLEDGE (RAG) to ground your explanations in evidence.
4. Maintain a professional yet accessible tone.

🚨 CRITICAL: You MUST include the "summary" field in your JSON output. This field should contain a concise but thorough overview of the findings and explanations.

INPUT DATA:
- VISION OBSERVATIONS: {image_caption}
- IMAGE TEXT (OCR): {image_text}
- USER CONTEXT: {user_context}
- MEDICAL REFERENCE DATA (RAG): {rag_data}

OUTPUT FORMAT (JSON):
{{
  "input_type": "medical_image",
  "modality": "radiology",
  "summary": "MANDATORY: A clear, concise summary of the radiology findings and their significance.",
  "health_information": "Detailed explanation of the possible conditions identified, including definitions and symptoms.",
  "observations": ["List of visual findings"],
  "possible_conditions": ["Conditions associated with these findings"],
  "general_advice": "Recommended next steps",
  "confidence_level": "High/Medium/Low",
  "disclaimer": "This is a screening-level insight and not a medical diagnosis."
}}
"""

PROMPT_SKIN_SPECIALIST = """
You are a Dermatology Expert. Your task is to analyze observations from a skin image (rash, lesion, etc.) and provide a clear, detailed explanation for the user.

TASK:
1. Summarize the visual observations from the skin image.
2. For each possible condition identified (e.g., Eczema, Psoriasis, Hives), provide a clear, detailed explanation of what it is, its common characteristics, and general care.
3. Use the RETRIEVED MEDICAL KNOWLEDGE (RAG) to ground your explanations in evidence.
4. Maintain a helpful and empathetic tone.

🚨 CRITICAL: You MUST include the "summary" field in your JSON output. This field should contain a concise but thorough overview of the findings and explanations.

INPUT DATA:
- VISION OBSERVATIONS: {image_caption}
- IMAGE TEXT (OCR): {image_text}
- USER CONTEXT: {user_context}
- MEDICAL REFERENCE DATA (RAG): {rag_data}

OUTPUT FORMAT (JSON):
{{
  "input_type": "medical_image",
  "modality": "dermatology",
  "summary": "MANDATORY: A clear, concise summary of the dermatological observations and their significance.",
  "health_information": "Detailed explanation of the possible skin conditions identified, including definitions and characteristics.",
  "observations": ["List of visual findings"],
  "possible_conditions": ["Conditions associated with these findings"],
  "general_advice": "Skin care or next steps",
  "confidence_level": "High/Medium/Low",
  "disclaimer": "This is a screening-level insight and not a medical diagnosis."
}}
"""

PROMPT_EYE_SPECIALIST = """
You are an Ophthalmology Expert. Your task is to analyze observations from an eye image and provide a clear, detailed explanation for the user.

TASK:
1. Summarize the visual observations from the eye image.
2. For each possible condition identified, provide a clear, detailed explanation of what it is, how it affects vision, and general care.
3. Use the RETRIEVED MEDICAL KNOWLEDGE (RAG) to ground your explanations in evidence.
4. Maintain a professional and cautious tone.

🚨 CRITICAL: You MUST include the "summary" field in your JSON output. This field should contain a concise but thorough overview of the findings and explanations.

INPUT DATA:
- VISION OBSERVATIONS: {image_caption}
- IMAGE TEXT (OCR): {image_text}
- USER CONTEXT: {user_context}
- MEDICAL REFERENCE DATA (RAG): {rag_data}

OUTPUT FORMAT (JSON):
{{
  "input_type": "medical_image",
  "modality": "ophthalmology",
  "summary": "MANDATORY: A clear, concise summary of the ophthalmological observations and their significance.",
  "health_information": "Detailed explanation of the possible eye conditions identified, including definitions and impact.",
  "observations": ["List of visual findings"],
  "possible_conditions": ["Conditions associated with these findings"],
  "general_advice": "Eye care or next steps",
  "confidence_level": "High/Medium/Low",
  "disclaimer": "This is a screening-level insight and not a medical diagnosis."
}}
"""

PROMPT_HITL_ESCALATION = """
You are a Medical Safety Agent. An image analysis request has been flagged for Human-in-the-Loop (HITL) escalation.
Reason for escalation: {escalation_reason}

STRICT RULES:
1. DO NOT provide any medical interpretation or advice.
2. DO NOT suggest any conditions.
3. Be calm, professional, and clear.
4. Recommend consulting a qualified healthcare professional.

OUTPUT FORMAT (JSON):
{{
  "input_type": "medical_image",
  "status": "HITL_ESCALATED",
  "message": "⚠️ This image cannot be safely analyzed by the system. Please consult a qualified healthcare professional for proper evaluation.",
  "reason": "{escalation_reason}",
  "disclaimer": "Human-in-the-loop escalation triggered for safety."
}}
"""

# --- Reasoning Layer (LLM) ---
async def run_clinical_analysis(profile: dict, history: list[dict], inputs: dict, request: Request | None = None) -> str:
    """
    Main orchestration function for the 'Google-Level' 8-stage pipeline.
    """
    user_id = int(profile.get("user_id")) if profile.get("user_id") else None

    if not client:
        await audit_logger.log_event(
            action="AI_QUERY",
            status="FAILURE",
            user_id=user_id,
            request=request,
            metadata={"reason": "Service Unavailable - API Key missing"}
        )
        return json.dumps({"summary": "Service Unavailable", "disclaimer": "Check API Keys"})

    # --- STEP 1: Input Harmonization (Multimodal) ---
    user_text = inputs.get("text_query", "") or ""
    voice_text = inputs.get("transcribed_text", "") or ""
    image_desc = inputs.get("image_caption", "") or ""
    report_text = inputs.get("report_text", "") or ""
    user_confirmation = (inputs.get("user_confirmation", "skip") or "skip").lower()
    
    print(f"DEBUG: Harmonized report_text length: {len(report_text)}")
    if report_text:
        print(f"DEBUG: report_text snippet: {report_text[:100]}...")
    
    # Ensure combined_input has at least a placeholder if report_text exists but OCR failed
    combined_input = f"{user_text} {voice_text} {image_desc} {report_text}".strip()
    
    # --- Context Bridge: now handled upstream in query_service.py ---
    # The merged text_query (e.g. "getting fever 5 days") is already in inputs["text_query"]
    # and combined_input was built from it above. Just read the flag.
    _bridge_merged = bool(inputs.get("bridge_active", False))
    if _bridge_merged:
        print(f"⚡ Bridge active (from query_service) → combined_input: {combined_input!r}")
    if not combined_input and report_text:
        combined_input = "[Medical Report Analysis Requested]"
        
    # Check if ANY input was provided (including multimodal data)
    has_any_input = any([user_text, voice_text, image_desc, report_text])
    
    if not has_any_input:
        return json.dumps({"summary": "No input provided.", "disclaimer": "Please provide symptoms or upload a report."})

    # --- STEP 1.5: Detect Analysis Mode ---
    is_report_analysis = bool(report_text)
    is_image_analysis = bool(image_desc)
    
    if is_report_analysis:
        if "[PDF Report Uploaded" in report_text or "[Image Report Uploaded" in report_text:
            print("⚠️ Report Analysis Mode (Placeholder detected)")
        else:
            print("📋 Entering Medical Report Analysis Mode")
    
    if is_image_analysis:
        print("📷 Entering Medical Image Analysis Mode")

    if is_report_analysis and is_image_analysis:
        print("🧬 Entering Combined Multimodal Analysis Mode")

    modality = None
    escalation_reason = None

    # --- STEP 2: Deterministic Guardrails (Safety) ---
    safety_result = guardrails.check_safety(combined_input)
    if not safety_result["is_safe"]:
        return json.dumps(safety_result["response"])
    skip_intent_detection = False
    
    # --- STEP 2.1: SESSION RESOLVER (FOLLOW-UP DETECTOR) ---
    if not is_report_analysis and not is_image_analysis and user_text.strip():
        try:
            from clinical_memory import session_repo, ClinicalState
            _skey = str(profile.get("user_id", "")) or None
            session = session_repo.get_or_create_session(_skey)
            prev_state = session.state
            
            # --- SESSION RESET (Moved from Step 3 to prevent state bleed into Session Resolver) ---
            # Find last assistant message for context
            last_message_str = ""
            if history:
                for m in reversed(history):
                    if m.get("role") == "assistant":
                        last_message_str = m.get("content", "").lower()
                        break

            # A session is considered "answering a clarification" if the last message was a question
            _is_answering_clarification = "how long" in last_message_str or "question" in last_message_str
            
            # A session is COMPLETE if either:
            # 1. It successfully collected both symptoms and duration
            # 2. The system already provided a final health report (e.g., from a symptom shortcut)
            _prev_has_data = bool(prev_state.symptoms and prev_state.duration)
            _prev_was_report = "since this is continuing" in last_message_str or "disclaimer" in last_message_str or "recommend" in last_message_str or "not a diagnosis" in last_message_str

            _prev_complete = _prev_has_data or _prev_was_report

            if _prev_complete and not _is_answering_clarification:
                session.state = ClinicalState()
                prev_state = session.state
                session_repo.save_session(session)
                print(f"🔄 SESSION RESET: Cleared previous session state. (was_report={_prev_was_report})")
            # --------------------------------------------------------------------------------------
            
            import re
            DURATION_PATTERN = r"\b(\d+)\s*(day|days|week|weeks|month|months|hour|hours|year|years|since\s+\w+|yesterday|last\s+\w+|a\s+few\s+days|this\s+(morning|evening|week))\b"
            _short_ans_match = re.search(DURATION_PATTERN, user_text.lower())
            _is_short_input = len(user_text.strip().split()) <= 4
            
            if session.state.pending_field and _is_short_input:
                print(f"🔄 Follow-Up Resolver: processing pending_field '{session.state.pending_field}'")
                field = session.state.pending_field
                
                if field == "duration":
                    session.state.duration = user_text.strip()
                elif field == "symptoms":
                    session.state.symptoms.append(user_text.strip())
                
                # MERGE INPUT SO RAG GETS THE FULL QUERY
                _syms_str = " and ".join(session.state.symptoms) if session.state.symptoms else ""
                if _syms_str:
                    combined_input = f"{_syms_str} {user_text.strip()}"
                else:
                    combined_input = user_text.strip()
                
                session.state.pending_field = None
                session_repo.save_session(session)
                skip_intent_detection = True
                _bridge_merged = True
                print(f"✅ State updated directly. Bypassing intent detection. Merged: {combined_input}")
            elif _short_ans_match and session.state.symptoms and _is_short_input:
                print("🛡 Hardening: Duration regex matched. Updating directly.")
                session.state.duration = user_text.strip()
                session.state.pending_field = None
                
                # MERGE INPUT SO RAG GETS THE FULL QUERY
                _syms_str = " and ".join(session.state.symptoms)
                combined_input = f"{_syms_str} {user_text.strip()}"
                
                session_repo.save_session(session)
                skip_intent_detection = True
                _bridge_merged = True
                print(f"✅ Quick duration detected. Bypassing intent detection. Merged: {combined_input}")
        except Exception as _ime:
            print(f"⚠️ Follow-Up Resolver failed/skipped ({_ime})")

    # --- STEP 2.2: MEDICAL / GENERAL INTENT GATE ---
    # Skip for multimodal inputs — images/reports/voice are always health-related
    _is_text_only = not (is_report_analysis or is_image_analysis or voice_text)
    if _is_text_only and combined_input and not skip_intent_detection:
        try:
            _intent_raw = await call_llm_with_fallback(
                messages=[{"role": "user", "content": PROMPT_INTENT_CLASSIFIER.format(message=combined_input)}],
                use_primary=False  # cheap single-word call
            )
            _intent = _intent_raw.strip().upper().split()[0] if _intent_raw.strip() else "MEDICAL"
            print(f"🧠 Intent Gate: {combined_input[:50]!r} → {_intent}")
        except Exception as _ie:
            print(f"⚠️ Intent gate failed ({_ie}), defaulting to MEDICAL")
            _intent = "MEDICAL"

        if _intent == "GENERAL":
            # Strict medical-only mode: always return the same redirect — never engage casually
            print(f"🚫 Non-medical input blocked: {combined_input[:60]!r}")
            return json.dumps({"type": "chat_message", "message": HEALTH_ONLY_REDIRECT})


    # --- STEP 2.5: SYMPTOM SHORTCUT CHECK (OPTIMIZATION) ---
    # Check if this is a common symptom query - if yes, skip LLM intent detection and go straight to fallback
    # This improves response time and reduces API costs for common queries
    query_lower = combined_input.lower()

    # Skip symptom shortcut if in report or image analysis mode
    if is_report_analysis or is_image_analysis:
        print(f"Skipping symptom shortcut for {'report' if is_report_analysis else 'image'} analysis")
        symptom_shortcut = None
    elif _bridge_merged:
        # CRITICAL: When a follow-up answer was merged (e.g. "headache fever from yesterday"),
        # the shortcut would match ONE symptom and return a generic single-symptom response,
        # ignoring the other symptoms and the duration context.
        # Always bypass the shortcut for merged inputs and let RAG give a FULL combined assessment.
        print("Bridge merged → skipping symptom shortcut to ensure full multi-symptom RAG response.")
        symptom_shortcut = None
    else:
        # Check for direct symptom mentions
        symptom_shortcut = get_symptom_fallback(combined_input)
        
        # MULTI-SYMPTOM CHECK: if more than one shortcut-eligible symptom is present,
        # skip the shortcut — RAG will give a properly combined multi-symptom analysis.
        if symptom_shortcut:
            import re as _re
            _matched_shortcuts = []
            _qn = _re.sub(r'[^\w\s]', '', query_lower).replace("head ache", "headache").replace("stomach ache", "stomach pain").replace("back ache", "back pain")
            for _sname in SYMPTOM_FALLBACKS.keys():
                if _re.search(rf"\b{_re.escape(_sname)}\b", _qn):
                    _matched_shortcuts.append(_sname)
            if len(_matched_shortcuts) > 1:
                print(f"Multiple symptoms in query {_matched_shortcuts} → skipping shortcut for full RAG response.")
                symptom_shortcut = None
    
    # Also check for "symptoms of/for [disease]" pattern - these should NOT use shortcut
    is_disease_symptom_query = any(pattern in query_lower for pattern in [
        "symptoms of", "symptoms for", "what are the symptoms", 
        "signs of", "signs and symptoms", "prevention", "dengue", "malaria"
    ])
    
    # CONVERSATION MEMORY: Check if we already discussed this symptom recently
    already_discussed = False
    if history and len(history) > 0 and symptom_shortcut:
        # Check last 5 interactions for the same symptom
        # MongoDB history structure: [{"role": "user", "content": "I have nausea"}, {"role": "assistant", "content": "..."}]
        for past_interaction in history[-5:]:
            # Only check user messages, not assistant responses
            if past_interaction.get("role") != "user":
                continue
                
            past_query = past_interaction.get("content", "").lower()
            
            # Check if any symptom from our fallback dict was mentioned
            for symptom_name in SYMPTOM_FALLBACKS.keys():
                if symptom_name in query_lower and symptom_name in past_query:
                    already_discussed = True
                    print(f"💬 CONVERSATION MEMORY: Already discussed '{symptom_name}' recently")
                    print(f"   Previous query: {past_query[:50]}...")
                    break
            if already_discussed:
                break
    
    # If it's a common symptom (not asking about disease symptoms) and we have fallback data, use shortcut
    if symptom_shortcut and not is_disease_symptom_query and user_confirmation != "yes":
        print(f"⚡ SYMPTOM SHORTCUT: Bypassing LLM for common symptom: {combined_input[:50]}...")
        
        # Use the conversation controller: update state from message then decide READY vs follow-up.
        # FAST PATH: if context bridge already merged a duration answer, we know state is complete.
        intent_enum = QueryIntent.SYMPTOM_QUERY
        if _bridge_merged:
            print("⚡ Bridge merged → skipping controller, state is READY")
            is_ready = True
            follow_up_q = None
        else:
            try:
                from clinical_memory import state_manager, session_repo, ClinicalState
                # Build conversation history strings for the controller
                recent_history_strs = [m.get("content", "") for m in history[-4:]] if history else []
                last_question_str = None
                if history:
                    for m in reversed(history):
                        if m.get("role") == "assistant" and ("how long" in m.get("content", "").lower() or "question" in m.get("content", "").lower()):
                            last_question_str = m.get("content", "")
                            break

                # Step 1: Load persisted session using user_id so state survives across turns
                # CRITICAL: using user_id as session_id keeps symptoms from the previous turn
                _session_key = str(profile.get("user_id", "")) or None
                session = session_repo.get_or_create_session(_session_key)
                prev_state = session.state  # snapshot before update

                # 🔄 SESSION RESET: if the previous conversation was complete (has symptoms+duration)
                # AND we are NOT answering a clarification question, this is a fresh conversation.
                # Reset so old symptoms don't bleed into the new session.
                _is_answering_clarification = bool(last_question_str)
                _prev_complete = bool(prev_state.symptoms and prev_state.duration)
                if _prev_complete and not _is_answering_clarification:
                    print("🔄 Session reset: new symptom conversation detected, clearing old state")
                    session.state = ClinicalState()
                    prev_state = session.state

                print(f"📋 Loaded prev state: symptoms={prev_state.symptoms}, duration={prev_state.duration}")

                orchestration_result = await state_manager.orchestrate_state(
                    prev_state,
                    combined_input,
                    last_question=last_question_str
                )

                updated_state = orchestration_result["state"]
                route = orchestration_result["route"]
                confidence = orchestration_result["confidence"]

                print(f"📋 Orchestrator output: state={updated_state.dict()}, route={route}")

                session.state = updated_state
                session_repo.save_session(session)

                is_ready = (route != "follow_up")

                if not is_ready:
                    # Decide follow up question
                    field_missing = updated_state.pending_field
                    
                    # LLM sometimes fails to set pending_field, manually infer:
                    if not field_missing:
                        if not updated_state.duration:
                            field_missing = "duration"
                            updated_state.pending_field = "duration"
                        else:
                            field_missing = "symptoms"
                            updated_state.pending_field = "symptoms"
                            
                    if field_missing == "duration":
                        follow_up_q = "How long have you been experiencing this?"
                    elif field_missing == "symptoms":
                        follow_up_q = "What symptoms are you experiencing?"
                    else:
                        follow_up_q = "Can you provide more details about how you are feeling?"
                    
                    session.last_question = follow_up_q
                    session.state = updated_state
                    session_repo.save_session(session)
                else:
                    follow_up_q = None

            except Exception as _ctrl_err:
                print(f"⚠️ Controller failed ({_ctrl_err}), falling back to rag_router")
                is_ready = not rag_router.should_ask_follow_up(combined_input, intent_enum, history)
                follow_up_q = "How long have you been experiencing this?"

        if not is_ready:
            await audit_logger.log_event(
                action="AI_QUERY",
                status="SUCCESS",
                user_id=user_id,
                request=request,
                metadata={"type": "clarification_triggered", "symptom": combined_input[:50]}
            )
            return json.dumps({
                "type": "clarification_questions",
                "context": f"I can certainly help you with information about {combined_input}. To be more specific:",
                "questions": [follow_up_q],
                "requires_confirmation": True
            })

        # If already discussed, provide follow-up response
        if already_discussed:
            await audit_logger.log_event(
                action="AI_QUERY",
                status="SUCCESS",
                user_id=user_id,
                request=request,
                metadata={"type": "symptom_shortcut", "already_discussed": True, "symptom": combined_input[:50]}
            )
            return json.dumps({
                "type": "health_report",
                "health_information": f"I see you're still experiencing this symptom. {symptom_shortcut}\n\nSince this is continuing, I recommend:\n1. Keep track of when it occurs and any triggers\n2. Note if it's getting better, worse, or staying the same\n3. Consider consulting a healthcare professional if it persists or worsens",
                "possible_conditions": ["Ongoing symptom - monitoring recommended"],
                "reasoning_brief": "Following up on previously discussed symptom with additional guidance.",
                "recommended_next_steps": "If symptoms persist or worsen, please consult a healthcare professional for personalized evaluation.",
                "ai_confidence": "High - Follow-up Guidance",
                "trusted_sources": ["Medical Knowledge Base", "MedlinePlus (NIH)"],
                "disclaimer": "This is for informational purposes and not a diagnosis. Consult a professional."
            })
        
        # First time discussing this symptom
        await audit_logger.log_event(
            action="AI_QUERY",
            status="SUCCESS",
            user_id=user_id,
            request=request,
            metadata={"type": "symptom_shortcut", "already_discussed": False, "symptom": combined_input[:50]}
        )
        return json.dumps({
            "type": "health_report",
            "health_information": symptom_shortcut,
            "possible_conditions": ["Various causes possible - not a diagnosis"],
            "reasoning_brief": "Providing general information about this common symptom.",
            "recommended_next_steps": "Monitor your symptoms. Consult a healthcare professional if symptoms persist, worsen, or are accompanied by other concerning signs.",
            "ai_confidence": "High - General Symptom Information",
            "trusted_sources": ["Medical Knowledge Base", "MedlinePlus (NIH)"],
            "disclaimer": "This is for informational purposes and not a diagnosis. Consult a professional."
        })

    # --- STEP 3: Intent Detection (RAG Router) ---
    # Use RAG router for deterministic, enterprise-grade intent detection
    if is_report_analysis:
        intent_enum = QueryIntent.TEST_OR_REPORT_QUERY
        detected_intent = "test_or_report_based"
    else:
        intent_enum = rag_router.detect_intent(combined_input, history)
        detected_intent = intent_enum.name.lower().replace('_query', '_based')  # Convert to old format for compatibility
    
    print(f"🎯 RAG Router detected intent: {intent_enum.name} -> {detected_intent}")
    
    # --- EMERGENCY INTERCEPT (Safety Layer 0) ---
    if intent_enum == QueryIntent.EMERGENCY_QUERY:
        print(f"🚨 EMERGENCY DETECTED: {combined_input[:50]}...")
        await audit_logger.log_event(
            action="AI_QUERY",
            status="SUCCESS",
            user_id=user_id,
            request=request,
            metadata={"type": "emergency_intercept", "query": combined_input[:50]}
        )
        return json.dumps({
            "type": "health_report",
            "health_information": "⚠️ **URGENT: EMERGENCY DETECTED**\n\nBased on your input, you may be experiencing a medical emergency. Please **stop using this app immediately** and take the following actions:\n\n1. **Call emergency services (e.g., 911, 112, or your local equivalent) right away.**\n2. Do not attempt to drive yourself to the hospital.\n3. If you are alone, try to alert a neighbor or someone nearby.",
            "possible_conditions": ["CRITICAL: Requires Immediate Medical Attention"],
            "reasoning_brief": "Deterministic safety layer identified keywords associated with life-threatening conditions.",
            "recommended_next_steps": "Contact emergency services immediately. Do not wait for further AI analysis.",
            "ai_confidence": "N/A - Deterministic Safety Override",
            "trusted_sources": ["Emergency Protocol"],
            "disclaimer": "This is a life-safety override. Seek professional medical help immediately."
        })

    # --- SMALL TALK INTERCEPT (Strict Medical-Only Mode) ---
    if intent_enum == QueryIntent.SMALL_TALK:
        print(f"🚫 SMALL_TALK blocked (strict mode): {combined_input[:50]}...")
        return json.dumps({"type": "chat_message", "message": HEALTH_ONLY_REDIRECT})

    # Also run LLM controller for clarification decision and STATE UPDATE
    if is_report_analysis:
        # Skip controller for report analysis - go straight to retrieval
        ctrl = {"needs_clarification": False, "detected_intent": detected_intent}
    else:
        from clinical_memory import state_manager, session_repo, ClinicalState
        
        # Load persisted session using user_id
        _session_key = str(profile.get("user_id", "")) or None
        session = session_repo.get_or_create_session(_session_key)
        prev_state = session.state

        # Find last assistant question for context
        last_question_str = None
        if history:
            for m in reversed(history):
                if m.get("role") == "assistant" and ("how long" in m.get("content", "").lower() or "question" in m.get("content", "").lower()):
                    last_question_str = m.get("content", "")
                    break

        try:
            # Sync ALL medical conditions through the Medical Orchestrator
            orchestration_result = await state_manager.orchestrate_state(
                prev_state, combined_input, last_question=last_question_str
            )
            updated_state = orchestration_result["state"]
            route = orchestration_result["route"]
            
            session.state = updated_state
            
            # Map route to the legacy ctrl object format
            needs_clarif = (route == "follow_up")
            qs = []
            if needs_clarif:
                if updated_state.pending_field == "duration":
                    qs = ["How long have you been experiencing this?"]
                else:
                    qs = ["What symptoms are you experiencing?"]
                session.last_question = qs[0]
            
            session_repo.save_session(session)
            
            ctrl = {
                "needs_clarification": needs_clarif,
                "detected_intent": detected_intent,
                "questions": qs
            }
            print(f"🎯 Final intent: {detected_intent} | State Managed: {updated_state.dict()}")
        except Exception as e:
            print(f"⚠️ Orchestrator Controller JSON Error: {e}")
            ctrl = {"needs_clarification": False, "detected_intent": detected_intent}
    
    # --- STEP 4: Clarification Loop (Follow-up) with CONVERSATION STATE CHECK ---
    # Only ask clarification if:
    # 1. This is the FIRST interaction (user_confirmation == "skip")
    # 2. We haven't already asked clarification for this query in conversation history
    
    if not is_report_analysis and user_confirmation == "skip":
        # Use RAG router's anti-loop logic for follow-up decision
        should_ask = rag_router.should_ask_follow_up(combined_input, intent_enum, history)
        
        # If router says ask AND controller agrees, then ask
        if should_ask and ctrl.get("needs_clarification") and detected_intent == "symptom_based":
            qs = ctrl.get("questions") or []
            if isinstance(qs, list) and len(qs) > 0:
                qs = [qs[0]]
            else:
                qs = ["How long have you been experiencing this?"]
            return json.dumps({
                "type": "clarification_questions",
                "context": "To provide a more accurate assessment, I have a follow-up question:",
                "questions": qs,
                "requires_confirmation": True # Trigger Yes/No/Skip UI in frontend
            })

    # --- STEP 5: Contextual Memory Selection (Memory Selector) ---
    user_id = str(profile.get("user_id", "unknown"))
    confirmed_context = "None (user denied prior occurrence or no confirmation provided)"
    
    if user_confirmation == "yes":
        relevant_memory_chunks = structured_memory.get_relevant_history(user_id, combined_input)
        raw_memory = structured_memory.summarize_memory(relevant_memory_chunks)
        
        if raw_memory and raw_memory != "No relevant past context found.":
            confirmed_context = await call_llm_with_fallback(
                messages=[
                    {"role": "system", "content": PROMPT_MEMORY_SELECTOR.format(
                        user_input=combined_input,
                        user_confirmation=user_confirmation,
                        past_data=raw_memory
                    )}
                ],
                use_primary=False # Memory selection is simple, use smaller model
            )

    # Add current multimodal context to confirmed_context for specialist prompts
    current_input_context = f"\n[CURRENT CLINICAL STATE]\n"
    
    # Safely extract state variables if they exist
    _c_symptoms = []
    _c_duration = None
    _c_severity = None
    try:
        if 'updated_state' in locals() and updated_state:
            _c_symptoms = updated_state.symptoms
            _c_duration = updated_state.duration
            _c_severity = updated_state.severity
        elif 'prev_state' in locals() and prev_state:
            _c_symptoms = prev_state.symptoms
            _c_duration = prev_state.duration
            _c_severity = prev_state.severity
    except Exception:
        pass
        
    if _c_symptoms:
        current_input_context += f"- Active Symptoms: {', '.join(_c_symptoms)}\n"
    if _c_duration:
        current_input_context += f"- Duration: {_c_duration}\n"
    if _c_severity:
        current_input_context += f"- Severity: {_c_severity}\n"
        
    current_input_context += f"\n[CURRENT INPUTS]\n"
    if user_text: current_input_context += f"- Raw Text Query: {user_text}\n"
    if voice_text: current_input_context += f"- Voice Query: {voice_text}\n"
    if image_desc: current_input_context += f"- Image Observations: {image_desc}\n"
    if report_text and not is_report_analysis: current_input_context += f"- Report Summary: {report_text[:200]}...\n"
    
    # If the user's combined_input is different from raw text (merged), explicitly state it
    if combined_input != user_text and combined_input.strip():
        current_input_context += f"- Merged Intent: {combined_input}\n"
    
    if confirmed_context == "None (user denied prior occurrence or no confirmation provided)":
        confirmed_context = current_input_context
    else:
        confirmed_context += current_input_context

    rag_data = "No specific reference data found. Use general medical knowledge for terminology."
    if rag_service.enabled:
        # Use RAG router for query augmentation and dataset routing
        search_query = rag_router.augment_query(combined_input, intent_enum)
        print(f"🔍 Augmented query: {search_query[:100]}...")
        
        # Search using confirmed context + current input
        if "Relevant memory included" in confirmed_context:
            search_query += " " + confirmed_context
            
        # Determine if we should use a specific namespace and filter
        namespace = None
        filter_dict = None
        if intent_enum == QueryIntent.TEST_OR_REPORT_QUERY:
            namespace = "lab_reference"
            extracted_key = rag_router.extract_test_key(combined_input)
            if extracted_key:
                filter_dict = {"testKey": extracted_key}
                print(f"🧪 Deterministic match: {extracted_key}. Using metadata filter.")
            else:
                print(f"🧪 No deterministic match. Using semantic search in namespace: {namespace}")

        # Retrieve with higher top_k, then filter by allowed datasets
        docs = rag_service.search(search_query, top_k=12, namespace=namespace, filter=filter_dict)
        
        # Filter results based on intent-specific dataset routing
        allowed_datasets = rag_router.get_dataset_routing(intent_enum)
        
        # SPECIAL RULE: For report analysis, use ONLY MedlinePlus/WHO/NHS
        if is_report_analysis:
            allowed_datasets = [
                DatasetType.MEDLINEPLUS,
                DatasetType.WHO_NHS
            ]
            print("🛡️ REPORT ANALYSIS: Restricting sources to MedlinePlus/WHO/NHS only")
            
        docs = rag_router.filter_results_by_dataset(docs, allowed_datasets)
        print(f"📊 Retrieved {len(docs)} results from allowed datasets: {[d.name for d in allowed_datasets]}")
        
        # Validate retrieval quality
        is_valid, reason = rag_router.validate_retrieval_quality(docs, intent_enum)
        if not is_valid:
            print(f"⚠️ Retrieval quality check failed: {reason}")
        if docs:
            rag_data = ""
            has_symptom_data = False
            for d in docs:
                # Basic cleaning to remove potential encoding artifacts
                cleaned_text = d['text'].encode('ascii', 'ignore').decode('ascii')
                source_info = f"[{d['source']}]"
                if d.get('metadata', {}).get('category') == "Primary Symptom":
                    source_info += " (PRIMARY SYMPTOM ENTRY)"
                    has_symptom_data = True
                
                rag_data += f"- {source_info} {cleaned_text} (Title: {d['title']})\n"
            
            # ENHANCED FALLBACK: If this is a symptom query but RAG didn't return symptom data, add fallback
            if detected_intent == "symptom_based" and not has_symptom_data:
                fallback = get_symptom_fallback(combined_input)
                if fallback:
                    rag_data = f"[FALLBACK SYMPTOM DATA - Primary Source]\n{fallback}\n\n[Additional Context from Medical Database]\n{rag_data}"
                    print(f"✅ Supplementing RAG data with symptom fallback for: {combined_input[:50]}...")
        else:
            # CRITICAL FALLBACK: Check for symptom fallback before failing
            fallback = get_symptom_fallback(combined_input)
            if fallback:
                rag_data = f"[FALLBACK SYMPTOM DATA] {fallback}"
                print(f"✅ Using symptom fallback for query: {combined_input[:50]}...")

    # --- STEP 8: RETRIEVAL QUALITY CHECK ---
    # Before calling expensive LLM, check if we have sufficient context
    # If it's a symptom query and we have no data, use fallback directly
    has_sufficient_context = True
    
    if detected_intent == "symptom_based":
        # For symptom queries, we need either RAG data or fallback
        if rag_data == "No verified medical information found for this specific query.":
            # No RAG data - check if we have fallback
            fallback = get_symptom_fallback(combined_input)
            if fallback:
                # Use fallback directly without LLM call (saves API cost)
                print(f"⚡ QUALITY CHECK: Using fallback directly, skipping LLM for: {combined_input[:50]}...")
                return json.dumps({
                    "type": "health_report",
                    "health_information": fallback,
                    "possible_conditions": ["Various causes possible - not a diagnosis"],
                    "reasoning_brief": "Providing general information about this symptom based on medical knowledge.",
                    "recommended_next_steps": "Monitor your symptoms. Consult a healthcare professional if symptoms persist, worsen, or are accompanied by other concerning signs.",
                    "ai_confidence": "High - General Symptom Information",
                    "trusted_sources": ["Medical Knowledge Base", "MedlinePlus (NIH)"],
                    "disclaimer": "This is for informational purposes and not a diagnosis. Consult a professional."
                })
            else:
                has_sufficient_context = False

    # --- STEP 7: Medical Report Generation (Medical RAG) ---
    image_text = inputs.get("image_text", "") or ""
    
    try:
        if is_report_analysis and is_image_analysis:
            print("🧬 Using MULTIMODAL Analysis Mode")
            prompt_content = PROMPT_REPORT_ANALYZER.format(
                report_text=f"{report_text}\n\n[IMAGE OBSERVATIONS]\n{image_desc}\n\n[IMAGE TEXT (OCR)]\n{image_text}",
                user_context=confirmed_context,
                rag_data=rag_data
            )
        elif is_report_analysis:
            print("📝 Using PROMPT_REPORT_ANALYZER")
            prompt_content = PROMPT_REPORT_ANALYZER.format(
                report_text=report_text,
                user_context=confirmed_context,
                rag_data=rag_data
            )
        elif is_image_analysis:
            print(f"🖼️ Routing Image Analysis: {image_desc[:100]}...")
            
            # 1. Modality Detection (Layer 1)
            modality_response = await call_llm_with_fallback(
                messages=[{"role": "system", "content": PROMPT_MODALITY_DETECTOR.format(image_caption=image_desc)}],
                response_format={"type": "json_object"}
            )
            
            try:
                modality_data = json.loads(modality_response)
                modality = modality_data.get("modality", "unknown")
                modality_confidence = modality_data.get("confidence", 0.0)
                print(f"🔍 Detected Modality: {modality} (Confidence: {modality_confidence})")
            except:
                modality = "unknown"
                modality_confidence = 0.0
                print("⚠️ Failed to parse modality response, defaulting to unknown")

            # 2. Model Router (Layer 2) & Confidence Gate (Layer 4)
            CONFIDENCE_THRESHOLD = 0.6
            escalation_reason = None
            
            if modality == "unknown":
                escalation_reason = "Unsupported or ambiguous image modality."
            elif modality_confidence < CONFIDENCE_THRESHOLD:
                escalation_reason = f"Low confidence in modality detection ({modality_confidence})."
            
            if escalation_reason:
                # HITL Escalation (Layer 5)
                print(f"🚨 HITL Escalation Triggered: {escalation_reason}")
                prompt_content = PROMPT_HITL_ESCALATION.format(escalation_reason=escalation_reason)
            else:
                # Route to Expert Model (Layer 3)
                if modality == "radiology":
                    print("🩻 Using PROMPT_RADIOLOGY_SPECIALIST")
                    prompt_content = PROMPT_RADIOLOGY_SPECIALIST.format(
                        image_caption=image_desc,
                        image_text=image_text,
                        user_context=confirmed_context,
                        rag_data=rag_data
                    )
                elif modality == "dermatology":
                    print("🧴 Using PROMPT_SKIN_SPECIALIST")
                    prompt_content = PROMPT_SKIN_SPECIALIST.format(
                        image_caption=image_desc,
                        image_text=image_text,
                        user_context=confirmed_context,
                        rag_data=rag_data
                    )
                elif modality == "ophthalmology":
                    print("👁️ Using PROMPT_EYE_SPECIALIST")
                    prompt_content = PROMPT_EYE_SPECIALIST.format(
                        image_caption=image_desc,
                        image_text=image_text,
                        user_context=confirmed_context,
                        rag_data=rag_data
                    )
                elif modality == "medical_document":
                    print("📄 Routing to Report Analysis Prompt (Image OCR)")
                    # Use OCR text if available, otherwise fallback to caption
                    doc_content = image_text if image_text else image_desc
                    prompt_content = PROMPT_REPORT_ANALYZER.format(
                        report_text=doc_content,
                        user_context=confirmed_context,
                        rag_data=rag_data
                    )
                else:
                    print("🚨 Fallback to HITL for unhandled modality")
                    prompt_content = PROMPT_HITL_ESCALATION.format(escalation_reason="Unhandled modality type.")

            # Audit Log Modality (Layer 6)
            await audit_logger.log_event(
                action="IMAGE_MODALITY_DETECTION",
                status="SUCCESS",
                user_id=user_id,
                request=request,
                metadata={
                    "detected_modality": modality,
                    "confidence": modality_confidence,
                    "escalated": bool(escalation_reason)
                }
            )
        else:
            print("🏥 Using PROMPT_MEDICAL_RAG")
            prompt_content = PROMPT_MEDICAL_RAG.format(
                user_query=combined_input,
                user_context=confirmed_context,
                rag_data=rag_data
            )
            
        final_response_content = await call_llm_with_fallback(
            messages=[
                {"role": "system", "content": prompt_content}
            ],
            response_format={"type": "json_object"},
            use_primary=True # Use big model for final analysis, fallback if needed
        )

        # DEBUG: Log final LLM response structure
        try:
            debug_parsed = json.loads(final_response_content)
            print(f"DEBUG: LLM Response Keys: {list(debug_parsed.keys())}")
            if is_report_analysis and "summary" not in debug_parsed:
                print("⚠️ WARNING: Report analysis missing 'summary' field!")
        except Exception as debug_e:
            print(f"DEBUG: Failed to parse LLM response for debug logging: {debug_e}")

        # --- STEP 8: Feedback Refinement (Handled by feedback_router.py) ---
        await audit_logger.log_event(
            action="AI_QUERY",
            status="SUCCESS",
            user_id=user_id,
            request=request,
            metadata={
                "model": LLM_MODEL,
                "intent": detected_intent,
                "is_report_analysis": is_report_analysis,
                "is_image_analysis": is_image_analysis,
                "has_voice": bool(voice_text),
                "has_image": bool(image_desc),
                "has_report": bool(report_text),
                "image_modality": modality if is_image_analysis else None,
                "is_escalated": bool(escalation_reason) if is_image_analysis else False
            }
        )
        return final_response_content
    except Exception as e:
        print(f"❌ Final RAG Error: {e}")
        await audit_logger.log_event(
            action="AI_QUERY",
            status="FAILURE",
            user_id=user_id,
            request=request,
            metadata={"error": str(e), "model": LLM_MODEL}
        )
        print(f"❌ Error type: {type(e).__name__}")
        print(f"❌ Query was: {combined_input[:100]}")
        import traceback
        traceback.print_exc()
        
        # LAST RESORT FALLBACK: Try symptom fallback even if LLM fails
        fallback = get_symptom_fallback(combined_input)
        if fallback:
            return json.dumps({
                "type": "health_report",
                "health_information": fallback,
                "possible_conditions": ["Various causes possible"],
                "reasoning_brief": "Using general symptom information due to system limitations.",
                "recommended_next_steps": "Consult a healthcare professional for personalized advice.",
                "ai_confidence": "Medium - General Information",
                "trusted_sources": ["Medical Knowledge Base"],
                "disclaimer": "This is for informational purposes and not a diagnosis. Consult a professional."
            })
        
        return json.dumps({
            "type": "health_report",
            "health_information": "I encountered an error while processing your request. Please try again or consult a professional.",
            "ai_confidence": "Low - System Error",
            "disclaimer": "This is not a diagnosis. Consult a professional."
        })

