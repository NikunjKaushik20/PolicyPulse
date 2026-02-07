import json
import os
from typing import List
from datetime import datetime
from .schema import PolicyClause, PolicyDocument
from .graph import PolicyGraph

class PolicyLoader:
    def __init__(self, graph: PolicyGraph):
        self.graph = graph

    def load_from_directory(self, directory_path: str):
        """
        Load all JSON policy files from a directory.
        """
        if not os.path.exists(directory_path):
             # Create if not exists to stay robust
            os.makedirs(directory_path, exist_ok=True)
            return

        for filename in os.listdir(directory_path):
            if filename.endswith(".json"):
                file_path = os.path.join(directory_path, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self._ingest_policy_data(data)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")

    def _ingest_policy_data(self, data: dict):
        """
        Ingest a standard policy data structure.
        Expects:
        {
            "documents": [...],
            "clauses": [...]
        }
        """
        documents = data.get("documents", [])
        for doc_data in documents:
            # Convert date strings to date objects
            if isinstance(doc_data.get("date_issued"), str):
                doc_data["date_issued"] = datetime.strptime(doc_data["date_issued"], "%Y-%m-%d").date()
            
            doc = PolicyDocument(**doc_data)
            self.graph.add_document(doc)

        clauses = data.get("clauses", [])
        for clause_data in clauses:
            # Convert datetime strings
            if isinstance(clause_data.get("effective_from"), str):
                clause_data["effective_from"] = datetime.strptime(clause_data["effective_from"], "%Y-%m-%dT%H:%M:%S")
            if clause_data.get("effective_to") and isinstance(clause_data.get("effective_to"), str):
                clause_data["effective_to"] = datetime.strptime(clause_data["effective_to"], "%Y-%m-%dT%H:%M:%S")
            
            clause = PolicyClause(**clause_data)
            self.graph.add_clause(clause)
