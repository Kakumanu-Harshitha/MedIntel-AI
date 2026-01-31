import os
import uuid
from groq import Groq
from gtts import gTTS
from dotenv import load_dotenv
from fastapi import UploadFile

# Load environment variables from .env file
load_dotenv()

# --- Initialize Groq Client ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = None
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)
    print("✅ Groq client for Speech-to-Text initialized.")
else:
    print("⚠️ WARNING: GROQ_API_KEY not found! Speech-to-Text service will be disabled.")

STT_MODEL = "whisper-large-v3"

def speech_to_text(audio_file: UploadFile) -> str:
    """
    Transcribes an audio file using Groq's Whisper model.
    """
    if not groq_client:
        return "[stt_error] Speech service is not configured due to missing API key."

    try:
        # Pass the file as a (filename, file_object) tuple, which the client expects.
        file_tuple = (audio_file.filename, audio_file.file)

        transcription = groq_client.audio.transcriptions.create(
            model=STT_MODEL,
            file=file_tuple,
            response_format="verbose_json"
        )
        return transcription.text
    except Exception as e:
        print(f"❌ ERROR: Groq STT API call failed. Error: {e}")
        return f"[stt_error] {e}"

# Define base static directory relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, "static", "audio")

def text_to_speech(text: str, output_dir: str = DEFAULT_OUTPUT_DIR) -> str:
    """
    Converts text to speech using gTTS and returns the filename.
    """
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Clean text (remove markdown asterisks etc for better reading)
        clean_text = text.replace("*", "").replace("#", "").replace("-", " ")
        
        # Limit length for gTTS (it can be slow)
        if len(clean_text) > 500:
            clean_text = clean_text[:500] + "... Check the report for more details."

        filename = f"{uuid.uuid4()}.mp3"
        file_path = os.path.join(output_dir, filename)
        
        tts = gTTS(text=clean_text, lang='en')
        tts.save(file_path)
        
        return filename
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        return None

