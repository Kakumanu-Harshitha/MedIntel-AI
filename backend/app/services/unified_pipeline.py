import asyncio
import json
import os
import hashlib
from typing import Dict, Any, List, Optional
from enum import Enum

from app.ai_pipeline.clinical_memory import state_manager, session_repo, ClinicalState, Session
from app.utils.clinical_validator import clinical_validator
from app.ai_pipeline.adaptive_router import adaptive_router, ExecutionEngine
from app.database.cache import AsyncCache
from app.services.llm_service import call_llm_with_fallback
from app.services import speech_service
from app.rag.rag_service import rag_service

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

class UnifiedPipeline:
    def __init__(self):
        self.state_manager = state_manager
        self.session_repo = session_repo
        self.validator = clinical_validator
        self.router = adaptive_router
        self.rag = rag_service
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
            session.last_question = None
            self.session_repo.save_session(session)
            return override_response
        
        # 3. Safety Layer
        safety_flag = self.validator.safety_check(updated_state)

        # 4. Readiness Check
        # RELAXED READINESS: If we have symptoms and duration, we proceed even if only 1 symptom
        is_ready = bool(updated_state.symptoms) and bool(updated_state.duration)

        # 5. Clinical Matching and Confidence Scoring
        matches = self.validator.match_conditions(updated_state.symptoms)
        confidence = self.validator.compute_confidence(matches)

        # 6. Adaptive Routing
        route = self.router.route(updated_state, confidence, is_ready, safety_flag)

        # 7. Cache Check
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
        possible_conditions = [c["name"] for c in response_data.get("possible_conditions", [])]
        
        # Only block if it's a severe condition for too few symptoms
        if route in [ExecutionEngine.RULE_BASED, ExecutionEngine.RAG, ExecutionEngine.LLM]:
            # Use specific validator rules
            if not self.validator.validate_response(updated_state, possible_conditions):
                if len(updated_state.symptoms) == 1 and updated_state.duration:
                    # Special Case: Single symptom + duration is actually enough for a basic but specific analysis
                    pass 
                else:
                    response_data = await self._generate_llm_follow_up(updated_state)
                    # Don't overwrite advice if it's already a specific question
                    if not response_data["advice"] or response_data["advice"] == "READY":
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

        # Save session
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
        
        current_symptoms = {s.lower() for s in state.symptoms}
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
                "reason": f"Critical symptoms detected: {', '.join(found_red_flags)}.",
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
            "reason": f"Red flag symptoms detected.",
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
        elif not state.symptoms:
            question = "What symptoms are you experiencing?"
            qtype = "SYMPTOMS"
        else:
            # If we have 1 symptom + duration, we should ideally NOT be here anymore 
            # as process_request handles single-symptom 'readiness'.
            # This is a safety fallback.
            question = "Do you have any other symptoms, or is it just the " + (state.symptoms[0] if state.symptoms else "symptom") + "?"
            qtype = "SYMPTOMS"

        return {
            "risk_level": "LOW",
            "symptoms": state.symptoms,
            "duration": state.duration,
            "possible_conditions": [],
            "reason": "Gathering more clinical context.",
            "advice": question,
            "last_question": qtype,
            "when_to_see_doctor": "If symptoms worsen.",
            "disclaimer": "This is informational only and not a medical diagnosis."
        }

    def _execute_rule_based(self, state: ClinicalState, matches: List[tuple]) -> Dict[str, Any]:
        top_matches = matches[:3]
        conditions = [{"name": m[0], "confidence": round(m[1], 2)} for m in top_matches]
        
        risk = "LOW"
        if any(c["confidence"] > 0.8 for c in conditions):
            risk = "MODERATE"
            
        return {
            "risk_level": risk,
            "symptoms": state.symptoms,
            "duration": state.duration,
            "possible_conditions": conditions,
            "reason": f"Matched logic for: {', '.join(state.symptoms)}.",
            "advice": "Rest and monitor symptoms.",
            "when_to_see_doctor": "If symptoms persist or worsen.",
            "disclaimer": "This is informational only and not a medical diagnosis."
        }

    async def _execute_llm(self, state: ClinicalState, matches: List[tuple], route: ExecutionEngine) -> Dict[str, Any]:
        # Enrichment: Fetch Medical Knowledge via RAG
        knowledge_context = ""
        if route == ExecutionEngine.RAG or (route == ExecutionEngine.LLM and state.symptoms):
            search_term = state.symptoms[0] if state.symptoms else "general symptoms"
            print(f"🔍 [UnifiedPipeline] RAG Search for: {search_term}")
            results = self.rag.search(f"{search_term} causes and duration", top_k=3)
            if results:
                knowledge_context = "\n".join([f"- {r['title']}: {r['text'][:300]}" for r in results])

        prompt = self._build_master_prompt(state, context=knowledge_context)
        
        try:
            response_text = await call_llm_with_fallback(
                messages=[{"role": "system", "content": prompt}],
                use_primary=True
            )
            
            try:
                clean_text = response_text.replace("```json", "").replace("```", "").strip()
                start = clean_text.find("{")
                end = clean_text.rfind("}") + 1
                if start != -1 and end != -1:
                    clean_text = clean_text[start:end]
                response_data = json.loads(clean_text)
                
                # Ensure symptoms and duration from state are mirrored in response
                response_data["symptoms"] = state.symptoms
                response_data["duration"] = state.duration
                return response_data
            except json.JSONDecodeError:
                return self._execute_rule_based(state, matches)
                
        except Exception as e:
            print(f"LLM execution failed: {e}")
            return self._execute_rule_based(state, matches)

    def _build_master_prompt(self, state: ClinicalState, context: str = "") -> str:
        context_block = f"\nRELEVANT MEDICAL KNOWLEDGE (RAG):\n{context}" if context else ""
        
        return f"""
You are a senior clinical reasoning assistant. 

PATIENT STATE:
{state.json()}
{context_block}

CRITICAL RULES:
1. Provide a SPECIFIC and CLINICALLY SOUND analysis.
2. If only one symptom is present (e.g., "headache") and duration is present (e.g., "5 days"), explain potential causes for THAT specific symptom+duration combination.
3. NEVER output generic disclaimers like "limited information" or "challenging to offer specific diagnosis".
4. Use the provided MEDICAL KNOWLEDGE (RAG) to ground your reasoning.
5. If duration is long (e.g., 5 days), emphasize that it warrants attention if not improving.
6. The 'reason' field MUST explicitly address why these symptoms for this duration are worth noting.

OUTPUT FORMAT (STRICT JSON ONLY):
{{
  "risk_level": "LOW" | "MODERATE" | "HIGH",
  "symptoms": [...],
  "duration": "...",
  "possible_conditions": [{{"name":"...","confidence":0.xx}}],
  "reason": "Specific analysis of symptoms + duration",
  "advice": "Specific clinical advice grounded in medical knowledge",
  "when_to_see_doctor": "Specific cues (e.g. if persists beyond X days)",
  "disclaimer": "This is informational only and not a medical diagnosis."
}}
"""

unified_pipeline = UnifiedPipeline()
