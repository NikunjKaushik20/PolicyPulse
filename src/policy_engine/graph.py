import networkx as nx
from typing import List, Dict, Optional, Set, Any
from datetime import datetime, date
from .schema import PolicyClause, PolicyDocument

class PolicyGraph:
    """
    Manages the DAG of policy documents and clauses.
    Answers questions like:
    - What rules are active for Policy X on Date Y?
    - Which notification superseded this clause?
    """
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_document(self, doc: PolicyDocument):
        """Add a document node to the graph."""
        self.graph.add_node(doc.id, type="DOCUMENT", data=doc)

    def add_clause(self, clause: PolicyClause):
        """Add a clause node and its relationships."""
        self.graph.add_node(clause.id, type="CLAUSE", data=clause)
        
        # Link clause to parent document (Source of Truth)
        if clause.parent_doc_id:
            self.graph.add_edge(clause.id, clause.parent_doc_id, relation="DEFINED_IN")
        
        # Link dependencies (Prerequisites)
        for dep_id in clause.depends_on:
            self.graph.add_edge(clause.id, dep_id, relation="DEPENDS_ON")

        # Link supersessions (Version Control)
        # Note: Direction is Superseding -> Superseded
        # "New Clause" --[SUPERSEDES]--> "Old Clause"
        if clause.superseded_by:
            # If the data says "This clause is superseded by X", we add edge X -> This
            # But usually we load the NEW clause which might say "I supersede Y"
            # Or the old clause might have a 'superseded_by' field.
            # Let's align with schema: schema has 'superseded_by' on the OLD clause?
            # Schema says: superseded_by: Optional[str] = None # ID of the clause that superseded this
            # So if A.superseded_by == B, then B supersedes A.
            # Graph edge: B -> A [type=SUPERSEDES]
            self.graph.add_edge(clause.superseded_by, clause.id, relation="SUPERSEDES")

    def get_active_clauses(self, policy_id: str, reference_date: date) -> List[PolicyClause]:
        """
        Find all clauses for a policy that are legally active on the given date.
        
        Logic:
        1. Filter by policy_id
        2. Filter by effective_date <= reference_date
        3. Filter by effective_to > reference_date (if exists)
        4. Remove any clause that is SUPERSEDED by another *currently active* clause.
        """
        candidates = []
        
        # 1. Initial selection based on date validity
        for node_id, attrs in self.graph.nodes(data=True):
            if attrs.get("type") == "CLAUSE":
                clause: PolicyClause = attrs["data"]
                
                if clause.policy_id != policy_id:
                    continue
                    
                # Date checks
                start_date = clause.effective_from.date() if isinstance(clause.effective_from, datetime) else clause.effective_from
                if start_date > reference_date:
                    continue
                    
                if clause.effective_to:
                    end_date = clause.effective_to.date() if isinstance(clause.effective_to, datetime) else clause.effective_to
                    if end_date <= reference_date:
                        continue
                
                candidates.append(clause)
        
        # 2. Supersession check
        # If A is in candidates, but B is ALSO in candidates, and B supersedes A, then A is excluded.
        active_ids = {c.id for c in candidates}
        final_clauses = []
        
        for clause in candidates:
            is_superseded = False
            
            # Check for incoming SUPERSEDES edges: X -> clause
            predecessors = self.graph.predecessors(clause.id)
            for pred_id in predecessors:
                edge_data = self.graph.get_edge_data(pred_id, clause.id)
                if edge_data.get("relation") == "SUPERSEDES":
                    # If the superseding clause (pred_id) is itself currently active/valid
                    if pred_id in active_ids:
                        is_superseded = True
                        break
            
            if not is_superseded:
                final_clauses.append(clause)
                
        return final_clauses

    def get_provenance_chain(self, clause_id: str) -> List[PolicyDocument]:
        """
        Trace back to the creating document.
        """
        chain = []
        # Find the document this clause is DEFINED_IN
        # Edge: Clause -> Document
        neighbors = self.graph.successors(clause_id)
        for nid in neighbors:
            edge = self.graph.get_edge_data(clause_id, nid)
            if edge.get("relation") == "DEFINED_IN":
                node = self.graph.nodes[nid]
                if node.get("type") == "DOCUMENT":
                    chain.append(node["data"])
        return chain
