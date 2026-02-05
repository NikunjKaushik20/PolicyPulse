from src.db import get_db

try:
    db = get_db()
    # The wrapper's find() returns a wrapped cursor, so we iterate it
    cursor = db.users.find() 
    users = list(cursor)
    
    print(f"Found {len(users)} users:")
    for u in users:
        print(f"- Email: '{u.get('email')}' | Name: '{u.get('full_name')}' | PassHash: {u.get('hashed_password')[:10]}...")
except Exception as e:
    print(f"Error: {e}")
