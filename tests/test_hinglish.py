
import sys
import os
sys.path.append(os.getcwd()) # Ensure we can find src
from src.language_detection import detect_language

queries = [
    "PM Kisan ke liye eligibility kya hai?",
    "NREGA ka status kaise check karein",
    "Mujhe loan chahiye",
    "Sarkar kya scheme de rahi hai?",
    "What is the eligibility for PM Kisan?"
]

print("Testing PolicyPulse Detection (with Hinglish support):")
for q in queries:
    try:
        res, conf = detect_language(q)
        print(f"'{q}' -> {res} ({conf:.2f})")
    except Exception as e:
        print(f"'{q}' -> Error: {e}")
