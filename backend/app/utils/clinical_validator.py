from typing import List, Set, Dict, Any

# Expanded Condition Database for better matching
CONDITION_DB = {
    "Common Cold": {"runny nose", "sneezing", "sore throat", "cough", "mild fever", "congestion", "cold", "fever"},
    "Flu (Influenza)": {"fever", "chills", "body ache", "fatigue", "cough", "headache", "sore throat", "cold"},
    "Pneumonia": {"high fever", "cough", "shortness of breath", "chest pain", "fatigue", "confusion"},
    "Gastroenteritis (Stomach Flu)": {"nausea", "vomiting", "diarrhea", "stomach pain", "fever", "headache"},
    "Migraine": {"severe headache", "nausea", "sensitivity to light", "sensitivity to sound", "blurred vision"},
    "Allergies": {"sneezing", "runny nose", "itchy eyes", "rash", "congestion"},
    "COVID-19": {"fever", "cough", "fatigue", "loss of taste", "loss of smell", "shortness of breath", "sore throat"},
    "Bronchitis": {"cough", "mucus", "fatigue", "shortness of breath", "mild fever", "chest discomfort"}
}

RED_FLAGS = {
    "chest pain",
    "difficulty breathing",
    "confusion",
    "blurred vision",
    "severe headache",
    "high fever", # Added based on common red flags, though user list was specific. Sticking to user list + strict matches.
    "shortness of breath"
}

# User specified RED_FLAGS exactly
STRICT_RED_FLAGS = {
     "chest pain",
     "difficulty breathing",
     "confusion",
     "blurred vision",
     "severe headache"
}

class ClinicalValidator:
    def safety_check(self, state) -> bool:
        """
        Checks for red flags in the symptoms.
        Returns True if any red flag is present (Emergency).
        """
        # Normalize symptoms to check against red flags
        return any(s in STRICT_RED_FLAGS for s in state.symptoms)

    def is_ready(self, state) -> bool:
        """
        STRICT READINESS CHECK:
        Returns True only if there are at least 2 symptoms AND duration is known.
        This prevents providing a diagnosis with vague or insufficient information.
        """
        has_min_symptoms = len(state.symptoms) >= 2
        has_duration = state.duration is not None
        return has_min_symptoms and has_duration

    def match_conditions(self, symptoms: List[str]) -> list:
        """
        Matches symptoms against the condition database.
        STRICT FILTER: Overlap must be >= 2.
        """
        matches = []
        symptom_set = set(symptoms)

        for condition, cond_symptoms in CONDITION_DB.items():
            overlap = len(symptom_set & cond_symptoms)

            # STRICT FILTER (fixes pneumonia bug)
            if overlap >= 2:
                score = overlap / len(cond_symptoms)
                matches.append((condition, score))

        return sorted(matches, key=lambda x: x[1], reverse=True)

    def compute_confidence(self, matches: list) -> float:
        """
        Returns the confidence score of the top match.
        """
        return matches[0][1] if matches else 0.0

    def validate_response(self, state, conditions: List[str]) -> bool:
        """
        RESPONSE VALIDATION (ANTI-PNEUMONIA BUG)
        Prevents overdiagnosis and severe disease misuse.
        """
        # prevent overdiagnosis
        if len(state.symptoms) < 2:
            return False

        # prevent severe disease misuse
        # check if 'pneumonia' or other severe conditions are in the proposed conditions
        # normalize conditions to lower case for check
        conditions_lower = [c.lower() for c in conditions]
        
        if "pneumonia" in conditions_lower and len(state.symptoms) < 3:
            return False

        return True

clinical_validator = ClinicalValidator()
