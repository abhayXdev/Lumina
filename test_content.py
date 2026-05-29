import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

try:
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    models_to_test = [
        'gemini-3.1-flash-lite',
        'gemini-2.5-flash-lite',
        'gemini-2.0-flash-lite',
        'gemini-3.5-flash',
        'gemini-2.5-flash',
        'gemini-2.0-flash'
    ]
    
    for m in models_to_test:
        print(f"Testing {m}...")
        try:
            res = client.models.generate_content(
                model=m,
                contents="Hello!"
            )
            print(f"SUCCESS {m}: {res.text}")
        except Exception as e:
            print(f"FAILED {m}: {e}")

except Exception as e:
    print(f"Client init failed: {e}")
