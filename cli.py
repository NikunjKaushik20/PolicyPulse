"""
Command-line interface for PolicyPulse data ingestion and management.

Provides commands to:
- Reset the vector database
- Ingest policy data from CSV and text files
- Load embeddings and sentiment analysis
"""

import argparse
import csv
import os
import logging
from uuid import uuid4
from src.qdrant_setup import get_client, COLLECTION_NAME, create_collection_if_not_exists
from src.embeddings import embed_text, get_sentiment
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

logger = logging.getLogger(__name__)

# Qdrant configuration
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
VECTOR_DIMENSION = 384

# Policy ID mappings
POLICY_MAPPINGS = {
    'nrega': 'NREGA',
    'rti': 'RTI',
    'swachhbharat': 'SWACHH-BHARAT',
    'digitalindia': 'DIGITAL-INDIA',
    'makeindia': 'MAKE-IN-INDIA',
    'skillindia': 'SKILL-INDIA',
    'smartcities': 'SMART-CITIES',
    'nep': 'NEP',
    'pmkisan': 'PM-KISAN',
    'ayushmanbharat': 'AYUSHMAN-BHARAT'
}

# Default payload values
DEFAULT_DECAY_WEIGHT = 1.0
DEFAULT_ACCESS_COUNT = 0
DEFAULT_SENTIMENT = 'neutral'

# File paths
DATA_DIRECTORY = 'data'
BUDGET_FILE_TEMPLATE = f'{DATA_DIRECTORY}/{{prefix}}_budgets.csv'
NEWS_FILE_TEMPLATE = f'{DATA_DIRECTORY}/{{prefix}}_news.csv'
TEMPORAL_FILE_TEMPLATE = f'{DATA_DIRECTORY}/{{prefix}}_temporal.txt'

# Text parsing constants
TEMPORAL_YEAR_PREFIX = 'Year '
TEMPORAL_YEAR_SEPARATOR = ':'
MIN_TEMPORAL_TEXT_LENGTH = 50
BUDGET_TEXT_VARIANTS = 3  # Multiple paraphrases per budget entry


def reset_database() -> None:
    """
    Reset the Qdrant database by deleting and recreating the collection.
    
    WARNING: This operation is destructive and cannot be undone.
    All stored policy data will be deleted.
    """
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    try:
        client.delete_collection(COLLECTION_NAME)
        logger.info("Deleted existing collection")
        print("🗑️  Deleted old collection")
    except Exception as error:
        logger.warning(f"No existing collection to delete: {error}")
        print("⚠️  No existing collection found")
    
    # Create fresh collection
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_DIMENSION, distance=Distance.COSINE)
    )
    logger.info("Created fresh collection")
    print("✅ Created fresh collection!")


def ingest_all_policies() -> None:
    """
    Ingest all policy data from CSV and text files.
    
    Processes three data modalities:
    1. Budget data (CSV): Financial allocations and expenditures
    2. News data (CSV): Media coverage and public discourse
    3. Temporal data (TXT): Policy evolution text by year
    
    Each entry is embedded using sentence transformers and stored
    with metadata for filtering and memory management.
    """
    client = get_client()
    total_ingested = 0
    
    for file_prefix, policy_id in POLICY_MAPPINGS.items():
        logger.info(f"Processing policy: {policy_id}")
        
        # ===== Budget Ingestion =====
        budget_file_path = BUDGET_FILE_TEMPLATE.format(prefix=file_prefix)
        if os.path.exists(budget_file_path):
            budget_ingested = _ingest_budget_file(client, budget_file_path, policy_id)
            total_ingested += budget_ingested
        else:
            logger.warning(f"Budget file not found: {budget_file_path}")
        
        # ===== News Ingestion =====
        news_file_path = NEWS_FILE_TEMPLATE.format(prefix=file_prefix)
        if os.path.exists(news_file_path):
            news_ingested = _ingest_news_file(client, news_file_path, policy_id)
            total_ingested += news_ingested
        else:
            logger.warning(f"News file not found: {news_file_path}")
        
        # ===== Temporal Ingestion =====
        temporal_file_path = TEMPORAL_FILE_TEMPLATE.format(prefix=file_prefix)
        if os.path.exists(temporal_file_path):
            temporal_ingested = _ingest_temporal_file(client, temporal_file_path, policy_id)
            total_ingested += temporal_ingested
        else:
            logger.warning(f"Temporal file not found: {temporal_file_path}")
    
    print(f"\n🎉 Ingestion complete! Total ingested: {total_ingested} chunks")
    logger.info(f"Ingestion complete: {total_ingested} total chunks ingested")


def _ingest_budget_file(client: QdrantClient, file_path: str, policy_id: str) -> int:
    """
    Ingest budget data from CSV file.
    
    Creates multiple text variants per budget entry to improve
    semantic coverage and retrieval diversity.
    
    Args:
        client: Qdrant client instance.
        file_path: Path to budget CSV file.
        policy_id: Policy identifier.
        
    Returns:
        int: Number of points ingested.
    """
    budget_points = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                year = int(row['year'])
                allocated_crores = float(row['allocated_crores'])
                spent_crores = float(row['spent_crores'])
                focus_area = row['focus_area']
                
                # Create multiple text variants for better retrieval
                text_variants = [
                    (f"{policy_id} budget {year}: Allocated Rs {allocated_crores} crore, "
                     f"spent Rs {spent_crores} crore. Focus: {focus_area}"),
                    (f"{policy_id} {year} expenditure: Budget utilization "
                     f"{round((spent_crores/allocated_crores)*100, 1)}% with focus on {focus_area}"),
                    (f"{policy_id} {year} financial allocation: {focus_area} program "
                     f"with Rs {allocated_crores} crore sanctioned")
                ]
                
                for text_variant in text_variants:
                    budget_points.append(PointStruct(
                        id=str(uuid4()),
                        vector=embed_text(text_variant),
                        payload={
                            'content': text_variant,
                            'policy_id': policy_id,
                            'year': year,
                            'modality': 'budget',
                            'sentiment': DEFAULT_SENTIMENT,
                            'allocation_crores': allocated_crores,
                            'expenditure_crores': spent_crores,
                            'decay_weight': DEFAULT_DECAY_WEIGHT,
                            'access_count': DEFAULT_ACCESS_COUNT
                        }
                    ))
        
        if budget_points:
            client.upsert(collection_name=COLLECTION_NAME, points=budget_points)
            print(f"✅ {policy_id} budgets: {len(budget_points)} chunks ingested")
            logger.info(f"{policy_id} budget ingestion: {len(budget_points)} chunks")
        
        return len(budget_points)
        
    except Exception as error:
        logger.error(f"Failed to ingest budget file {file_path}: {error}")
        return 0


def _ingest_news_file(client: QdrantClient, file_path: str, policy_id: str) -> int:
    """
    Ingest news and discourse data from CSV file.
    
    Args:
        client: Qdrant client instance.
        file_path: Path to news CSV file.
        policy_id: Policy identifier.
        
    Returns:
        int: Number of points ingested.
    """
    news_points = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                year = int(row['year'])
                headline = row['headline']
                summary = row['summary']
                source = row['source']
                sentiment = row['sentiment']
                
                # Combine into single text for embedding
                combined_text = f"{headline}. {summary} (Source: {source}, {year})"
                
                news_points.append(PointStruct(
                    id=str(uuid4()),
                    vector=embed_text(combined_text),
                    payload={
                        'content': combined_text,
                        'policy_id': policy_id,
                        'year': year,
                        'modality': 'news',
                        'sentiment': sentiment,
                        'headline': headline,
                        'decay_weight': DEFAULT_DECAY_WEIGHT,
                        'access_count': DEFAULT_ACCESS_COUNT
                    }
                ))
        
        if news_points:
            client.upsert(collection_name=COLLECTION_NAME, points=news_points)
            print(f"✅ {policy_id} news: {len(news_points)} chunks ingested")
            logger.info(f"{policy_id} news ingestion: {len(news_points)} chunks")
        
        return len(news_points)
        
    except Exception as error:
        logger.error(f"Failed to ingest news file {file_path}: {error}")
        return 0


def _ingest_temporal_file(client: QdrantClient, file_path: str, policy_id: str) -> int:
    """
    Ingest temporal/policy evolution data from text file.
    
    Expected format:
        Year 2005:
        Policy description text here...
        
        Year 2010:
        Updated policy text...
    
    Args:
        client: Qdrant client instance.
        file_path: Path to temporal text file.
        policy_id: Policy identifier.
        
    Returns:
        int: Number of points ingested.
    """
    temporal_points = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
            # Split by double newlines (paragraph separators)
            for paragraph in content.split('\n\n'):
                paragraph = paragraph.strip()
                
                # Check for year marker
                if paragraph.startswith(TEMPORAL_YEAR_PREFIX) and TEMPORAL_YEAR_SEPARATOR in paragraph:
                    try:
                        # Extract year
                        year_part = paragraph.split(TEMPORAL_YEAR_SEPARATOR)[0]
                        year_str = year_part.replace(TEMPORAL_YEAR_PREFIX, '').strip()
                        year = int(year_str)
                        
                        # Extract text after year marker
                        text_content = paragraph.replace(f'{TEMPORAL_YEAR_PREFIX}{year}:', '').strip()
                        
                        # Only ingest if text is substantial
                        if len(text_content) >= MIN_TEMPORAL_TEXT_LENGTH:
                            temporal_points.append(PointStruct(
                                id=str(uuid4()),
                                vector=embed_text(text_content),
                                payload={
                                    'content': text_content,
                                    'policy_id': policy_id,
                                    'year': year,
                                    'modality': 'temporal',
                                    'sentiment': get_sentiment(text_content),
                                    'decay_weight': DEFAULT_DECAY_WEIGHT,
                                    'access_count': DEFAULT_ACCESS_COUNT
                                }
                            ))
                    
                    except (ValueError, IndexError) as parse_error:
                        logger.warning(f"Failed to parse temporal entry: {parse_error}")
                        continue
        
        if temporal_points:
            client.upsert(collection_name=COLLECTION_NAME, points=temporal_points)
            print(f"✅ {policy_id} temporal: {len(temporal_points)} chunks ingested")
            logger.info(f"{policy_id} temporal ingestion: {len(temporal_points)} chunks")
        
        return len(temporal_points)
        
    except Exception as error:
        logger.error(f"Failed to ingest temporal file {file_path}: {error}")
        return 0


def main() -> None:
    """
    Main CLI entry point.
    
    Supports commands:
        reset-db: Delete and recreate the collection
        ingest-all: Load all policy data from files
    """
    parser = argparse.ArgumentParser(
        description='PolicyPulse CLI - Manage policy data ingestion'
    )
    parser.add_argument(
        'command',
        choices=['ingest-all', 'reset-db'],
        help='Command to execute'
    )
    
    args = parser.parse_args()
    
    if args.command == 'reset-db':
        print("🔄 Resetting database...")
        logger.info("User initiated database reset")
        reset_database()
    
    elif args.command == 'ingest-all':
        print("📦 Ingesting policy data...")
        logger.info("User initiated data ingestion")
        create_collection_if_not_exists()
        ingest_all_policies()


if __name__ == "__main__":
    main()