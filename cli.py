"""
Command-line interface for PolicyPulse data ingestion and management.
Uses ChromaDB for Docker-free vector storage.
"""

import argparse
import csv
import os
import logging
from uuid import uuid4
from src.chromadb_setup import reset_collection, add_documents, get_collection_info
from src.embeddings import embed_text, get_sentiment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# v2: refactored from single ingest_all.py script
# keeping the old mappings for backward compat with data folder naming

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
    'ayushmanbharat': 'AYUSHMAN-BHARAT',
    # Batch 2: 10 policies added
    'ujjwala': 'UJJWALA',
    'jandhan': 'JAN-DHAN',
    'mudra': 'MUDRA',
    'jaljeevan': 'JAL-JEEVAN',
    'startupindia': 'STARTUP-INDIA',
    'fasalbima': 'FASAL-BIMA',
    'atalpension': 'ATAL-PENSION',
    'betibachao': 'BETI-BACHAO',
    'saubhagya': 'SAUBHAGYA',
    'pmay': 'PMAY',
    # Batch 3: 10 more policies added
    'standupindia': 'STANDUP-INDIA',
    'sukanya': 'SUKANYA',
    'kcc': 'KCC',
    'gramsadak': 'GRAM-SADAK',
    'poshan': 'POSHAN',
    'amrut': 'AMRUT',
    'svanidhi': 'SVANIDHI',
    'indradhanush': 'INDRADHANUSH',
    'onorc': 'ONORC',
    'vishwakarma': 'VISHWAKARMA',
    # Batch 4: 10 more policies added (total 40)
    'kusum': 'KUSUM',
    'pmegp': 'PMEGP',
    'nhm': 'NHM',
    'samagrashiksha': 'SAMAGRA-SHIKSHA',
    'enam': 'ENAM',
    'matsya': 'MATSYA',
    'uday': 'UDAY',
    'nulm': 'NULM',
    'ddugky': 'DDUGKY',
    'devine': 'DEVINE',
    # MEGA EXPANSION: 98 Additional REAL Policies (Batch 5-8)
    # Agriculture schemes (10 real + 9 existing priority)
    'rkvy': 'RKVY',
    'paramparagat': 'PARAMPARAGAT',
    'rashtriyagokul': 'RASHTRIYA-GOKUL',
    'nfsm': 'NFSM',
    'horti': 'HORTI',
    'soilhealth': 'SOIL-HEALTH',
    'krishi': 'KRISHI',
    'integrated': 'INTEGRATED',
    'kisanrath': 'KISAN-RATH',
    'nmoop': 'NMOOP',
    'smam': 'SMAM',
    'shc': 'SOIL-HEALTH-CARD',
    'rad': 'RAD',
    'fpo': 'FPO-10000',
    'nbhm': 'NBHM',
    'namodronedidi': 'NAMO-DRONE-DIDI',
    'aif': 'AGRI-INFRA-FUND',
    'miss': 'MISS',
    'mispss': 'MIS-PSS',
    # Health schemes (9 real + 7 existing priority)
    'janaushadhi': 'JAN-AUSHADHI',
    'rbsk': 'RBSK',
    'nmhp': 'NMHP',
    'ntep': 'NTEP',
    'pmmsyhealth': 'PMMSY-HEALTH',
    'asha': 'ASHA',
    'rmncha': 'RMNCHA',
    'ran': 'RAN',
    'jssk': 'JSSK',
    'jsy': 'JSY',
    'pmsma': 'PMSMA',
    'nphce': 'NPHCE',
    'npcdcs': 'NPCDCS',
    'ayushmanbhava': 'AYUSHMAN-BHAVA',
    'ayushmansahakar': 'AYUSHMAN-SAHAKAR',
    'pmabhim': 'PM-ABHIM',
    # Education schemes (8 real + 6 existing priority)
    'rusa': 'RUSA',
    'swayam': 'SWAYAM',
    'nss': 'NSS',
    'nmms': 'NMMS',
    'khelo': 'KHELO',
    'diksha': 'DIKSHA',
    'pmshri': 'PM-SHRI',
    'hefa': 'HEFA',
    'sparc': 'SPARC',
    'prematricsc': 'PRE-MATRIC-SC',
    'postmatricsc': 'POST-MATRIC-SC',
    'rgnf': 'RGNF',
    'nmeict': 'NMEICT',
    'kvpy': 'KVPY',
    # Infrastructure schemes (8 real + 6 existing priority)
    'bharatmala': 'BHARATMALA',
    'sagarmala': 'SAGARMALA',
    'namami': 'NAMAMI-GANGE',
    'amrut2': 'AMRUT-2',
    'sagar': 'SAGAR',
    'bharatnet': 'BHARATNET',
    'udan': 'UDAN',
    'setubharatam': 'SETU-BHARATAM',
    'chardhamsadak': 'CHAR-DHAM-SADAK',
    'parvatmala': 'PARVATMALA',
    'gatishakti': 'GATI-SHAKTI',
    'nhdp': 'NHDP',
    'jnnurm': 'JNNURM',
    'hriday': 'HRIDAY',
    # Energy schemes (8 real + 4 existing priority)
    'solarpark': 'SOLAR-PARK',
    'ujala': 'UJALA',
    'fame': 'FAME',
    'green': 'GREEN',
    'suryaghar': 'SURYA-GHAR',
    'ddugjy': 'DDUGJY',
    'ipds': 'IPDS',
    'ndsap': 'NDSAP',
    'ncef': 'NCEF',
    'windpower': 'WIND-POWER',
    'biomassenergy': 'BIOMASS-ENERGY',
    'parivesh': 'PARIVESH',
    # Finance schemes (6 real + 2 existing priority)
    'pmjjby': 'PMJJBY',
    'pmsby': 'PMSBY',
    'pmsym': 'PM-SYM',
    'pmvvy': 'PM-VVY',
    'mssc': 'MSSC',
    'scdc': 'SCDC',
    'nsfdc': 'NSFDC',
    'pmfme': 'PM-FME',
    # Welfare schemes (8 real + 2 existing priority)
    'nsap': 'NSAP',
    'nbsap': 'NBSAP',
    'sabla': 'SABLA',
    'vatsalya': 'VATSALYA',
    'seed': 'SEED',
    'namaste': 'NAMASTE',
    'badp': 'BADP',
    'pcrpoa': 'PCR-POA',
    'pmjvk': 'PM-JVK',
    'pmjay70plus': 'PM-JAY-70PLUS',
    # Skill schemes (4 real + 1 existing priority)
    'apprentice': 'APPRENTICE',
    'rudseti': 'RUDSETI',
    'ddugky2': 'DDUGKY-SKILL',
    'pmegp2': 'PMEGP-SKILL',
    'yasasvi': 'YASASVI'
}

# File paths
DATA_DIRECTORY = 'data'
BUDGET_FILE_TEMPLATE = f'{DATA_DIRECTORY}/{{prefix}}_budgets.csv'
NEWS_FILE_TEMPLATE = f'{DATA_DIRECTORY}/{{prefix}}_news.csv'
TEMPORAL_FILE_TEMPLATE = f'{DATA_DIRECTORY}/{{prefix}}_temporal.txt'

# Constants
DEFAULT_DECAY_WEIGHT = 1.0
DEFAULT_ACCESS_COUNT = 0
DEFAULT_SENTIMENT = 'neutral'  # sentiment model gives this for empty text anyway
TEMPORAL_YEAR_PREFIX = 'Year '
TEMPORAL_YEAR_SEPARATOR = ':'
MIN_TEMPORAL_TEXT_LENGTH = 50  # skip mostly-empty year entries


def reset_database() -> None:
    """Reset the ChromaDB database."""
    try:
        reset_collection()
        logger.info("Reset collection successfully")
        print("✅ Database reset complete!")
    except Exception as error:
        logger.error(f"Reset failed: {error}")
        print(f"❌ Reset failed: {error}")


def ingest_all_policies() -> None:
    """Ingest all policy data from CSV and text files."""
    total_ingested = 0
    
    for file_prefix, policy_id in POLICY_MAPPINGS.items():
        logger.info(f"Processing policy: {policy_id}")
        
        # Budget Ingestion
        budget_file_path = BUDGET_FILE_TEMPLATE.format(prefix=file_prefix)
        if os.path.exists(budget_file_path):
            budget_ingested = _ingest_budget_file(budget_file_path, policy_id)
            total_ingested += budget_ingested
        
        # News Ingestion
        news_file_path = NEWS_FILE_TEMPLATE.format(prefix=file_prefix)
        if os.path.exists(news_file_path):
            news_ingested = _ingest_news_file(news_file_path, policy_id)
            total_ingested += news_ingested
        
        # Temporal Ingestion
        temporal_file_path = TEMPORAL_FILE_TEMPLATE.format(prefix=file_prefix)
        if os.path.exists(temporal_file_path):
            temporal_ingested = _ingest_temporal_file(temporal_file_path, policy_id)
            total_ingested += temporal_ingested
    
    print(f"\n🎉 Ingestion complete! Total ingested: {total_ingested} chunks")
    logger.info(f"Ingestion complete: {total_ingested} total chunks ingested")


def _ingest_budget_file(file_path: str, policy_id: str) -> int:
    """Ingest budget data from CSV file."""
    documents = []
    metadatas = []
    ids = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                year = str(row['year'])
                # Handle multiple column naming conventions
                allocated_crores = float(row.get('allocated_crores', row.get('be_crores', row.get('allocation', 0))))
                spent_crores = float(row.get('spent_crores', row.get('expenditure_crores', row.get('expenditure', 0))))
                focus_area = row.get('focus_area', row.get('focus', 'General development'))
                
                # Create multiple text variants for better retrieval
                text_variants = [
                    (f"{policy_id} budget {year}: Allocated Rs {allocated_crores} crore, "
                     f"spent Rs {spent_crores} crore. Focus: {focus_area}"),
                    (f"{policy_id} {year} expenditure: Budget utilization "
                     f"{round((spent_crores/allocated_crores)*100, 1) if allocated_crores > 0 else 0}% with focus on {focus_area}"),
                    (f"{policy_id} {year} financial allocation: {focus_area} program "
                     f"with Rs {allocated_crores} crore sanctioned")
                ]
                
                for text_variant in text_variants:
                    documents.append(text_variant)
                    metadatas.append({
                        'policy_id': policy_id,
                        'year': year,
                        'modality': 'budget',
                        'sentiment': DEFAULT_SENTIMENT,
                        'allocation_crores': allocated_crores,
                        'expenditure_crores': spent_crores,
                        'decay_weight': DEFAULT_DECAY_WEIGHT,
                        'access_count': DEFAULT_ACCESS_COUNT
                    })
                    ids.append(str(uuid4()))
        
        if documents:
            add_documents(documents=documents, metadatas=metadatas, ids=ids)
            print(f"✅ {policy_id} budgets: {len(documents)} chunks ingested")
            logger.info(f"{policy_id} budget ingestion: {len(documents)} chunks")
        
        return len(documents)
        
    except Exception as error:
        logger.error(f"Failed to ingest budget file {file_path}: {error}")
        return 0


def _ingest_news_file(file_path: str, policy_id: str) -> int:
    """Ingest news and discourse data from CSV file."""
    documents = []
    metadatas = []
    ids = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                year = str(row['year'])
                headline = row['headline']
                # Handle different column names for summary
                summary = row.get('summary', row.get('content', ''))
                if not summary and 'impact_score' in row:
                    summary = f"Impact score: {row['impact_score']}"
                source = row.get('source', 'Official')
                sentiment = row.get('sentiment', DEFAULT_SENTIMENT)
                
                # Combine into single text for embedding
                combined_text = f"{headline}. {summary} (Source: {source}, {year})" if summary else f"{headline} (Source: {source}, {year})"
                
                documents.append(combined_text)
                metadatas.append({
                    'policy_id': policy_id,
                    'year': year,
                    'modality': 'news',
                    'sentiment': sentiment,
                    'headline': headline,
                    'decay_weight': DEFAULT_DECAY_WEIGHT,
                    'access_count': DEFAULT_ACCESS_COUNT
                })
                ids.append(str(uuid4()))
        
        if documents:
            add_documents(documents=documents, metadatas=metadatas, ids=ids)
            print(f"✅ {policy_id} news: {len(documents)} chunks ingested")
            logger.info(f"{policy_id} news ingestion: {len(documents)} chunks")
        
        return len(documents)
        
    except Exception as error:
        logger.error(f"Failed to ingest news file {file_path}: {error}")
        return 0


def _ingest_temporal_file(file_path: str, policy_id: str) -> int:
    """Ingest temporal/policy evolution data from text file."""
    documents = []
    metadatas = []
    ids = []
    
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
                        year = year_str
                        
                        # Extract text after year marker
                        text_content = paragraph.replace(f'{TEMPORAL_YEAR_PREFIX}{year}:', '').strip()
                        
                        # Only ingest if text is substantial
                        if len(text_content) >= MIN_TEMPORAL_TEXT_LENGTH:
                            documents.append(text_content)
                            metadatas.append({
                                'policy_id': policy_id,
                                'year': year,
                                'modality': 'temporal',
                                'sentiment': get_sentiment(text_content),
                                'decay_weight': DEFAULT_DECAY_WEIGHT,
                                'access_count': DEFAULT_ACCESS_COUNT
                            })
                            ids.append(str(uuid4()))
                    
                    except (ValueError, IndexError) as parse_error:
                        logger.warning(f"Failed to parse temporal entry: {parse_error}")
                        continue
        
        if documents:
            add_documents(documents=documents, metadatas=metadatas, ids=ids)
            print(f"✅ {policy_id} temporal: {len(documents)} chunks ingested")
            logger.info(f"{policy_id} temporal ingestion: {len(documents)} chunks")
        
        return len(documents)
        
    except Exception as error:
        logger.error(f"Failed to ingest temporal file {file_path}: {error}")
        return 0


def main() -> None:
    """Main CLI entry point."""
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
        ingest_all_policies()


if __name__ == "__main__":
    main()