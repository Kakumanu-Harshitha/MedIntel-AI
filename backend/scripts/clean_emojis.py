import re
import os

def clean_file(path):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove emojis and other non-BMP characters
    cleaned = re.sub(r'[^\u0000-\uFFFF]', '', content)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(cleaned)
    print(f"Cleaned: {path}")

clean_file(r'd:\Ai_health_assistant\backend\app\services\bulk_ingester.py')
clean_file(r'd:\Ai_health_assistant\backend\app\rag\rag_service.py')
