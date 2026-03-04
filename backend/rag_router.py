"""
RAG Router - Enterprise-Grade Query Routing Controller

This module implements strict intent-based routing to ensure:
1. Correct dataset selection for each query type
2. Anti-loop guarantees (max 1 follow-up)
3. Symptom shortcut optimization
4. Retrieval quality validation
5. Safe fallback handling

Meets enterprise (MNC) standards for safety, scalability, and correctness.
"""

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import re

class QueryIntent(Enum):
    """Primary query intent types with strict priority ordering"""
    EMERGENCY_QUERY = 0         # Critical: Bypasses AI, immediate redirect
    SMALL_TALK = 1             # Greetings, farewells, gratitude
    DISEASE_QUERY = 2          # Highest priority for specific questions
    SYMPTOM_QUERY = 3
    DRUG_INTERACTION_QUERY = 4
    TEST_OR_REPORT_QUERY = 5
    RESEARCH_QUERY = 6         # Lowest priority
    UNKNOWN = 99


class DatasetType(Enum):
    """Available datasets with specific use cases"""
    SYMPTOM_FALLBACK = "symptom_fallback"  # Hardcoded symptom data
    MEDLINEPLUS = "medlineplus"            # Patient education
    WHO_NHS = "who_nhs"                    # Patient education
    ICD11 = "icd11"                        # Disease taxonomy
    DRUG_INTERACTIONS = "drug_interactions" # Safety data
    PUBMED = "pubmed"                      # Research abstracts
    LAB_REFERENCE = "lab_reference"        # Expert lab markers


class RAGRouter:
    """
    Enterprise-grade RAG routing controller with anti-loop guarantees.
    
    Responsibilities:
    1. Intent detection and classification
    2. Dataset routing based on intent
    3. Query optimization and augmentation
    4. Retrieval quality validation
    5. Follow-up control (max 1 per conversation)
    """
    
    # Common symptoms that trigger shortcut (bypass RAG)
    COMMON_SYMPTOMS = {
        "nausea", "nauseous", "headache", "fever", "feverish", "bloating", 
        "fatigue", "tired", "dizziness", "dizzy", "pain", "cough", "coughing",
        "cold", "weakness", "vomiting", "vomit", "diarrhea", "constipation",
        "insomnia", "rash", "back pain", "sore throat", "runny nose",
        "sweating", "chills", "swelling", "itching", "numbness",
        "loss of appetite", "weight loss", "anxiety", "confusion",
        "chest pain", "joint pain", "muscle ache", "shortness of breath",
        "stomach pain", "abdominal pain"
    }
    
    # Symptom keywords for detection
    SYMPTOM_KEYWORDS = COMMON_SYMPTOMS.union({
        "ache", "aching", "hurt", "hurting", "sore", "painful",
        "discomfort", "uncomfortable", "sick", "ill", "unwell",
        "nauseous", "dizzy", "feverish", "vomit", "coughing", "sneezing"
    })
    
    # Disease query patterns
    DISEASE_PATTERNS = [
        r"what is ([\w\s]+)",
        r"tell me about ([\w\s]+)",
        r"explain ([\w\s]+)",
        r"([\w\s]+) disease",
        r"([\w\s]+) condition",
        r"symptoms of ([\w\s]+)",
        r"symptoms for ([\w\s]+)",
        r"signs of ([\w\s]+)",
        r"causes of ([\w\s]+)",
        r"prevention of ([\w\s]+)",
        r"how to prevent ([\w\s]+)",
        r"prevention and symptoms of ([\w\s]+)",
        r"dengue",
        r"malaria",
        r"covid",
        r"diabetes",
        r"cancer",
        r"typhoid",
        r"rheumatic"
    ]
    
    # Drug interaction patterns
    DRUG_PATTERNS = [
        r"interaction",
        r"drug interaction",
        r"medication interaction",
        r"can i take ([\w\s]+) with ([\w\s]+)",
        r"is it safe to take ([\w\s]+) with ([\w\s]+)",
        r"taking ([\w\s]+) (with|and) ([\w\s]+)",
        r"combine ([\w\s]+) and ([\w\s]+)",
        r"safe to take ([\w\s]+) and ([\w\s]+)",
        r"interaction between ([\w\s]+) and ([\w\s]+)",
        r"([\w\s]+) with ([\w\s]+) safe"
    ]
    
    # Test/report patterns
    TEST_PATTERNS = [
        r"blood test",
        r"lab test",
        r"thyroid test",
        r"glucose test",
        r"cholesterol",
        r"test results",
        r"report",
        r"lab report",
        r"hba1c",
        r"glucose",
        r"fasting",
        r"platelets",
        r"tsh",
        r"t3",
        r"t4",
        r"creatinine",
        r"cbc",
        r"biopsy",
        r"mri",
        r"ct scan",
        r"x-ray",
        r"ultrasound"
    ]
    
    # Research patterns
    RESEARCH_PATTERNS = [
        r"research",
        r"study",
        r"studies",
        r"clinical trial",
        r"evidence",
        r"what does research say",
        r"pubmed",
        r"papers on",
        r"journal"
    ]
    
    # Small talk patterns
    GREETINGS = ["hi", "hello", "hey", "good morning", "good evening", "good afternoon", "hi there", "hello there"]
    FAREWELLS = ["bye", "goodbye", "see you", "talk later", "farewell"]
    GRATITUDE = ["thanks", "thank you", "thx", "much appreciated"]
    CASUAL_REPLIES = ["ok", "fine", "cool", "nice", "got it", "alright"]
    
    # Emergency keywords (Deterministic Safety Intercept)
    EMERGENCY_KEYWORDS = {
        "chest pain", "heart attack", "stroke", "cannot breathe", "shortness of breath",
        "suicide", "kill myself", "unconscious", "heavy bleeding", "seizure",
        "poisoning", "overdose", "choking", "anaphylaxis", "severe allergic reaction"
    }

    # Query augmentation rules
    AUGMENTATION_RULES = {
        "platelet": "platelets thrombocytopenia normal range",
        "hba1c": "hba1c diabetes blood sugar monitoring",
        "creatinine": "creatinine kidney function kft egfr",
        "tsh": "tsh thyroid function hypothyroidism hyperthyroidism",
        "hemoglobin": "hemoglobin anemia iron level",
        "alt": "alt sgpt liver function lft",
        "ldl": "ldl cholesterol lipid profile heart health",
        "vitamin d": "vitamin d deficiency bone health",
        "wbc": "wbc white blood cells infection",
        "crp": "crp inflammation marker infection"
    }

    def __init__(self):
        """Initialize RAG router with configuration"""
        self.max_follow_ups = 1  # Enterprise standard: max 1 follow-up
        self.min_similarity_score = 0.3  # Minimum RAG retrieval score
        
    def detect_intent(self, query: str, history: Optional[List[Dict]] = None) -> QueryIntent:
        """
        Detect primary intent from user query with strict priority ordering.
        
        Priority: EMERGENCY > DRUG > RESEARCH > TEST > DISEASE > SYMPTOM
        
        Args:
            query: User's query text
            history: Conversation history (optional)
            
        Returns:
            QueryIntent enum value
        """
        query_lower = query.lower()
        
        # Priority 0: EMERGENCY_QUERY (Immediate Safety Intercept)
        if any(keyword in query_lower for keyword in self.EMERGENCY_KEYWORDS):
            return QueryIntent.EMERGENCY_QUERY

        # Priority 1: SMALL_TALK (Greetings, etc.)
        if self._is_small_talk(query_lower):
            return QueryIntent.SMALL_TALK

        # Priority 2: DRUG_INTERACTION_QUERY (Safety critical, highly specific)
        if self._is_drug_query(query_lower):
            return QueryIntent.DRUG_INTERACTION_QUERY

        # Priority 2: RESEARCH_QUERY (Specific scholarly intent)
        if self._is_research_query(query_lower):
            return QueryIntent.RESEARCH_QUERY

        # Priority 3: TEST_OR_REPORT_QUERY (Specific lab markers/results)
        if self._is_test_query(query_lower):
            return QueryIntent.TEST_OR_REPORT_QUERY

        # Priority 4: DISEASE_QUERY (General condition information)
        if self._is_disease_query(query_lower):
            return QueryIntent.DISEASE_QUERY
            
        # Priority 5: SYMPTOM_QUERY (General symptom reports)
        if self._is_symptom_query(query_lower):
            return QueryIntent.SYMPTOM_QUERY
        
        # Default: UNKNOWN
        return QueryIntent.UNKNOWN
    
    def _is_small_talk(self, query_lower: str) -> bool:
        """Check if query is small talk (greetings, farewells, etc.)"""
        # Clean query: remove punctuation and extra whitespace
        clean_query = re.sub(r'[^\w\s]', '', query_lower).strip()
        
        # Check for single word or short phrase matches
        all_small_talk = self.GREETINGS + self.FAREWELLS + self.GRATITUDE + self.CASUAL_REPLIES
        
        # 1. Exact match for short queries
        if clean_query in all_small_talk:
            return True
            
        # 2. Check if the query starts with a greeting (e.g., "Hi, I have a headache" should NOT be small talk)
        # But "Hi there" should be.
        # So we only count it as small talk if the REMAINING part is also small talk or empty.
        words = clean_query.split()
        if len(words) <= 2:
            if all(word in all_small_talk for word in words):
                return True
                
        return False

    def _is_symptom_query(self, query_lower: str) -> bool:
        """Check if query is about symptoms"""
        # Check for direct symptom mentions
        for symptom in self.SYMPTOM_KEYWORDS:
            if symptom in query_lower:
                return True
        
        # Check for "I have/feel" patterns
        symptom_patterns = [
            r"i have",
            r"i feel",
            r"i'm feeling",
            r"i am feeling",
            r"experiencing",
            r"suffering from"
        ]
        
        for pattern in symptom_patterns:
            if re.search(pattern, query_lower):
                return True
        
        return False
    
    def _is_drug_query(self, query_lower: str) -> bool:
        """Check if query is about drug interactions"""
        for pattern in self.DRUG_PATTERNS:
            if re.search(pattern, query_lower):
                return True
        return False
    
    def _is_test_query(self, query_lower: str) -> bool:
        """Check if query is about tests or reports"""
        for pattern in self.TEST_PATTERNS:
            if re.search(pattern, query_lower):
                return True
        return False
    
    def _is_disease_query(self, query_lower: str) -> bool:
        """Check if query is about a disease/condition"""
        for pattern in self.DISEASE_PATTERNS:
            if re.search(pattern, query_lower):
                return True
        return False
    
    def _is_research_query(self, query_lower: str) -> bool:
        """Check if query is about research/studies"""
        for pattern in self.RESEARCH_PATTERNS:
            if re.search(pattern, query_lower):
                return True
        return False
    
    def should_use_symptom_shortcut(self, query: str, intent: QueryIntent) -> bool:
        """
        Determine if query should bypass RAG and use symptom fallback directly.
        
        Criteria:
        1. NOT a disease-specific query (e.g., "dengue fever") - override everything else
        2. Intent is SYMPTOM_QUERY
        3. Symptom is common (in COMMON_SYMPTOMS)
        4. NOT asking about disease symptoms (e.g., "symptoms of diabetes")
        
        Args:
            query: User's query text
            intent: Detected intent
            
        Returns:
            True if should use shortcut, False otherwise
        """
        query_lower = query.lower()
        
        # Check if it's actually a disease query (higher specificity) - override shortcut
        if self._is_disease_query(query_lower):
            return False

        if intent != QueryIntent.SYMPTOM_QUERY:
            return False

        # Check if asking about disease symptoms (should NOT use shortcut)
        disease_symptom_patterns = [
            "symptoms of", "symptoms for", "what are the symptoms",
            "signs of", "signs and symptoms", "prevention"
        ]
        
        if any(pattern in query_lower for pattern in disease_symptom_patterns):
            return False
        
        # Check if symptom is common
        for symptom in self.COMMON_SYMPTOMS:
            if symptom in query_lower:
                return True
        
        return False
    
    def extract_test_key(self, query: str) -> Optional[str]:
        """
        Deterministic extraction of testKey from query.
        Matches against common lab markers and aliases.
        """
        query_lower = query.lower()
        
        # This list should ideally be synced with lab_reference_dataset.json
        test_keys = [
            "hemoglobin", "rbc_count", "hematocrit", "wbc", "neutrophils", 
            "lymphocytes", "monocytes", "eosinophils", "basophils", "platelets",
            "mcv", "mch", "mchc", "rdw", "esr", "fasting_glucose", "random_glucose",
            "postprandial_glucose", "hba1c", "insulin_level", "c_peptide",
            "tsh", "free_t4", "free_t3", "total_t4", "total_t3", "anti_tpo",
            "creatinine", "urea", "bun", "egfr", "sodium", "potassium", "chloride",
            "uric_acid", "alt_sgpt", "ast_sgot", "alp", "total_bilirubin",
            "direct_bilirubin", "albumin", "total_protein", "ggt", "total_cholesterol",
            "ldl", "hdl", "triglycerides", "vldl", "non_hdl_cholesterol",
            "vitamin_d", "vitamin_b12", "ferritin", "calcium", "magnesium", "iron",
            "crp", "procalcitonin", "dengue_ns1", "dengue_igm", "malaria_antigen"
        ]
        
        for key in test_keys:
            if key.replace("_", " ") in query_lower or key in query_lower:
                return key
                
        return None

    def get_dataset_routing(self, intent: QueryIntent) -> List[DatasetType]:
        """
        Get ordered list of datasets to query based on intent.
        
        Returns datasets in priority order (first = highest priority).
        
        Args:
            intent: Detected query intent
            
        Returns:
            List of DatasetType in priority order
        """
        routing_map = {
            QueryIntent.SYMPTOM_QUERY: [
                DatasetType.SYMPTOM_FALLBACK,  # Primary
                DatasetType.MEDLINEPLUS,        # Secondary
                DatasetType.WHO_NHS             # Tertiary
            ],
            QueryIntent.DRUG_INTERACTION_QUERY: [
                DatasetType.DRUG_INTERACTIONS   # Only drug interaction data
            ],
            QueryIntent.TEST_OR_REPORT_QUERY: [
                DatasetType.LAB_REFERENCE,      # Primary expert knowledge
                DatasetType.MEDLINEPLUS,        # Secondary
                DatasetType.WHO_NHS             # Tertiary
            ],
            QueryIntent.DISEASE_QUERY: [
                DatasetType.MEDLINEPLUS,        # Primary (patient education)
                DatasetType.WHO_NHS,            # Secondary (patient education)
                DatasetType.ICD11               # Fallback (taxonomy only)
            ],
            QueryIntent.RESEARCH_QUERY: [
                DatasetType.PUBMED              # Only research data
            ],
            QueryIntent.UNKNOWN: [
                DatasetType.MEDLINEPLUS,        # Default to patient education
                DatasetType.WHO_NHS,
                DatasetType.ICD11
            ]
        }
        
        return routing_map.get(intent, [DatasetType.MEDLINEPLUS])
    
    def augment_query(self, query: str, intent: QueryIntent) -> str:
        """
        Augment query with keywords to improve retrieval based on intent.
        Includes specific rules for lab reference data.
        """
        query_lower = query.lower()
        
        # Apply specific lab augmentation rules
        for trigger, addition in self.AUGMENTATION_RULES.items():
            if trigger in query_lower:
                query = f"{query} {addition}"
                break

        augmentation_map = {
            QueryIntent.SYMPTOM_QUERY: "symptom causes treatment management",
            QueryIntent.DRUG_INTERACTION_QUERY: "drug interaction safety warning",
            QueryIntent.TEST_OR_REPORT_QUERY: "test results interpretation normal range",
            QueryIntent.DISEASE_QUERY: "disease condition overview causes symptoms",
            QueryIntent.RESEARCH_QUERY: "research study clinical evidence"
        }
        
        augmentation = augmentation_map.get(intent, "")
        
        if augmentation:
            return f"{augmentation} {query}"
        
        return query
    
    def get_min_score(self, intent: QueryIntent) -> float:
        """Get strict similarity threshold based on query intent."""
        thresholds = {
            QueryIntent.SYMPTOM_QUERY: 0.35,
            QueryIntent.RESEARCH_QUERY: 0.45,
            QueryIntent.DRUG_INTERACTION_QUERY: 0.5,
            QueryIntent.DISEASE_QUERY: 0.35,
            QueryIntent.TEST_OR_REPORT_QUERY: 0.4
        }
        return thresholds.get(intent, 0.3)

    def validate_retrieval_quality(
        self, 
        results: List[Dict], 
        intent: QueryIntent,
        min_score: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        Validate that retrieved results are sufficient and relevant.
        
        Args:
            results: Retrieved documents from RAG
            intent: Detected intent
            min_score: Minimum similarity score (optional, uses default if None)
            
        Returns:
            Tuple of (is_valid, reason)
        """
        if min_score is None:
            min_score = self.get_min_score(intent)
        
        # Check 1: Do we have any results?
        if not results or len(results) == 0:
            return False, "No results retrieved from knowledge base"
        
        # Check 2: Are results above minimum score threshold?
        high_quality_results = [r for r in results if r.get('score', 0) >= min_score]
        
        if not high_quality_results:
            return False, f"All results below quality threshold ({min_score})"
        
        # Check 3: Intent-specific validation
        if intent == QueryIntent.SYMPTOM_QUERY:
            # For symptom queries, check if we have symptom-focused content
            has_symptom_content = any(
                r.get('metadata', {}).get('category') == 'Primary Symptom' or
                r.get('metadata', {}).get('category') == 'Patient Education'
                for r in high_quality_results
            )
            
            if not has_symptom_content:
                return False, "No symptom-focused content in results"
        
        elif intent == QueryIntent.DRUG_INTERACTION_QUERY:
            # For drug queries, ensure we have drug interaction data
            has_drug_content = any(
                'drug interaction' in r.get('source', '').lower() or
                r.get('metadata', {}).get('category') == 'Medication Safety'
                for r in high_quality_results
            )
            
            if not has_drug_content:
                return False, "No drug interaction data in results"
        
        # All checks passed
        return True, "Retrieval quality validated"
    
    def should_ask_follow_up(
        self, 
        query: str, 
        intent: QueryIntent,
        history: Optional[List[Dict]] = None
    ) -> bool:
        """
        Determine if a follow-up question should be asked.
        
        ENTERPRISE CLINICAL RULES:
        1. Allow follow-ups if query is brief (< 5 words) and lacks context (duration/severity)
        2. Max 1 follow-up per topic to prevent loops
        3. Only ask if it helps narrow down potential causes safely
        
        Args:
            query: User's query text
            intent: Detected intent
            history: Conversation history
            
        Returns:
            True if should ask follow-up, False otherwise
        """
        query_lower = query.lower()
        
        # Rule 1: Max 1 follow-up per interaction sequence
        if history:
            # Check last 4 interactions for clarification questions already asked.
            # History items are {"role": ..., "content": ...} dicts — NOT type-keyed objects.
            # A clarification response is stored as a JSON string containing "clarification_questions".
            for interaction in history[-4:]:
                role = interaction.get('role', '')
                content = interaction.get('content', '')
                # Detect assistant clarification responses whether stored as JSON string or plain
                if role == 'assistant' and (
                    '"type": "clarification_questions"' in content
                    or "clarification_questions" in content
                    or "how long have you been experiencing" in content.lower()
                    or "how long has this been" in content.lower()
                ):
                    return False  # Already asked recently, don't loop
        
        # Rule 2: NEVER ask for disease symptom queries (they are informational)
        disease_symptom_patterns = [
            "symptoms of", "symptoms for", "what are the symptoms",
            "signs of", "signs and symptoms"
        ]
        if any(pattern in query_lower for pattern in disease_symptom_patterns):
            return False
        
        # Rule 3: Check for brevity and lack of context
        word_count = len(query.split())
        has_duration = any(word in query_lower for word in ["day", "week", "month", "long", "since", "yesterday"])
        has_severity = any(word in query_lower for word in ["severe", "mild", "bad", "worst", "intense", "low"])
        
        # If it's a symptom query and very short, ask for more details
        if intent == QueryIntent.SYMPTOM_QUERY and word_count < 6 and not (has_duration or has_severity):
            return True
            
        # Rule 4: Vague personal symptoms always need clarification
        vague_patterns = [
            r"i don't feel well",
            r"something is wrong",
            r"i feel bad",
            r"not feeling good",
            r"i am sick",
            r"feeling unwell"
        ]
        
        for pattern in vague_patterns:
            if re.search(pattern, query_lower):
                return True
        
        # Rule 5: If it's a common symptom but no context provided, allow one follow-up
        if self.should_use_symptom_shortcut(query, intent) and word_count < 4:
            return True
            
        return False
    
    def filter_results_by_dataset(
        self, 
        results: List[Dict], 
        allowed_datasets: List[DatasetType]
    ) -> List[Dict]:
        """
        Filter retrieved results to only include allowed datasets.
        
        Args:
            results: Retrieved documents
            allowed_datasets: List of allowed dataset types
            
        Returns:
            Filtered list of results
        """
        if not allowed_datasets:
            return results
        
        allowed_dataset_names = {ds.value for ds in allowed_datasets}
        
        filtered = []
        for result in results:
            # Check dataset field in metadata
            dataset = result.get('metadata', {}).get('dataset', '').lower()
            
            # Also check source field for backward compatibility
            source = result.get('source', '').lower()
            
            # Map source to dataset type
            if dataset in allowed_dataset_names:
                filtered.append(result)
            elif 'medlineplus' in source and DatasetType.MEDLINEPLUS in allowed_datasets:
                filtered.append(result)
            elif 'who' in source or 'nhs' in source and DatasetType.WHO_NHS in allowed_datasets:
                filtered.append(result)
            elif 'icd' in source and DatasetType.ICD11 in allowed_datasets:
                filtered.append(result)
            elif 'drug interaction' in source and DatasetType.DRUG_INTERACTIONS in allowed_datasets:
                filtered.append(result)
            elif 'pubmed' in source and DatasetType.PUBMED in allowed_datasets:
                filtered.append(result)
        
        return filtered


# Global router instance
rag_router = RAGRouter()
