from enum import Enum

class ExecutionEngine(Enum):
    EMERGENCY = "emergency"
    FOLLOW_UP = "follow_up"
    RULE_BASED = "rule_based"
    RAG = "rag"
    LLM = "llm"

class AdaptiveRouter:
    def route(self, state, confidence, ready, safety_flag):
        if safety_flag:
            return ExecutionEngine.EMERGENCY

        if not ready:
            return ExecutionEngine.FOLLOW_UP

        if confidence > 0.75:
            return ExecutionEngine.RULE_BASED

        elif 0.5 <= confidence <= 0.75:
            return ExecutionEngine.RAG

        else:
            return ExecutionEngine.LLM

adaptive_router = AdaptiveRouter()