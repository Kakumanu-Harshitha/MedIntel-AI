import asyncio
import json
import os
import hashlib
from typing import Dict, Any, List, Optional
from enum import Enum

from clinical_memory import state_manager, session_repo, ClinicalState, Session
from clinical_validator import clinical_validator
from adaptive_router import adaptive_router, ExecutionEngine
from cache import AsyncCache
from llm_service import call_llm_with_fallback
import speech_service

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

class UnifiedPipeline:
    def __init__(self):
        self.state_manager = state_manager
        self.session_repo = session_repo
        self.validator = clinical_validator
        self.router = adaptive_router
        try:
            self.cache = AsyncCache(redis_url=REDIS_URL)
        except Exception as e:
            print(f"Cache initialization failed: {e}")
            self.cache = None

    async def process_request(self, message: str, session_id: Optional[str] = None):
        """
        Main pipeline execution flow.
        """
        # 1. Session Loading
        session = self.session_repo.get_or_create_session(session_id)

        # 2. State Extraction and Update (LLM Contextual Update)
        # Use LLM for state update to handle "answers to previous questions"
        updated_state = await self.state_manager.contextual_update(
            session.state,
            message,
            session.last_question,
            session.history[-3:]
        )
        
        # Update session with new state and history
        session.state = updated_state
        session.history.append(message)
        
        # --- HARD SAFETY OVERRIDE (CRITICAL) ---
        # Checks for specific red flags before any further processing
        override_response = self._safety_override(updated_state)
        if override_response:
            # If safety override triggers, return immediately
            # We treat this similarly to EMERGENCY route but with specific message
            session.last_question = None
            self.session_repo.save_session(session)
            return override_response
        
        # 3. Safety Layer
        safety_flag = self.validator.safety_check(updated_state)

        # 4. Readiness Check
        is_ready = self.validator.is_ready(updated_state)

        # 5. Clinical Matching and Confidence Scoring
        matches = self.validator.match_conditions(updated_state.symptoms)
        confidence = self.validator.compute_confidence(matches)

        # 6. Adaptive Routing
        route = self.router.route(updated_state, confidence, is_ready, safety_flag)

        # 7. Cache Check
        # Only cache for Rule-based, RAG, LLM. Skip for Emergency/Follow-up
        cached_response = None
        cache_key = None
        
        if self.cache and route not in [ExecutionEngine.FOLLOW_UP, ExecutionEngine.EMERGENCY]:
            try:
                cache_key = self.cache.get_cache_key(updated_state, route)
                cached_data = await self.cache.get(cache_key)
                if cached_data:
                    cached_response = json.loads(cached_data)
            except Exception as e:
                print(f"Cache read failed: {e}")

        if cached_response:
            return cached_response

        # 8. Execute Engine
        response_data = {}
        
        if route == ExecutionEngine.EMERGENCY:
            response_data = self._generate_emergency_response(updated_state)
            session.last_question = None
        elif route == ExecutionEngine.FOLLOW_UP:
            response_data = await self._generate_llm_follow_up(updated_state)
            session.last_question = response_data.get("last_question") or response_data.get("advice")
        elif route == ExecutionEngine.RULE_BASED:
            response_data = self._execute_rule_based(updated_state, matches)
            session.last_question = None
        elif route == ExecutionEngine.RAG or route == ExecutionEngine.LLM:
            response_data = await self._execute_llm(updated_state, matches, route)
            session.last_question = None

        # 9. Response Validation (Anti-Overdiagnosis)
        # We need to extract the conditions from the response_data to validate
        possible_conditions = [c["name"] for c in response_data.get("possible_conditions", [])]
        
        if route in [ExecutionEngine.RULE_BASED, ExecutionEngine.RAG, ExecutionEngine.LLM]:
            if not self.validator.validate_response(updated_state, possible_conditions):
                # Fallback to follow-up or a safe response if validation fails
                response_data = await self._generate_llm_follow_up(updated_state)
                response_data["advice"] = "Symptoms are insufficient for a clear assessment. Please consult a doctor."
                session.last_question = response_data["advice"]

        # 10. Generate Audio (TTS)
        try:
            text_to_speak = response_data.get("advice", "") or response_data.get("reason", "")
            if text_to_speak:
                filename = speech_service.text_to_speech(text_to_speak)
                if filename:
                    response_data["audio_url"] = f"/static/audio/{filename}"
        except Exception as e:
            print(f"TTS generation failed: {e}")

        # 11. Cache Store
        if self.cache and cache_key and route not in [ExecutionEngine.FOLLOW_UP, ExecutionEngine.EMERGENCY]:
            try:
                await self.cache.set(cache_key, json.dumps(response_data))
            except Exception as e:
                print(f"Cache write failed: {e}")

        # Save session (including last_question and updated state)
        self.session_repo.save_session(session)

        return response_data

    def _safety_override(self, state: ClinicalState) -> Optional[Dict[str, Any]]:
        """
        Hard safety check that bypasses LLM and RAG if critical symptoms are found.
        """
        RED_FLAGS = {
            "blurred vision", 
            "confusion", 
            "chest pain", 
            "difficulty breathing", 
            "severe headache"
        }
        
        # Normalize state symptoms for checking
        current_symptoms = {s.lower() for s in state.symptoms}
        
        # Check if any red flag is in current symptoms (partial match allowed)
        # e.g., "severe chest pain" matches "chest pain"
        found_red_flags = []
        for flag in RED_FLAGS:
            for s in current_symptoms:
                if flag in s:
                    found_red_flags.append(s)
                    
        if found_red_flags:
            return {
                "risk_level": "HIGH",
                "symptoms": state.symptoms,
                "duration": state.duration,
                "possible_conditions": [],
                "reason": f"Critical symptoms detected: {', '.join(found_red_flags)}. Combined symptoms considered: {', '.join(state.symptoms)}.",
                "advice": "This may require urgent medical attention. Please seek immediate care.",
                "when_to_see_doctor": "IMMEDIATELY",
                "disclaimer": "This is informational only and not a medical diagnosis."
            }
        return None

    def _generate_emergency_response(self, state: ClinicalState) -> Dict[str, Any]:
        return {
            "risk_level": "HIGH",
            "symptoms": state.symptoms,
            "duration": state.duration,
            "possible_conditions": [],
            "reason": f"Red flag symptoms detected. Combined symptoms considered: {', '.join(state.symptoms)}.",
            "advice": "Please seek immediate medical attention. Call emergency services.",
            "when_to_see_doctor": "IMMEDIATELY",
            "disclaimer": "This is informational only and not a medical diagnosis."
        }

    async def _generate_llm_follow_up(self, state: ClinicalState) -> Dict[str, Any]:
        question = None
        qtype = None
        if not state.duration:
            question = "How long have you been experiencing these symptoms?"
            qtype = "DURATION"
        elif len(state.symptoms) < 2:
            question = "Do you have any other symptoms?"
            qtype = "SYMPTOMS"
        else:
            question = "READY"
            qtype = None

        return {
            "risk_level": "LOW",
            "symptoms": state.symptoms,
            "duration": state.duration,
            "possible_conditions": [],
            "reason": "Insufficient information.",
            "advice": question,
            "last_question": qtype,
            "when_to_see_doctor": "If symptoms worsen.",
            "disclaimer": "This is informational only and not a medical diagnosis."
        }

    def _generate_follow_up_response(self, state: ClinicalState) -> Dict[str, Any]:
        question = "How long have you been experiencing these symptoms?" if not state.duration else (
            "Do you have any other symptoms?" if len(state.symptoms) < 2 else "READY"
        )
        qtype = "DURATION" if not state.duration else ("SYMPTOMS" if len(state.symptoms) < 2 else None)
        
        return {
            "risk_level": "LOW",
            "symptoms": state.symptoms,
            "duration": state.duration,
            "possible_conditions": [],
            "reason": "Insufficient information for assessment.",
            "advice": question,
            "last_question": qtype,
            "when_to_see_doctor": "If symptoms worsen.",
            "disclaimer": "This is informational only and not a medical diagnosis."
        }

    def _execute_rule_based(self, state: ClinicalState, matches: List[tuple]) -> Dict[str, Any]:
        # Top 3 matches
        top_matches = matches[:3]
        conditions = [{"name": m[0], "confidence": round(m[1], 2)} for m in top_matches]
        
        risk = "LOW"
        if any(c["confidence"] > 0.8 for c in conditions):
            risk = "MODERATE"
        # Rule based doesn't usually output HIGH unless red flags (handled by safety check)
            
        return {
            "risk_level": risk,
            "symptoms": state.symptoms,
            "duration": state.duration,
            "possible_conditions": conditions,
            "reason": f"Combined symptoms considered: {', '.join(state.symptoms)}. Matched against common patterns.",
            "advice": "Rest and monitor symptoms.",
            "when_to_see_doctor": "If symptoms persist or worsen.",
            "disclaimer": "This is informational only and not a medical diagnosis."
        }

    async def _execute_llm(self, state: ClinicalState, matches: List[tuple], route: ExecutionEngine) -> Dict[str, Any]:
        prompt = self._build_master_prompt(state)
        
        try:
            # Call LLM with JSON response format enforced if possible
            response_text = await call_llm_with_fallback(
                messages=[{"role": "system", "content": prompt}],
                use_primary=True
            )
            
            # Parse JSON
            try:
                clean_text = response_text.replace("```json", "").replace("```", "").strip()
                # Find the first { and last }
                start = clean_text.find("{")
                end = clean_text.rfind("}") + 1
                if start != -1 and end != -1:
                    clean_text = clean_text[start:end]
                response_data = json.loads(clean_text)
                return response_data
            except json.JSONDecodeError:
                print("LLM returned invalid JSON. Falling back to rule-based.")
                return self._execute_rule_based(state, matches)
                
        except Exception as e:
            print(f"LLM execution failed: {e}")
            return self._execute_rule_based(state, matches)

    def _build_master_prompt(self, state: ClinicalState) -> str:
        return f"""
You are a clinical reasoning assistant.

PATIENT STATE:
{state.json()}

CRITICAL RULES (MUST FOLLOW):
1. Use ALL symptoms provided in the state.
2. Do NOT ignore any symptom.
3. If multiple symptoms exist, reasoning MUST include ALL of them.
4. Do NOT focus on only one symptom.
5. Do NOT give general explanations.

REASONING REQUIREMENTS:
- Combine symptoms together.
- Explain how symptoms are related.
- Output only relevant conditions (max 2–3).

SAFETY RULE:
If symptoms include blurred vision, severe headache, confusion, chest pain, or difficulty breathing → set risk_level = HIGH.

OUTPUT FORMAT (STRICT JSON):
{{
  "risk_level": "LOW" | "MODERATE" | "HIGH",
  "symptoms": [...],
  "duration": "...",
  "possible_conditions": [{{"name":"...","confidence":0.xx}}],
  "reason": "Explicitly mention ALL symptoms from the state",
  "advice": "...",
  "when_to_see_doctor": "...",
  "disclaimer": "This is informational only and not a medical diagnosis."
}}
"""

unified_pipeline = UnifiedPipeline()
