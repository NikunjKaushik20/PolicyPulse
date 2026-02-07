import sys
import os

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

from src.eligibility import check_eligibility

def test_why_not():
    print("\n--- Testing 'Why Not' Reasoning ---")
    
    # Profile that should fail PM-KISAN (Income) and SUKANYA (Gender)
    profile = {
        "age": 30,
        "gender": "male",
        "occupation": "farmer",
        "income": 800000, # High income
        "category": "general",
        "land_ownership": True
    }
    
    results = check_eligibility(profile)
    
    print(f"Profile: {profile}\n")
    
    print("ELIBIGLE SCHEMES:")
    for s in results['eligible']:
        print(f"✅ {s['name']}")
        
    print("\nEXCLUDED SCHEMES (Why Not?):")
    for s in results['excluded']:
        if s['reasons']:
            print(f"❌ {s['name']}: {', '.join(s['reasons'])}")
            
            # Check for metadata
            if s.get('metadata'):
                meta = s['metadata']
                print(f"   [Source: {meta.get('authority')} - Notification {meta.get('notification_number', 'N/A')}]")

if __name__ == "__main__":
    test_why_not()
