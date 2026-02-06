import os
import time
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODELS_TO_TEST = [
    'gemini-2.5-flash',
    'gemini-flash-latest',
    'gemini-3-flash-preview',
    'gemini-2.0-flash-lite',
    'gemini-1.5-flash' # Just in case
]

print("Testing Gemini Models for Availability...")
print("-" * 40)

for model_name in MODELS_TO_TEST:
    print(f"Testing: {model_name}...", end=" ")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello")
        if response.text:
            print("✅ SUCCESS")
            print(f"Recommended Model: {model_name}")
            break
    except Exception as e:
        print(f"❌ FAILED")
        error_msg = str(e)
        if "404" in error_msg:
            print(f"  -> Model not found (404)")
        elif "429" in error_msg:
            print(f"  -> Rate Limited (429)")
        else:
            print(f"  -> Error: {error_msg}")
    
    time.sleep(1) # Brief pause
