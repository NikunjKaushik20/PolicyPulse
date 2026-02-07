from src.db import get_db
from src.auth import verify_password, get_password_hash

email_input = "nikunjkaushik28@Gmail.com" # Simulating user input
password_guess = "nikunj123" # Guessing a common password or just testing validity

def test_auth():
    db = get_db()
    
    # 1. Test case insensitive lookup
    email = email_input.lower()
    print(f"Looking up: {email}")
    
    user = db.users.find_one({"email": email})
    if not user:
        print("❌ User not found!")
        return
        
    print(f"✅ User found: {user['email']}")
    
    # 2. Test password verification (Simulating failure if unknown)
    # We can't know the real password, but we can verify if the HASHING works.
    # Let's create a temp user/hash to verify the LIBRARY works.
    
    test_pass = "test1234"
    test_hash = get_password_hash(test_pass)
    print(f"Test Hash generated: {test_hash[:10]}...")
    
    is_valid = verify_password(test_pass, test_hash)
    print(f"Library Verification Test: {'✅ Passed' if is_valid else '❌ Failed'}")

    # 3. Check actual user password (we can't technically check without knowing it)
    # But we can print the stored hash to see if it looks corrupted
    print(f"Stored Hash for user: {user['hashed_password']}")
    
if __name__ == "__main__":
    test_auth()
