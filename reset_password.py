from src.db import get_db
from src.auth import get_password_hash
from tinydb import Query

def reset_password(email, new_password):
    db = get_db()
    email = email.lower()
    
    # TinyDB update logic
    User = Query()
    new_hash = get_password_hash(new_password)
    
    # db.users is our wrapper, db.users.table is the raw TinyDB table
    updated = db.users.table.update({'hashed_password': new_hash}, User.email == email)
    
    if updated:
        print(f"✅ Password reset for {email} to: {new_password}")
    else:
        print(f"❌ User not found or update failed for {email}")

if __name__ == "__main__":
    reset_password("nikunjkaushik28@gmail.com", "123456")
