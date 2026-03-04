import re
import json
import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# We need to import the LLM service to use the new prompt
from app.services.llm_service import call_llm_with_fallback

try:
    import redis
except ImportError:
    redis = None

try:
    from pymongo import MongoClient
except ImportError:
    MongoClient = None

# --- Configuration ---
REDIS_HOST = "localhost"
REDIS_PORT = 6379
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "health_assistant"

class ClinicalState(BaseModel):
    symptoms: List[str] = Field(default_factory=list)
    duration: Optional[str] = None
    severity: Optional[str] = None
    pending_field: Optional[str] = None

class Session(BaseModel):
    session_id: str
    state: ClinicalState = Field(default_factory=ClinicalState)
    history: List[str] = Field(default_factory=list)
    last_question: Optional[str] = None # Added to track the last question asked

class StateManager:
    def extract_state(self, message: str) -> ClinicalState:
        """
        Extracts symptoms, duration, and severity from the user message using regex/NER.
        (Legacy method, kept for fallback/simple cases)
        """
        message_lower = message.lower()
        
        # Pre-normalize common variants before matching
        variants = {
            "head ache": "headache",
            "head-ache": "headache",
            "blurry vision": "blurred vision",
            "blur vision": "blurred vision",
            "vomtings": "vomiting"
        }
        for k, v in variants.items():
            message_lower = message_lower.replace(k, v)
        
        # 1. Extract Symptoms (Simplified List - In production, use a comprehensive NER model)
        common_symptoms = [
            "fever", "cough", "headache", "cold", "runny nose", "sore throat", 
            "fatigue", "tiredness", "chest pain", "difficulty breathing", 
            "shortness of breath", "confusion", "blurred vision", "dizziness",
            "nausea", "vomiting", "diarrhea", "stomach pain", "abdominal pain",
            "rash", "itching", "swelling", "joint pain", "muscle ache", "chills"
        ]
        
        # Pre-normalize verb phrases: "getting fever" / "having vomiting" / "experiencing headache"
        # so the bare symptom word is present for regex matching
        message_lower = re.sub(
            r'\b(getting|having|experiencing|suffering from|got|feeling)\s+',
            '',
            message_lower
        )

        found_symptoms = []
        for symptom in common_symptoms:
            if re.search(rf'\b{re.escape(symptom)}\b', message_lower):
                found_symptoms.append(symptom)
                
        # Catch unlisted general symptoms like "leg pain", "tooth ache", etc.
        body_pain_matches = re.finditer(r'\b(\w+)\s+(pain|ache|soreness)\b', message_lower)
        for match in body_pain_matches:
            symptom_phrase = match.group(0)
            if symptom_phrase not in found_symptoms:
                found_symptoms.append(symptom_phrase)
        
        # 2. Extract Duration
        duration_match = re.search(r'(\d+\s+(day|week|month|hour)s?|since\s+\w+|for\s+\d+\s+(day|week|month|hour)s?)', message_lower)
        duration = duration_match.group(0) if duration_match else None
        
        # 3. Extract Severity (Simple keyword matching)
        severity = None
        if "severe" in message_lower or "extreme" in message_lower or "worst" in message_lower:
            severity = "high"
        elif "moderate" in message_lower:
            severity = "moderate"
        elif "mild" in message_lower or "slight" in message_lower:
            severity = "low"
            
        return ClinicalState(symptoms=found_symptoms, duration=duration, severity=severity)

    def update_state(self, prev_state: ClinicalState, extracted_state: ClinicalState) -> ClinicalState:
        """
        Merges the previous state with the newly extracted state.
        (Legacy method, kept for fallback)
        """
        new_symptoms = list(set(prev_state.symptoms + extracted_state.symptoms))
        new_duration = extracted_state.duration if extracted_state.duration else prev_state.duration
        new_severity = extracted_state.severity if extracted_state.severity else prev_state.severity
        return ClinicalState(symptoms=new_symptoms, duration=new_duration, severity=new_severity)

    def _is_valid_duration(self, d: str) -> bool:
        """
        Returns True only if a string looks like a real duration
        (e.g. '3 days', 'since yesterday', '2 weeks').
        Rejects words like 'getting', 'having', 'experiencing' that the LLM
        sometimes mistakenly places in the duration field.
        """
        if not d:
            return False
        d_lower = d.strip().lower()
        return bool(re.search(
            r'(\d+\s*(day|days|week|weeks|month|months|hour|hours|year|years)'
            r'|since\s+\w+|yesterday|last\s+\w+|a\s+few\s+days|this\s+(morning|evening|week))',
            d_lower
        ))

    async def contextual_update(self, current_state: ClinicalState, message: str, last_question: str = None, recent_history: Optional[List[str]] = None) -> ClinicalState:
        """
        Updates the state using an LLM to understand context, handling answers to questions
        and new symptoms simultaneously.
        """
        
        state_json = current_state.json()
        last_q_str = last_question if last_question else "None"
        history_str = "\n".join(recent_history[-3:]) if recent_history else "None"
        
        prompt = f"""
You are a deterministic clinical state updater inside an AI Health Assistant.

Your job is to update the structured clinical state using the previous state, the last question asked, and the current user message.

You MUST interpret short answers correctly.

---

INPUTS

PREVIOUS_STATE:
{state_json}

LAST_QUESTION:
{last_q_str}

RECENT_HISTORY (last 3–4 messages):
{history_str}

CURRENT_MESSAGE:
"{message}"

---

CRITICAL RULES

RULE 1 — FOLLOW-UP ANSWERS
If a specific field was requested (like duration), the user message MUST be interpreted as the answer to that field.
Example: Last question asked about duration, user says "5 days" -> duration = "5 days".

RULE 2 — SHORT NUMERIC ANSWERS
If the message contains numbers or time expressions (days, weeks, months, hours) and symptoms already exist, the message MUST be interpreted as the duration.

RULE 3 — NEVER REMOVE EXISTING SYMPTOMS
Existing symptoms are the source of truth. Final symptoms must be the UNION of previous and newly extracted symptoms.

RULE 4 — MERGE CONTEXT
If symptoms already exist and duration is provided later, merge them.

RULE 5 — WHEN STATE IS COMPLETE
If BOTH at least one symptom AND a duration are present, the state is READY.

RULE 6 — NEVER OUTPUT EXPLANATIONS
Return STRICT JSON only.

---

OUTPUT FORMAT (STRICT JSON ONLY):

{{
  "symptoms": [...],
  "duration": "...",
  "severity": null
}}
"""
        try:
            response_text = await call_llm_with_fallback(
                messages=[{"role": "system", "content": prompt}],
                use_primary=False # Use fallback model (smaller/faster) for state updates to reduce latency
            )
            
            # Clean and parse JSON
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            # Find the first { and last }
            start = clean_text.find("{")
            end = clean_text.rfind("}") + 1
            if start != -1 and end != -1:
                clean_text = clean_text[start:end]
                
            data = json.loads(clean_text)
            
            # Union LLM-detected symptoms with regex-detected to avoid misses
            # Also normalize common variants to canonical forms
            # 1) Gather LLM symptoms
            llm_symptoms = data.get("symptoms", []) if isinstance(data, dict) else []
            # 2) Fallback regex extraction on the raw message
            regex_state = self.extract_state(message)
            combined = set(s.lower() for s in llm_symptoms) | set(s.lower() for s in regex_state.symptoms)
            # 3) Normalize variants
            normalized = []
            for s in combined:
                if s in ["head ache", "head-ache"]:
                    normalized.append("headache")
                elif s in ["blurry vision", "blur vision"]:
                    normalized.append("blurred vision")
                else:
                    normalized.append(s)
            # 4) Build final state using previous state union rule
            final_symptoms = list({*{sym.lower() for sym in current_state.symptoms}, *set(normalized)})

            # Validate LLM-extracted duration: reject garbage like 'getting', 'having', 'experiencing'
            llm_duration = data.get("duration")
            validated_duration = (
                llm_duration
                if llm_duration and self._is_valid_duration(llm_duration)
                else None
            )
            final_duration = validated_duration or regex_state.duration or current_state.duration
            final_severity = data.get("severity") or regex_state.severity or current_state.severity
            print(f"   [contextual_update] llm_dur={llm_duration!r} validated={validated_duration!r} final={final_duration!r}")
            return ClinicalState(symptoms=final_symptoms, duration=final_duration, severity=final_severity)
            
        except Exception as e:
            print(f"⚠️ LLM State Update Failed: {e}. Fallback to regex.")
            # Fallback to regex extraction + simple merge
            extracted = self.extract_state(message)
            return self.update_state(current_state, extracted)

    async def orchestrate_state(self, current_state: ClinicalState, message: str, last_question: str = None) -> dict:
        """
        Clinical State Normalization Engine.
        Extracts and normalizes structured medical state from the user message.
        Uses Python-level routing enforcement for deterministic route decisions.
        Returns a dict: {state: ClinicalState, route: str, confidence: float}
        """
        state_dict = {
            "symptoms": current_state.symptoms,
            "duration": current_state.duration,
            "severity": current_state.severity,
            "pending_field": current_state.pending_field
        }
        
        prompt = f"""You are the Clinical State Normalization Engine inside a production Medical AI Assistant.

You are NOT a chatbot.

Your job is ONLY to extract and normalize structured medical information from the user message.

You MUST output STRICT JSON.

Never generate explanations, diagnoses, or extra text.

---

## INPUT

PREVIOUS_STATE:
{json.dumps(state_dict)}

USER_MESSAGE:
"{message}"

---

## TARGET STRUCTURE

{{
  "updated_state": {{
    "symptoms": [],
    "duration": null,
    "severity": null,
    "pending_field": null
  }}
}}

---

## CRITICAL RULES

1. NEVER remove previously detected symptoms.

Existing symptoms in PREVIOUS_STATE are the source of truth.

New symptoms must be merged with existing ones.

---

2. SYMPTOMS MUST BE CANONICAL MEDICAL TERMS.

Symptoms must always be single medical terms.

VALID examples:
"fever"
"headache"
"back pain"
"vomiting"
"dizziness"
"nausea"

INVALID examples:
"getting fever"
"having headache"
"headache for 5 days"
"fever and headache"
"pain in my back for 5 days"

If the user message contains phrases like:

"getting fever"
"having headache"
"feeling nausea"
"suffering from dizziness"

You MUST normalize them to:

"fever"
"headache"
"nausea"
"dizziness"

---

3. REMOVE ACTION WORDS.

Ignore verbs such as:

getting
having
feeling
experiencing
suffering from
started having

Example:

User message:
"getting headache"

Output symptom:
"headache"

---

4. MULTIPLE SYMPTOMS

If multiple symptoms are mentioned:

Example:

"I have fever and headache"

Output:

"symptoms": ["fever","headache"]

Never output them as one phrase.

---

5. DURATION EXTRACTION

Extract duration ONLY if the message contains a valid time expression.

VALID examples:

"5 days"
"2 weeks"
"3 months"
"since yesterday"
"for 4 hours"

INVALID examples:

"getting"
"recently"
"for some time"

If no valid duration is detected, set duration = null.

---

6. FOLLOW-UP ANSWERS

If PREVIOUS_STATE contains:

pending_field = "duration"

Then interpret the user message as a duration answer if it contains a time expression.

Example:

PREVIOUS_STATE:
{{"symptoms": ["fever"], "duration": null, "pending_field": "duration"}}

USER_MESSAGE:
"5 days"

OUTPUT:

{{
  "updated_state": {{
    "symptoms": ["fever"],
    "duration": "5 days",
    "severity": null,
    "pending_field": null
  }}
}}

---

7. SEVERITY EXTRACTION

Extract severity if words like:

mild
moderate
severe
intense
extreme

Map them to:

low
moderate
high

Example:

"severe headache"

severity = "high"

---

8. NEVER DROP VALID DATA

If PREVIOUS_STATE already contains:

symptoms = ["fever"]

and user says:

"5 days"

Do NOT modify symptoms.

---

9. REMOVE DUPLICATES

Never produce duplicate symptoms.

Example:

["fever","fever"] → ["fever"]

---

10. NO INVENTION

Do NOT invent symptoms.

Only extract symptoms explicitly present in USER_MESSAGE.

---

OUTPUT FORMAT

Return ONLY JSON.

{{
  "updated_state": {{
    "symptoms": [],
    "duration": null,
    "severity": null,
    "pending_field": null
  }}
}}
"""
        try:
            response_text = await call_llm_with_fallback(
                messages=[{"role": "system", "content": prompt}],
                use_primary=False
            )
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            start = clean_text.find("{")
            end = clean_text.rfind("}") + 1
            if start != -1 and end != -1:
                clean_text = clean_text[start:end]
            
            data = json.loads(clean_text)
            state_data = data.get("updated_state", {})
            
            # Regex fallback union to ensure no symptoms are missed by the LLM
            regex_state = self.extract_state(message)
            llm_symptoms = state_data.get("symptoms", [])
            
            combined_symptoms = list({
                *[s.lower() for s in current_state.symptoms],
                *[s.lower() for s in llm_symptoms], 
                *[s.lower() for s in regex_state.symptoms]
            })
            
            final_duration = state_data.get("duration") or regex_state.duration or current_state.duration
            final_severity = state_data.get("severity") or regex_state.severity or current_state.severity
            
            final_route = data.get("route", "rag")
            
            # Python-level Routing Enforcement rules bypassing LLM unreliability:
            missing_symptoms = not bool(combined_symptoms)
            missing_duration = not bool(final_duration)
            
            # Rule 1: Always enforce correct pending_field if there are missing critical fields
            if missing_symptoms or missing_duration:
                final_route = "follow_up"
                state_data["pending_field"] = "symptoms" if missing_symptoms else "duration"
                
            # Rule 2: If the LLM requested a follow-up, but our regex union rescued the missing fields
            elif final_route == "follow_up" and not missing_symptoms and not missing_duration:
                final_route = "rag" # Rescued! Proceed safely.
                state_data["pending_field"] = None

            return {
                "state": ClinicalState(
                    symptoms=combined_symptoms,
                    duration=final_duration,
                    severity=final_severity,
                    pending_field=state_data.get("pending_field")
                ),
                "route": final_route,
                "confidence": 0.9  # Fixed: routing is determined by Python rules, not LLM
            }
        except Exception as e:
            print(f"⚠️ Orchestrator Failed: {e}")
            regex_state = self.extract_state(message)
            combined_symptoms = list({*[s.lower() for s in current_state.symptoms], *[s.lower() for s in regex_state.symptoms]})
            return {
                "state": ClinicalState(
                    symptoms=combined_symptoms,
                    duration=regex_state.duration or current_state.duration,
                    severity=regex_state.severity or current_state.severity,
                    pending_field=current_state.pending_field
                ),
                "route": "follow_up" if not combined_symptoms or not (regex_state.duration or current_state.duration) else "llm",
                "confidence": 0.5
            }

    async def decide_next_action(
        self,
        current_state: ClinicalState,
        message: str,
        last_question: Optional[str] = None,
        recent_history: Optional[List[str]] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Conversation controller: decides whether the current state is complete
        enough to proceed to diagnosis (READY) or whether we need to ask a
        targeted follow-up question.

        Returns:
            (True, None)               → state is READY, proceed to diagnosis
            (False, "follow-up text")  → state is incomplete, ask the question
        """
        # --- Fast deterministic path (avoids LLM call if obvious) ---
        has_symptoms = bool(current_state.symptoms)
        has_duration = bool(current_state.duration)
        if has_symptoms and has_duration:
            print("✅ Controller (deterministic): State READY")
            return True, None

        # --- LLM path for nuanced judgment ---
        state_json = current_state.json()
        last_q_str = last_question if last_question else "None"
        history_str = "\n".join(recent_history[-4:]) if recent_history else "None"

        prompt = f"""
You are a medical conversation controller. Respond with ONE line only.

CURRENT STATE (JSON):
{state_json}

LAST QUESTION ASKED:
{last_q_str}

CURRENT MESSAGE:
"{message}"

RULES:
- If state has at least 1 symptom AND a duration → output exactly: READY
- If duration is missing → ask only about duration in one short sentence
- If symptoms are missing → ask only about symptoms in one short sentence
- NEVER output explanations, reasoning, or multiple sentences
- NEVER say "unclear"

OUTPUT FORMAT EXAMPLES:
  State has headache + 3 days      → READY
  State has headache, no duration  → How long have you been experiencing this?
  State is empty                   → What symptoms are you experiencing?

YOUR RESPONSE (one line only, no punctuation after the question mark):"""

        def _extract_clean_question(raw: str) -> str:
            """
            Pull the last question sentence from LLM output.
            Strips any prefixed reasoning/context the model may have leaked.
            """
            import re
            raw = raw.strip()
            # If "READY" appears anywhere treat as READY signal
            if raw.upper().startswith("READY"):
                return "READY"
            # Find sentences ending with '?'
            sentences = re.split(r'(?<=[.!?])\s+', raw)
            for s in reversed(sentences):
                s = s.strip()
                if s.endswith("?"):
                    # Remove leading labels like "ASK:", "Question:", etc.
                    s = re.sub(r'^(ASK|QUESTION|Q)\s*:\s*', '', s, flags=re.IGNORECASE)
                    return s
            # Fallback: return last non-empty line
            lines = [l.strip() for l in raw.splitlines() if l.strip()]
            return lines[-1] if lines else raw

        try:
            response_text = await call_llm_with_fallback(
                messages=[{"role": "system", "content": prompt}],
                use_primary=False  # Fast fallback model for controller decisions
            )
            raw_answer = response_text.strip()
            print(f"🧠 Controller LLM raw: {raw_answer[:120]}")

            if raw_answer.upper().startswith("READY"):
                return True, None

            # Post-process: extract just the clean question
            clean_q = _extract_clean_question(raw_answer)
            if clean_q.upper() == "READY":
                return True, None

            print(f"🧠 Controller clean question: {clean_q}")
            return False, clean_q

        except Exception as e:
            print(f"⚠️ Controller LLM failed: {e}. Using deterministic fallback.")
            # Fallback: ask for the first missing field
            if not has_symptoms:
                return False, "What symptoms are you experiencing?"
            if not has_duration:
                return False, "How long have you been experiencing this?"
            return True, None  # Both present → READY



class SessionRepository:
    def __init__(self):
        self.redis_client = None
        self.mongo_collection = None
        
        # Initialize Redis
        if redis:
            try:
                self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
                self.redis_client.ping() # Check connection
            except Exception as e:
                print(f"⚠️ Redis connection failed: {e}")
                self.redis_client = None
        
        # Initialize MongoDB
        if MongoClient:
            try:
                self.mongo_client = MongoClient(MONGO_URI)
                self.mongo_db = self.mongo_client[DB_NAME]
                self.mongo_collection = self.mongo_db["sessions"]
            except Exception as e:
                print(f"⚠️ MongoDB connection failed: {e}")
                self.mongo_collection = None

    def get_or_create_session(self, session_id: Optional[str] = None) -> Session:
        if not session_id:
            session_id = str(uuid.uuid4())
            return Session(session_id=session_id)

        # 1. Try Redis first
        if self.redis_client:
            try:
                cached_session = self.redis_client.get(f"session:{session_id}")
                if cached_session:
                    return Session.parse_raw(cached_session)
            except Exception as e:
                print(f"⚠️ Redis read error: {e}")

        # 2. Fallback to MongoDB
        if self.mongo_collection is not None:
            try:
                mongo_session = self.mongo_collection.find_one({"session_id": session_id})
                if mongo_session:
                    # Convert _id to string or remove it if needed, usually Pydantic handles extras if configured
                    if "_id" in mongo_session:
                        del mongo_session["_id"]
                    return Session.parse_obj(mongo_session)
            except Exception as e:
                print(f"⚠️ MongoDB read error: {e}")

        # 3. Create new if not found
        return Session(session_id=session_id)

    def save_session(self, session: Session):
        session_json = session.json()
        session_dict = session.dict()
        
        # 1. Save to Redis with TTL (e.g., 1 hour)
        if self.redis_client:
            try:
                self.redis_client.set(f"session:{session.session_id}", session_json, ex=3600)
            except Exception as e:
                print(f"⚠️ Redis write error: {e}")
        
        # 2. Save to MongoDB (Persistent)
        if self.mongo_collection is not None:
            try:
                self.mongo_collection.update_one(
                    {"session_id": session.session_id}, 
                    {"$set": session_dict}, 
                    upsert=True
                )
            except Exception as e:
                print(f"⚠️ MongoDB write error: {e}")

# Singleton instances
state_manager = StateManager()
session_repo = SessionRepository()
