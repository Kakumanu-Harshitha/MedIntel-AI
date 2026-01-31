import os
import torch
import open_clip
from sentence_transformers import SentenceTransformer
import easyocr

def download_models():
    print("🚀 Starting model pre-download process...")

    # 1. RAG Embedding Model
    print("⏳ Downloading RAG Embedding Model (all-mpnet-base-v2)...")
    SentenceTransformer('all-mpnet-base-v2')
    print("✅ RAG Embedding Model downloaded.")

    # 2. MediCLIP (BiomedCLIP) Model
    MEDICLIP_MODEL_ID = "hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224"
    print(f"⏳ Downloading MediCLIP Model ({MEDICLIP_MODEL_ID})...")
    # This will download and cache the model weights
    open_clip.create_model_and_transforms(MEDICLIP_MODEL_ID)
    open_clip.get_tokenizer(MEDICLIP_MODEL_ID)
    print("✅ MediCLIP Model downloaded.")

    # 3. EasyOCR Models
    print("⏳ Downloading EasyOCR Models (English)...")
    # This will download and cache the detection and recognition models
    easyocr.Reader(['en'], gpu=False)
    print("✅ EasyOCR Models downloaded.")

    print("\n🎉 All models have been successfully downloaded and cached!")

if __name__ == "__main__":
    download_models()
