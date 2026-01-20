from src.qdrant_setup import create_collection_if_not_exists

if __name__ == "__main__":
    print("🔧 Creating collection and indexes...")
    create_collection_if_not_exists()
    print("✅ Done!")
