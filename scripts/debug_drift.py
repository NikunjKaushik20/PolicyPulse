"""Quick debug script for drift analysis."""
import sys
sys.path.insert(0, ".")

from src.chromadb_setup import get_all_documents

# Get NREGA docs with embeddings
print("Fetching NREGA documents...")
r = get_all_documents(where={"policy_id": "NREGA"}, include_embeddings=True)

print(f"Total docs: {len(r.get('ids', []))}")
print(f"Has embeddings key: {'embeddings' in r}")
print(f"Embeddings type: {type(r.get('embeddings'))}")

if r.get('embeddings'):
    print(f"First embedding type: {type(r['embeddings'][0])}")
    print(f"First embedding length: {len(r['embeddings'][0]) if r['embeddings'][0] else 'None'}")

# Check years
years = set()
for m in r.get('metadatas', []):
    y = m.get('year')
    if y:
        years.add(y)

print(f"\nYears found: {sorted(years) if years else 'None'}")
print(f"Number of unique years: {len(years)}")

# Sample metadata
if r.get('metadatas'):
    print(f"\nSample metadata[0]: {r['metadatas'][0]}")
