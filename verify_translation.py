import os
import sys
from dotenv import load_dotenv

# Ensure we can import from src
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Load env to get keys
load_dotenv()

from src.translation import translate_text

def test_translation():
    print("="*50)
    print("Testing Translation Logic (Gemini Fallback)")
    print("="*50)
    
    google_key = os.getenv("GOOGLE_CLOUD_TRANSLATE_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    print(f"Google Key present: {bool(google_key and google_key.strip())}")
    print(f"Gemini Key present: {bool(gemini_key and gemini_key.strip())}")
    
    text = "What is the eligibility criteria for PM Kisan scheme?"
    target = "hi"
    
    print(f"\nOriginal: {text}")
    print(f"Target: {target}")
    print("-" * 30)
    
    try:
        translated = translate_text(text, target_lang=target)
        print(f"Translated: {translated}")
        
        # Simple check if it looks like Hindi (Devanagari range)
        is_hindi = any('\u0900' <= char <= '\u097f' for char in translated)
        if is_hindi:
            print("\n✅ Success: Output contains Hindi characters.")
        else:
            print("\n⚠️ Warning: Output does not look like Hindi.")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    test_translation()
