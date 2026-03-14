"""
Dataset Deletion Utility for AI Health Assistant

This script allows safe deletion of specific datasets from Pinecone
without affecting other data.

Usage:
    python backend/delete_datasets.py WHO_NHS
    python backend/delete_datasets.py SNOMED_CT
    python backend/delete_datasets.py UMLS

CRITICAL: Only deletes datasets with the specified 'dataset' metadata field.
"""

import sys
from backend.rag_service import rag_service

def delete_dataset(dataset_name: str):
    """
    Deletes all vectors with the specified dataset metadata.
    
    Args:
        dataset_name: One of "WHO_NHS", "SNOMED_CT", "UMLS", "MedlinePlus", "PubMed", "lab_reference", "ICD11_MMS", "OpenFDA_DDI"
    
    Raises:
        ValueError: If dataset_name is not valid
    """
    VALID_DATASETS = ["WHO_NHS", "SNOMED_CT", "UMLS", "MedlinePlus", "PubMed", "lab_reference", "ICD11_MMS", "OpenFDA_DDI"]
    
    if dataset_name not in VALID_DATASETS:
        raise ValueError(
            f"Invalid dataset: '{dataset_name}'. "
            f"Must be one of: {VALID_DATASETS}"
        )
    
    if not rag_service.enabled:
        print("❌ RAG Service is not enabled. Check your PINECONE_API_KEY.")
        return
    
    if rag_service.mock_mode:
        print(f"[MOCK MODE] Would delete all vectors with dataset='{dataset_name}'")
        return
    
    # Confirm deletion
    print(f"⚠️  WARNING: This will delete ALL vectors with dataset='{dataset_name}'")
    print(f"   This action cannot be undone.")
    
    confirm = input(f"   Type '{dataset_name}' to confirm deletion: ")
    
    if confirm != dataset_name:
        print("❌ Deletion cancelled. Confirmation did not match.")
        return
    
    try:
        # Delete by metadata filter using rag_service method
        rag_service.delete_by_filter(filter_dict={"dataset": dataset_name})
        print(f"✅ Successfully deleted all vectors with dataset='{dataset_name}'")
        print(f"   ℹ️  Other datasets remain unaffected.")
    except Exception as e:
        print(f"❌ Error during deletion: {e}")

def list_datasets():
    """
    Lists all available datasets that can be deleted.
    """
    print("📋 Available Datasets for Deletion:")
    print("   - WHO_NHS: Patient education fact sheets from WHO and NHS")
    print("   - SNOMED_CT: Disease and symptom ontology (subset)")
    print("   - UMLS: Unified Medical Language System mappings")
    print("   - MedlinePlus: Health topic summaries from MedlinePlus")
    print("   - PubMed: Clinical research abstracts from PubMed")
    print("   - lab_reference: Lab test reference ranges and explanations")
    print("   - ICD11_MMS: Clinical taxonomy from ICD-11")
    print("   - OpenFDA_DDI: Drug-drug interaction profiles from OpenFDA")
    print("\nUsage:")
    print("   python backend/delete_datasets.py <DATASET_NAME>")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("❌ Error: Missing dataset name argument")
        print()
        list_datasets()
        sys.exit(1)
    
    dataset_arg = sys.argv[1]
    
    if dataset_arg in ["--help", "-h", "help"]:
        list_datasets()
        sys.exit(0)
    
    try:
        delete_dataset(dataset_arg)
    except ValueError as e:
        print(f"❌ {e}")
        print()
        list_datasets()
        sys.exit(1)
