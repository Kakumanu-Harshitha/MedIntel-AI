# Medical Condition Explanation System Documentation

## Overview
This document outlines the architecture and implementation of the Medical Condition Explanation system in the AI Health Assistant. The system uses Retrieval-Augmented Generation (RAG) to provide evidence-based medical information alongside AI analysis of images and lab reports.

## System Architecture

### 1. Data Ingestion & Storage
- **Source Management**: Medical URLs from trusted sources (MedlinePlus, NHS, WHO, ICD-11) are stored in `backend/disease_urls.json`.
- **Ingestion Pipeline**: The `backend/medical_ingester.py` script scrapes these URLs, cleans the content, and generates embeddings using the `all-mpnet-base-v2` sentence-transformer model.
- **Vector Database**: Processed document chunks are stored in **Pinecone** for efficient semantic search.

### 2. Retrieval-Augmented Generation (RAG)
The RAG pipeline is managed by `backend/rag_service.py` and `backend/rag_router.py`.
- **Intent Detection**: The system identifies if a user query is a disease-related or symptom-related question.
- **Query Augmentation**: User queries are expanded with keywords like "causes", "symptoms", and "management" to improve retrieval accuracy.
- **Semantic Search**: Pinecone returns the top-K most relevant medical snippets based on the augmented query.
- **Source Prioritization**: Results are ranked with priority given to MedlinePlus, WHO, and ICD-11.

### 3. AI Analysis & Explanation (LLM)
The `backend/llm_service.py` handles the generation of clinical reports.
- **Prompt Engineering**: Specific prompts (`PROMPT_MEDICAL_RAG`, `PROMPT_REPORT_ANALYZER`, `PROMPT_MEDICAL_IMAGE`) enforce a structured JSON response containing a `health_information` field.
- **Requirement**: The LLM must include a detailed medical explanation (Definition, Symptoms, Causes, Management) for any condition discussed.

### 4. Frontend Rendering
The React frontend in `frontend_react/src/components/ReportCard.jsx` renders the AI's response.
- **Detailed Visibility**: Displays the `health_information` field with Markdown support to ensure the user can read formatted medical knowledge.
- **Confidence Scoring**: Displays an AI confidence level to provide transparency on the generated analysis.

## Key Files
- [disease_urls.json](file:///d:/Ai_health_assistant/backend/disease_urls.json): Trusted source directory.
- [medical_ingester.py](file:///d:/Ai_health_assistant/backend/medical_ingester.py): Data processing and indexing logic.
- [rag_service.py](file:///d:/Ai_health_assistant/backend/rag_service.py): Pinecone search and ranking.
- [llm_service.py](file:///d:/Ai_health_assistant/backend/llm_service.py): Response generation and prompt logic.
- [ReportCard.jsx](file:///d:/Ai_health_assistant/frontend_react/src/components/ReportCard.jsx): UI component for report display.

## Safety Disclaimer
The system is designed for informational purposes only. Every report generated includes a mandatory medical disclaimer advising users to consult with healthcare professionals for diagnosis and treatment.
