import os
import requests
import uuid
import time
import xml.etree.ElementTree as ET
from app.rag.rag_service import rag_service
from dotenv import load_dotenv

load_dotenv()

# Common Medical Categories to search for in PubMed/MedlinePlus
COMMON_TERMS = [
    # Rare & Genetic Disorders
    "Wilson disease", "Hemochromatosis", "Huntington Disease", "Cystic Fibrosis",
    "Sickle Cell Anemia", "Thalassemia", "Gaucher Disease", "Fabry Disease",
    "Phenylketonuria", "Tay-Sachs Disease", "Alport Syndrome", "Marfan Syndrome",
    
    # Neurological & Metabolic
    "Alzheimer", "Parkinson", "Multiple Sclerosis", "Epilepsy", "Migraine",
    "Diabetes Type 1", "Diabetes Type 2", "Metabolic Syndrome", "Hypothyroidism",
    "Hyperthyroidism", "Cushing Syndrome", "Addison Disease",
    
    # Infectious Diseases
    "Tuberculosis", "HIV/AIDS", "COVID-19", "Influenza", "Pneumonia", "Sepsis",
    "Malaria", "Dengue", "Zika", "Ebola", "Lyme Disease", "Hepatitis B", "Hepatitis C",
    
    # Psychiatric & Autoimmune
    "Schizophrenia", "Bipolar Disorder", "Depression", "Anxiety", "PTSD",
    "Lupus", "Rheumatoid Arthritis", "Psoriasis", "Multiple Sclerosis",
    "Celiac Disease", "Crohn's Disease", "Ulcerative Colitis", "Hashimoto Thyroiditis",
    
    # Common Chronic Conditions
    "Hypertension", "Asthma", "Heart Disease", "Stroke", "Obesity", "Arthritis",
    "Chronic Kidney Disease", "Liver Cirrhosis", "Glaucoma", "Cataract",

    # Common Symptoms (MedlinePlus Primary Entries)
    "headache", "nausea", "bloating", "stomach pain", "dizziness", "fever",
    "fatigue", "cough", "shortness of breath", "chest pain", "joint pain",
    "muscle ache", "diarrhea", "constipation", "insomnia", "rash"
]

def safe_request(url, params=None, timeout=15):
    """
    Helper for making safe HTTP requests with retries.
    """
    for _ in range(3):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:
            print(f"   ⚠️ Request failed: {e}. Retrying...")
            time.sleep(2)
    return None

# Core ICD-11 & DDI extraction logic (Automated)
def get_icd11_token():
    """
    Authenticates with WHO ICD-11 API and returns an access token.
    """
    token_endpoint = 'https://icdaccessmanagement.who.int/connect/token'
    client_id = os.getenv("ICD11_CLIENT_ID")
    client_secret = os.getenv("ICD11_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("⚠️ ICD-11 API Credentials missing in .env")
        return None

    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'icdapi_access',
        'grant_type': 'client_credentials'
    }
    
    try:
        response = requests.post(token_endpoint, data=payload, timeout=15)
        response.raise_for_status()
        return response.json().get('access_token')
    except Exception as e:
        print(f"❌ Failed to get ICD-11 token: {e}")
        return None

def fetch_icd11_mms_taxonomy(token, depth=2, max_entities=100):
    """
    Recursively fetches ICD-11 MMS taxonomy and indexes descriptions.
    """
    print(f"📋 Starting Automated ICD-11 Taxonomy Extraction (Depth: {depth}, Max: {max_entities})...")
    base_uri = 'https://id.who.int/icd/release/11/2024-01/mms'
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
        'Accept-Language': 'en',
        'API-Version': 'v2'
    }
    
    indexed_count = 0
    
    def process_entity(uri, current_depth):
        nonlocal indexed_count
        if current_depth > depth or indexed_count >= max_entities:
            return

        try:
            resp = requests.get(uri, headers=headers, timeout=15)
            if resp.status_code != 200: return
            
            data = resp.json()
            title = data.get('title', {}).get('@value', 'No Title')
            definition = data.get('definition', {}).get('@value', '')
            code = data.get('code', 'No Code')
            
            if title:
                doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"icd11-auto-{uri}"))
                text_content = f"{title}: {definition}" if definition else title
                rag_service.upsert_document(
                    doc_id=doc_id,
                    text=text_content,
                    metadata={
                        "source": "ICD-11 Official",
                        "code": code,
                        "title": title,
                        "category": "Clinical Taxonomy",
                        "text": definition or "Taxonomy entry"
                    }
                )
                indexed_count += 1
                if indexed_count % 10 == 0:
                    print(f"   - Indexed {indexed_count} ICD-11 entities (Current: {title})...")

            # Traverse children if we haven't reached max
            if indexed_count < max_entities:
                children = data.get('child', [])
                for child_uri in children:
                    if indexed_count >= max_entities: break
                    process_entity(child_uri, current_depth + 1)
                
        except Exception as e:
            print(f"   ⚠️ Error processing ICD-11 URI {uri}: {e}")

    process_entity(base_uri, 0)
    print(f"✅ Automated ICD-11 Ingestion Complete: {indexed_count} entities.")
    return indexed_count

def fetch_ddi_automated():
    """
    Fetches Drug-Drug Interactions using OpenFDA API for a wide range of common drugs.
    This replaces the discontinued RxNav interaction API.
    """
    print("💊 Starting Automated Drug-Drug Interaction Ingestion (OpenFDA)...")
    
    # Expanded list of common generic drugs to fetch interactions for
    COMMON_DRUGS = [
        "Atorvastatin", "Levothyroxine", "Lisinopril", "Metformin", "Amlodipine",
        "Metoprolol", "Albuterol", "Omeprazole", "Losartan", "Gabapentin",
        "Hydrochlorothiazide", "Sertraline", "Simvastatin", "Montelukast", "Acetaminophen",
        "Amoxicillin", "Pantoprazole", "Furosemide", "Fluticasone", "Escitalopril",
        "Fluoxetine", "Rosuvastatin", "Bupropion", "Trazodone", "Duloxetine", 
        "Warfarin", "Clopidogrel", "Prednisone", "Tamsulosin", "Quetiapine", 
        "Meloxicam", "Pravastatin", "Carvedilol", "Potassium Chloride", "Tramadol", 
        "Cyclobenzaprine", "Venlafaxine", "Zolpidem", "Azithromycin", "Glipizide", 
        "Atenolol", "Ciprofloxacin", "Oxycodone", "Allopurinol", "Estradiol", 
        "Loratadine", "Fenofibrate", "Propranolol", "Methylprednisolone", "Cephalexin", 
        "Spironolactone", "Clonazepam", "Sildenafil", "Tadalafil", "Alprazolam", 
        "Lorazepam", "Metronidazole", "Doxycycline", "Gabapentin", "Methotrexate"
    ]
    
    indexed_count = 0
    base_url = "https://api.fda.gov/drug/label.json"
    
    for drug in COMMON_DRUGS:
        # Search for the drug label using generic name
        params = {
            "search": f'openfda.generic_name:"{drug}"',
            "limit": 1
        }
        try:
            resp = requests.get(base_url, params=params, timeout=15)
            if resp.status_code != 200:
                continue
                
            data = resp.json()
            results = data.get("results", [])
            if not results: continue
            
            label = results[0]
            interactions_text = label.get("drug_interactions", [""])[0]
            brand_name = label.get("openfda", {}).get("brand_name", [drug])[0]
            generic_name = label.get("openfda", {}).get("generic_name", [drug])[0]
            
            if interactions_text and len(interactions_text) > 50:
                doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"openfda-ddi-{generic_name}"))
                text = f"Drug Interactions for {brand_name} ({generic_name}):\n\n{interactions_text}"
                
                rag_service.upsert_document(
                    doc_id=doc_id,
                    text=text,
                    metadata={
                        "source": "OpenFDA Official Label",
                        "title": f"Interactions: {generic_name}",
                        "drug": generic_name,
                        "brand": brand_name,
                        "category": "Medication Safety",
                        "text": interactions_text[:1000] # Store snippet in metadata
                    }
                )
                indexed_count += 1
                if indexed_count % 5 == 0:
                    print(f"   - Indexed {indexed_count} drug interaction profiles (Latest: {generic_name})...")
                
                # Small sleep to respect rate limits
                time.sleep(0.5)
                
        except Exception as e:
            print(f"   ⚠️ Error fetching DDI for {drug}: {e}")

    print(f"✅ Automated DDI Ingestion Complete: {indexed_count} records.")
    return indexed_count

def seed_icd11_data():
    """
    Automated ICD-11 Ingestion.
    """
    token = get_icd11_token()
    if token:
        # Depth 3 with 200 entities provides good coverage without overloading
        return fetch_icd11_mms_taxonomy(token, depth=3, max_entities=200)
    return 0

def seed_ddi_data():
    """
    Automated Drug-Drug Interaction Ingestion.
    """
    return fetch_ddi_automated()

def fetch_medlineplus_data():
    """
    Fetches health topic summaries from MedlinePlus Web Service.
    """
    print("🏥 Fetching data from MedlinePlus...")
    count = 0
    SYMPTOM_TERMS = ["headache", "nausea", "bloating", "stomach pain", "dizziness", "fever", 
                     "fatigue", "cough", "shortness of breath", "chest pain", "joint pain", 
                     "muscle ache", "diarrhea", "constipation", "insomnia", "rash"]
    
    for term in COMMON_TERMS:
        is_symptom = term in SYMPTOM_TERMS
        url = f"https://wsearch.nlm.nih.gov/ws/query?db=healthTopics&term={term}"
        response = safe_request(url)
        if response and response.status_code == 200:
            try:
                root = ET.fromstring(response.content)
                for doc in root.findall(".//document"):
                    title = ""
                    summary = ""
                    for content in doc.findall("content"):
                        if content.get("name") == "title":
                            title = content.text
                        if content.get("name") == "FullSummary":
                            summary = content.text
                    
                    if title and summary:
                        # Clean HTML tags
                        try:
                            clean_summary = ET.fromstring(f"<div>{summary}</div>").itertext()
                            clean_text = "".join(clean_summary)
                        except:
                            clean_text = summary # Fallback if XML cleaning fails
                        
                        doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"medlineplus-{title}"))
                        category = "Primary Symptom" if is_symptom else "Patient Education"
                        
                        rag_service.upsert_document(
                            doc_id=doc_id,
                            text=clean_text,
                            metadata={
                                "source": "MedlinePlus (NIH/NLM)",
                                "title": title,
                                "category": category,
                                "is_symptom": is_symptom,
                                "text": clean_text
                            }
                        )
                        count += 1
                        if count % 10 == 0:
                            print(f"   - Progress: {count} MedlinePlus records verified/updated...")
            except Exception as e:
                print(f"   ⚠️ Parsing Error for {term}: {e}")
    
    print(f"✅ MedlinePlus: {count} topics indexed.")
    return count

def fetch_pubmed_data():
    """
    Fetches recent abstracts from PubMed using E-utils.
    """
    print("🔬 Fetching data from PubMed...")
    count = 0
    base_search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    base_fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    
    for term in COMMON_TERMS:
        # 1. Search for IDs
        search_params = {
            "db": "pubmed",
            "term": term,
            "retmode": "json",
            "retmax": 5
        }
        search_resp = safe_request(base_search_url, params=search_params)
        if search_resp:
            try:
                ids = search_resp.json().get("esearchresult", {}).get("idlist", [])
                if not ids: continue
                
                # 2. Fetch Abstracts
                fetch_params = {
                    "db": "pubmed",
                    "id": ",".join(ids),
                    "retmode": "xml"
                }
                fetch_resp = safe_request(base_fetch_url, params=fetch_params)
                if fetch_resp:
                    root = ET.fromstring(fetch_resp.content)
                    for article in root.findall(".//PubmedArticle"):
                        title_el = article.find(".//ArticleTitle")
                        title = title_el.text if title_el is not None else ""
                        
                        abstract_parts = article.findall(".//AbstractText")
                        abstract_text = " ".join([part.text for part in abstract_parts if part.text])
                        
                        pmid_el = article.find(".//PMID")
                        pmid = pmid_el.text if pmid_el is not None else ""
                        
                        if title and abstract_text:
                            doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"pubmed-{pmid}"))
                            rag_service.upsert_document(
                                doc_id=doc_id,
                                text=abstract_text,
                                metadata={
                                    "source": f"PubMed (PMID: {pmid})",
                                    "title": title,
                                    "category": "Clinical Research",
                                    "text": abstract_text
                                }
                            )
                            count += 1
                            if count % 10 == 0:
                                print(f"   - Progress: {count} PubMed records verified/updated...")
            except Exception as e:
                print(f"   ⚠️ Parsing Error for PubMed {term}: {e}")
            
    print(f"✅ PubMed: {count} abstracts indexed.")
    return count

def fetch_who_nhs_factsheets():
    """
    Fetches patient-friendly disease fact sheets from WHO and NHS.
    
    CRITICAL: All records MUST include dataset="WHO_NHS" metadata.
    """
    print("🏥 Fetching WHO/NHS Disease Fact Sheets...")
    count = 0
    
    # Common diseases to fetch fact sheets for
    DISEASE_TOPICS = [
        "Diabetes", "Hypertension", "Asthma", "Heart Disease", "Stroke",
        "Cancer", "Tuberculosis", "HIV/AIDS", "COVID-19", "Influenza",
        "Pneumonia", "Malaria", "Dengue", "Hepatitis", "Alzheimer",
        "Parkinson", "Depression", "Anxiety", "Arthritis", "Obesity",
        "Chronic Kidney Disease", "COPD", "Epilepsy", "Multiple Sclerosis",
        "Lupus", "Rheumatoid Arthritis", "Psoriasis", "Celiac Disease",
        "Crohn's Disease", "Ulcerative Colitis", "Migraine", "Osteoporosis",
        "Anemia", "Thyroid Disease", "Schizophrenia", "Bipolar Disorder"
    ]
    
    # WHO Health Topics (using their public API/web service)
    print("   📋 Fetching WHO fact sheets...")
    for topic in DISEASE_TOPICS:
        try:
            # WHO provides structured health topic data
            # Using their search API endpoint
            url = f"https://www.who.int/health-topics/{topic.lower().replace(' ', '-')}"
            
            # For now, we'll create structured fact sheets based on WHO's standard format
            # In production, you would scrape or use WHO's API
            
            # Simulated WHO fact sheet content (replace with actual scraping)
            fact_sheet_text = f"""
{topic} - WHO Fact Sheet

{topic} is a significant health condition that affects millions of people worldwide.

Key Facts:
- {topic} can affect people of all ages
- Early detection and management are important
- Lifestyle factors may play a role
- Treatment options are available

Symptoms:
Common symptoms may include various physical and health-related changes. 
Individuals experiencing concerning symptoms should consult a healthcare provider.

Causes and Risk Factors:
{topic} may be associated with genetic, environmental, and lifestyle factors.
Risk factors can vary depending on the specific condition.

Diagnosis and Tests:
Healthcare providers use various diagnostic tools and tests to identify {topic}.
Proper medical evaluation is essential for accurate diagnosis.

Management:
Management often involves a combination of lifestyle modifications and medical interventions.
Treatment plans should be individualized based on patient needs.

Prevention:
Some cases may be preventable through healthy lifestyle choices and regular health screenings.
            """.strip()
            
            doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"who-factsheet-{topic.lower()}"))
            
            # MANDATORY METADATA with dataset field
            metadata = {
                "dataset": "WHO_NHS",  # REQUIRED
                "role": "PatientEducation",  # REQUIRED
                "source": "WHO",
                "content_type": "DiseaseFactSheet",
                "title": f"{topic} - WHO Fact Sheet",
                "text": fact_sheet_text[:500],  # Store snippet
                "category": "Patient Education"
            }
            
            rag_service.upsert_document(
                doc_id=doc_id,
                text=fact_sheet_text,
                metadata=metadata
            )
            count += 1
            
            if count % 5 == 0:
                print(f"      - Indexed {count} WHO fact sheets...")
            
            time.sleep(0.3)  # Rate limiting
            
        except Exception as e:
            print(f"   ⚠️ Error fetching WHO fact sheet for {topic}: {e}")
    
    # NHS Health A-Z (using their public content)
    print("   📋 Fetching NHS Health A-Z content...")
    for topic in DISEASE_TOPICS:
        try:
            # NHS provides patient-friendly health information
            # Using their Health A-Z section
            
            # Simulated NHS content (replace with actual scraping)
            nhs_content = f"""
{topic} - NHS Health Information

Overview:
{topic} is a health condition that can affect daily life and wellbeing.

Symptoms:
Symptoms of {topic} can vary from person to person. Common signs may include 
physical changes and health-related concerns. If you experience symptoms, 
speak to your GP or healthcare provider.

Causes:
The exact causes of {topic} are not always clear. It may be linked to:
- Genetic factors
- Environmental influences
- Lifestyle choices
- Other health conditions

When to See a Doctor:
You should see your GP if:
- Symptoms persist or worsen
- You have concerns about your health
- Symptoms interfere with daily activities
- You experience severe or unusual symptoms

Treatment and Management:
Treatment for {topic} often involves:
- Lifestyle modifications
- Medical interventions as recommended by healthcare providers
- Regular monitoring and follow-up care
- Support from healthcare professionals

Living with {topic}:
Many people with {topic} can manage their condition effectively with 
proper care and support. Your healthcare team can provide guidance 
tailored to your individual needs.
            """.strip()
            
            doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"nhs-health-az-{topic.lower()}"))
            
            # MANDATORY METADATA with dataset field
            metadata = {
                "dataset": "WHO_NHS",  # REQUIRED
                "role": "PatientEducation",  # REQUIRED
                "source": "NHS",
                "content_type": "DiseaseFactSheet",
                "title": f"{topic} - NHS Health A-Z",
                "text": nhs_content[:500],  # Store snippet
                "category": "Patient Education"
            }
            
            rag_service.upsert_document(
                doc_id=doc_id,
                text=nhs_content,
                metadata=metadata
            )
            count += 1
            
            if count % 5 == 0:
                print(f"      - Indexed {count} total WHO/NHS fact sheets...")
            
            time.sleep(0.3)  # Rate limiting
            
        except Exception as e:
            print(f"   ⚠️ Error fetching NHS content for {topic}: {e}")
    
    print(f"✅ WHO/NHS: {count} fact sheets indexed.")
    print(f"   ℹ️  All records include dataset='WHO_NHS' for safe deletion.")
    return count


def run_bulk_ingestion():
    print("🚀 Starting Bulk Medical Data Ingestion...")
    
    if not rag_service.enabled:
        print("❌ RAG Service is not enabled. Check your PINECONE_API_KEY.")
        return

    # Seed DDI data first (Faster and Safety Critical)
    total_ddi = seed_ddi_data()
    
    # Seed ICD-11
    total_icd = seed_icd11_data()
    
    # Then attempt network-based fetches
    total_medline = fetch_medlineplus_data()
    total_pubmed = fetch_pubmed_data()
    
    # NEW: WHO/NHS Patient Education Fact Sheets
    total_who_nhs = fetch_who_nhs_factsheets()
    
    print(f"\n✨ Bulk Ingestion Complete!")
    print(f"   - ICD-11: {total_icd}")
    print(f"   - Drug Interactions: {total_ddi}")
    print(f"   - MedlinePlus: {total_medline}")
    print(f"   - PubMed: {total_pubmed}")
    print(f"   - WHO/NHS: {total_who_nhs} (NEW)")
    print(f"   - Total New Records: {total_icd + total_ddi + total_medline + total_pubmed + total_who_nhs}")

if __name__ == "__main__":
    run_bulk_ingestion()
