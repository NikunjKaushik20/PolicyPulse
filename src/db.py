"""
TinyDB Database Connection
Handles connection to local JSON database for user auth and chat history.
Used as a fallback when MongoDB is not available.
"""
import os
import logging
from tinydb import TinyDB, Query, where
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = "policypulse_db.json"

class TinyDBCollection:
    """Wrapper to make TinyDB look like a PyMongo collection."""
    def __init__(self, table):
        self.table = table

    def find_one(self, query):
        """Simulate find_one."""
        if not query:
            return None
        
        # Simple exact match handling
        cond = None
        for k, v in query.items():
            if cond is None:
                cond = (where(k) == v)
            else:
                cond = cond & (where(k) == v)
        
        result = self.table.get(cond)
        if result:
            # Simulate _id
            result['_id'] = str(result.doc_id)
        return result

    def _serialize_dates(self, obj):
        """Recursively convert datetime objects to ISO strings."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                obj[k] = self._serialize_dates(v)
        elif isinstance(obj, list):
            obj = [self._serialize_dates(i) for i in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    def insert_one(self, document):
        """Simulate insert_one."""
        # Convert datetimes to strings for JSON
        doc_copy = self._serialize_dates(document.copy())
        doc_id = self.table.insert(doc_copy)
        return type('InsertOneResult', (object,), {'inserted_id': str(doc_id)})()

    def insert_many(self, documents):
        """Simulate insert_many."""
        docs_copy = [self._serialize_dates(d.copy()) for d in documents]
        doc_ids = self.table.insert_multiple(docs_copy)
        return type('InsertManyResult', (object,), {'inserted_ids': [str(d) for d in doc_ids]})()

    def find(self, query=None):
        """Simulate find returning a cursor-like list."""
        if not query:
            results = self.table.all()
        else:
            cond = None
            for k, v in query.items():
                if cond is None:
                    cond = (where(k) == v)
                else:
                    cond = cond & (where(k) == v)
            results = self.table.search(cond)
            
        # Add fake _id
        for r in results:
            r['_id'] = str(r.doc_id)
            
        return TinyDBCursor(results)

    def create_index(self, keys, **kwargs):
        """No-op for TinyDB."""
        pass

class TinyDBCursor:
    """Wrapper to simulate PyMongo cursor."""
    def __init__(self, data):
        self.data = data

    def sort(self, key, direction=-1):
        """Simulate sort."""
        # direction -1 is DESC, 1 is ASC
        reverse = (direction == -1)
        self.data.sort(key=lambda x: x.get(key, 0), reverse=reverse)
        return self

    def limit(self, n):
        """Simulate limit."""
        self.data = self.data[:n]
        return self

    def __iter__(self):
        return iter(self.data)
        
    def __list__(self):
        return self.data

class TinyDBClient:
    """Wrapper to mimic MongoClient."""
    def __init__(self):
        self._db = TinyDB(DB_PATH)
        self.users = TinyDBCollection(self._db.table('users'))
        self.chats = TinyDBCollection(self._db.table('chats'))

_db_instance = None

def get_db():
    """Get Database Instance (TinyDB)."""
    global _db_instance
    if _db_instance is None:
        logger.info(f"Using TinyDB at {DB_PATH}")
        _db_instance = TinyDBClient()
    return _db_instance

def close_db():
    """Close (No-op for TinyDB usually, but good practice)."""
    global _db_instance
    if _db_instance:
        _db_instance._db.close()

