import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

try:
    client = genai.Client(api_key=GEMINI_API_KEY)
    print("--- RAW MODELS DUMP ---")
    for m in client.models.list():
        print(f"Name: {m.name}, Methods: {getattr(m, 'supported_generation_methods', 'N/A')}")
    print("-----------------------")
except Exception as e:
    print(f"Failed: {e}")
