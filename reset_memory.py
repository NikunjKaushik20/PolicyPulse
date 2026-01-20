from src.qdrant_setup import get_client, COLLECTION_NAME

def reset_all_weights():
    client = get_client()
    
    # get all points
    pts, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=10000,
        with_payload=True
    )
    
    # reset each one
    for pt in pts:
        client.set_payload(
            collection_name=COLLECTION_NAME,
            payload={
                "decay_weight": 1.0,
                "access_count": 0
            },
            points=[pt.id]
        )
    
    print(f"✅ Reset {len(pts)} points to default weights")

if __name__ == "__main__":
    reset_all_weights()
