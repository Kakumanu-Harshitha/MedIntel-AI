from rag_service import rag_service
import uuid

# Expanded Trusted Medical Data representing various gold-standard sources
TRUSTED_DATA = [
    # --- MedlinePlus (Patient-friendly) ---
    {
        "title": "Diabetes Overview",
        "source": "MedlinePlus",
        "category": "Patient Education",
        "text": "Diabetes is a disease in which your blood glucose, or blood sugar, levels are too high. Glucose comes from the foods you eat. Insulin is a hormone that helps the glucose get into your cells to give them energy. With type 1 diabetes, your body does not make insulin. With type 2 diabetes, the more common type, your body does not make or use insulin well."
    },
    {
        "title": "Healthy Sleep Habits",
        "source": "MedlinePlus",
        "category": "Wellness",
        "text": "Sleep is a natural process that helps your body restore energy, supports learning and memory, and keeps you healthy. Most adults need 7-9 hours of sleep. Good sleep habits include sticking to a schedule, keeping the bedroom dark and cool, and avoiding caffeine or large meals before bed."
    },
    
    # --- PubMed (Clinical/Research) ---
    {
        "title": "Alzheimer's Disease and Peripheral Cancer",
        "source": "PubMed (PMID: 41576952)",
        "category": "Clinical Research",
        "text": "Recent studies suggest that peripheral cancer may attenuate amyloid pathology in Alzheimer's disease via cystatin-c activation of TREM2. This research opens new pathways for understanding the intersection of oncology and neurodegeneration."
    },
    {
        "title": "Chronic Respiratory Disease in Asia (1990-2023)",
        "source": "PubMed (Lancet Respir Med)",
        "category": "Global Health",
        "text": "A systematic analysis for the Global Burden of Disease Study 2023 shows a significant burden of chronic respiratory diseases in Asia. The study highlights the need for improved air quality and early intervention strategies in developing regions."
    },

    # --- ICD-11 (Taxonomy/Classification) ---
    {
        "title": "ICD-11 Code: 1B70 (Influenza)",
        "source": "ICD-11",
        "category": "Taxonomy",
        "text": "1B70 Influenza due to identified seasonal influenza virus. This category includes influenza with pneumonia, influenza with other respiratory manifestations, and influenza with other manifestations. It is used globally for mortality and morbidity statistics."
    },
    {
        "title": "ICD-11 Code: CA40 (Asthma)",
        "source": "ICD-11",
        "category": "Taxonomy",
        "text": "CA40 Asthma is a chronic inflammatory disorder of the airways in which many cells and cellular elements play a role. The chronic inflammation is associated with airway hyper-responsiveness that leads to recurrent episodes of wheezing, breathlessness, chest tightness, and coughing."
    },
    {
        "title": "ICD-11 Code: 5A11 (Type 2 Diabetes)",
        "source": "ICD-11",
        "category": "Taxonomy",
        "text": "5A11 Type 2 diabetes mellitus is characterized by insulin resistance and relative insulin deficiency, either of which may be predominant at the time of diagnosis."
    },
    {
        "title": "ICD-11 Code: 8A60 (Alzheimer Disease)",
        "source": "ICD-11",
        "category": "Taxonomy",
        "text": "8A60 Alzheimer disease is a neurodegenerative disease that is the most common cause of dementia. It usually starts slowly and progressively worsens over time."
    },
    {
        "title": "ICD-11 Code: 1D0Z (Tuberculosis)",
        "source": "ICD-11",
        "category": "Taxonomy",
        "text": "1D0Z Tuberculosis is an infectious disease usually caused by Mycobacterium tuberculosis (MTB) bacteria. Tuberculosis generally affects the lungs, but can also affect other parts of the body."
    },
    {
        "title": "ICD-11 Code: BA00 (Hypertension)",
        "source": "ICD-11",
        "category": "Taxonomy",
        "text": "BA00 Essential hypertension is high blood pressure that doesn't have a known secondary cause. It is also referred to as primary hypertension."
    },

    # --- MeSH (Subject Headings/Hierarchy) ---
    {
        "title": "Analgesics (MeSH Category)",
        "source": "MeSH",
        "category": "Hierarchy",
        "text": "Analgesics are compounds capable of relieving pain without the loss of consciousness. They are classified into various subcategories including opioid analgesics, non-narcotic analgesics, and anti-inflammatory agents. MeSH Tree: D03.383.663.283."
    },
    {
        "title": "Cardiovascular Diseases (MeSH Category)",
        "source": "MeSH",
        "category": "Hierarchy",
        "text": "Diseases of the HEART and BLOOD VESSELS. This category includes conditions like hypertension, myocardial ischemia, and various arrhythmias. MeSH Tree: C14."
    },

    # --- UMLS (Interoperability/Concepts) ---
    {
        "title": "Concept: C0011847 (Diabetes Mellitus)",
        "source": "UMLS",
        "category": "Concept Mapping",
        "text": "UMLS CUI C0011847 maps terms across SNOMED CT (73211009), ICD-10 (E10-E14), and MeSH (D003920). It represents a group of metabolic diseases characterized by high blood sugar levels over a prolonged period."
    },
    {
        "title": "Concept: C0020538 (Hypertension)",
        "source": "UMLS",
        "category": "Concept Mapping",
        "text": "UMLS CUI C0020538 represents High Blood Pressure. It links clinical terms used by pharmacies, hospitals, and insurance companies to ensure interoperability in electronic health records."
    },

    # --- Original Data (Retained for consistency) ---
    {
        "title": "Influenza (Flu) - Symptoms",
        "source": "CDC",
        "category": "Public Health",
        "text": "Influenza (flu) can cause mild to severe illness. Symptoms usually come on suddenly: fever, cough, sore throat, runny nose, muscle aches, headaches, and fatigue."
    }
]

def seed_database():
    print("🌱 Seeding RAG Database with Medical Gold-Standard Data...")
    
    if not rag_service.enabled:
        print("❌ RAG Service is not enabled (Check API Key or Dependencies).")
        return

    count = 0
    for item in TRUSTED_DATA:
        # Create a unique ID based on title and source
        doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{item['source']}-{item['title']}"))
        
        # Upsert
        rag_service.upsert_document(
            doc_id=doc_id,
            text=item["text"],
            metadata={
                "source": item["source"],
                "title": item["title"],
                "category": item.get("category", "General"),
                "text": item["text"]
            }
        )
        count += 1
        print(f"   - Indexed: [{item['source']}] {item['title']}")
    
    print(f"✅ Seeding Complete. {count} documents indexed in Pinecone.")

if __name__ == "__main__":
    seed_database()
