# 🏥 AI Health Assistant

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Groq](https://img.shields.io/badge/Groq-Llama_3-orange?style=for-the-badge)](https://groq.com/)

A professional-grade multimodal AI Health Assistant that bridges the gap between patient queries and clinical insights. Leveraging state-of-the-art LLMs, voice processing, and computer vision, this system provides a comprehensive health companion experience.

## 🎯 Why AI Health Assistant? 
This project demonstrates real-world skills in: 
- **RAG-Driven Clinical Knowledge**: Integration with Pinecone vector database for evidence-based condition explanations using MedlinePlus and WHO data.
- **LLM Routing + Deterministic Intent Detection**: Sophisticated logic to handle diverse health queries with high accuracy.
- **Multimodal AI (Text + Voice + Image)**: Seamless integration of multiple data formats for a holistic health assessment.
- **Secure Authentication (JWT)**: Industry-standard security for protecting sensitive user health data.
- **Database Engineering (PostgreSQL + MongoDB + Pinecone)**: Efficient management of structured profiles, unstructured history, and high-dimensional vector embeddings.
- **Production-Style Backend Architecture**: Scalable, modular design following enterprise software patterns.

---

> [!CAUTION]
> **CRITICAL SAFETY NOTE:** This system is **NOT** a medical diagnosis tool. It is an intelligent health companion designed for informational purposes only. Always consult a licensed medical professional for clinical diagnosis and treatment.

---

## 🌟 Key Features

### 🧠 Advanced Reasoning Engine
- **RAG-Powered Explanations:** Automatically retrieves and explains medical conditions (Symptoms, Causes, Management) using verified sources.
- **Clinical Triage:** Categorizes queries into LOW, MEDIUM, HIGH, or EMERGENCY severity.
- **Explainable AI (XAI):** Provides detailed reasoning for every health insight, citing profile and history factors.
- **Dynamic Recommendations:** Generates tailored lifestyle, nutrition, and immediate action advice.
- **HITL (Human-in-the-Loop):** Critical queries are flagged for escalation to medical specialists.

### 🎙️ Multimodal Intelligence
- **Text & Voice:** Seamlessly switch between typing and recording queries using the Web Speech API.
- **Medical Image Analysis:** Upload images (e.g., skin conditions, reports) for preliminary AI visual inspection.
- **Audio TTS:** Receive audible responses for an accessible user experience.

### 🔒 Security & Privacy
- **Secure Auth:** JWT-based authentication with protected routes.
- **Profile Management:** Stores clinical metadata (Age, BMI, Conditions) in PostgreSQL for personalized context.
- **Encrypted History:** Conversation memory stored in MongoDB Atlas for long-term pattern recognition.

### 📄 Clinical Reporting
- **PDF Generation:** Download high-quality, clinical-grade health reports with professional branding and risk badges.
- **Responsive Dashboard:** View and manage previous assessments and health metrics.

---

## 🛠️ Tech Stack

### Backend
- **Framework:** FastAPI (Asynchronous Python)
- **AI/LLM:** Groq (Llama 3.3 70B), Transformers (BLIP for Vision)
- **Vector DB:** Pinecone (Semantic Search)
- **Embeddings:** Sentence-Transformers (`all-mpnet-base-v2`)
- **Databases:** PostgreSQL (User Profiles), MongoDB (Conversation History)
- **Auth:** Python-Jose (JWT), Passlib (Bcrypt)
- **Services:** FPDF (Reports), gTTS (Speech), SMTP (Emails)

### Frontend
- **Framework:** React 18 (Vite)
- **Styling:** Tailwind CSS, Lucide React (Icons)
- **State Management:** React Hooks, Axios (API Client)

---

## 📁 Project Structure

```
Ai_health_assistant/
├── backend/                # FastAPI Backend Implementation
│   ├── auth/               # JWT & Security logic
│   ├── rag_router.py       # Intent-based RAG Routing
│   ├── rag_service.py      # Pinecone Vector Search
│   ├── medical_ingester.py # Data Ingestion Pipeline
│   ├── disease_urls.json   # Trusted Medical Sources
│   ├── llm_service.py      # Core AI Reasoning Engine
│   ├── query_service.py    # Multimodal processing
│   ├── report_router.py    # PDF Report generation
│   ├── database.py         # SQLAlchemy/PostgreSQL config
│   └── mongo_memory.py     # MongoDB History service
├── frontend_react/         # React + Vite Frontend
│   ├── src/
│   │   ├── components/     # UI Components (ReportCard, InputArea)
│   │   ├── pages/          # Feature Pages (Chat, Dashboard, Profile)
│   │   └── services/       # Backend API Integration
└── ARCHITECTURE.md         # Detailed System Design & Flow
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.9+
- Node.js 18+
- PostgreSQL & MongoDB instances

### 2. Backend Setup
1. **Clone & Install:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Environment Variables:**
   Create a `.env` file in the root directory:
   ```env
   # PostgreSQL
   DATABASE_USERNAME=your_user
   DATABASE_PASSWORD=your_pass
   DATABASE_HOSTNAME=localhost
   DATABASE_PORT=5432
   DATABASE_NAME=health_db

   # MongoDB
   MONGO_URI=mongodb+srv://...

   # AI Keys
   GROQ_API_KEY=gsk_...

   # Security
   JWT_SECRET_KEY=your_super_secret_key
   
   # Email (Optional)
   GMAIL_SENDER_EMAIL=your@gmail.com
   GMAIL_APP_PASSWORD=your_app_password
   ```
3. **Run Server:**
   ```bash
   uvicorn backend.main:app --reload
   ```

### 3. Frontend Setup
1. **Install & Run:**
   ```bash
   cd frontend_react
   npm install
   npm run dev
   ```
2. **Access App:**
   Open `http://localhost:5173` (Vite default) or `http://localhost:3000`.

---

## 📊 System Architecture
For a deep dive into the routing graph, query processing flow, and data schemas, please refer to the [ARCHITECTURE.md](./ARCHITECTURE.md)file.

---

## 🤝 Contributing
Contributions are welcome! Please ensure you follow the safety guidelines and include disclaimers for any AI-related changes.

## 👤 Owner
[Harshitha-Kakumanu](https://github.com/Kakumanu-Harshitha)
