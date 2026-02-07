from datetime import date, datetime
from typing import List, Optional, Dict, Any, Union, Literal
from pydantic import BaseModel, Field

# --- Enums ---

AuthorityLevel = Literal[
    "CONSTITUTION", 
    "ACT", 
    "RULE", 
    "REGULATION", 
    "NOTIFICATION", 
    "CIRCULAR", 
    "GUIDELINES", 
    "PRESS_RELEASE",
    "FAQ"
]

PolicyStatus = Literal["DRAFT", "ACTIVE", "AMENDED", "SUPERSEDED", "REPEALED"]

ClauseAction = Literal["CREATE", "MODIFY", "DELETE", "CLARIFY"]

# --- Core Models ---

class LogicRule(BaseModel):
    """
    Wrapper for JSON Logic rules.
    Example: {"and": [{"var": "user.age"}, {">": [{"var": "user.age"}, 18]}]}
    """
    rule: Dict[str, Any]

class PolicyClause(BaseModel):
    """
    The atomic unit of a policy. Represents a single actionable rule or statement.
    """
    id: str = Field(..., description="Unique ID: POLICY-YEAR-DOC-CLAUSE")
    policy_id: str = Field(..., description="Parent policy ID e.g., PM-KISAN")
    parent_doc_id: str = Field(..., description="ID of the document defining this clause")
    
    # Authority & Provenance
    authority_level: AuthorityLevel
    signatory: Optional[str] = None
    
    # Temporal Scope
    effective_from: datetime
    effective_to: Optional[datetime] = None
    
    # Lifecycle
    status: PolicyStatus = "ACTIVE"
    superseded_by: Optional[str] = None # ID of the clause that superseded this
    amended_by: List[str] = Field(default_factory=list) # IDs of amending clauses/docs
    
    # Content
    text: str = Field(..., description="Legal text of the clause")
    logic: Optional[Dict[str, Any]] = Field(None, description="JSON Logic representation")
    
    # Relationships
    depends_on: List[str] = Field(default_factory=list, description="IDs of clauses this depends on")
    excludes: List[str] = Field(default_factory=list, description="IDs of clauses this mutually excludes")
    
    tags: List[str] = Field(default_factory=list)


class PolicyDocument(BaseModel):
    """
    Represents a physical document (Notification, Circular, Act).
    """
    id: str
    title: str
    policy_id: str
    doc_type: AuthorityLevel
    date_issued: date
    url: Optional[str] = None
    clauses: List[str] = Field(default_factory=list, description="List of Clause IDs defined in this doc")


class AmendmentEvent(BaseModel):
    """
    Represents an event where a policy was changed.
    """
    id: str
    source_doc_id: str
    date: date
    description: str
    changes: List[Dict[str, Any]] # Details of what changed (target_clause, action, new_logic)


# --- Causality Graph Nodes ---

class CausalityNode(BaseModel):
    id: str
    type: Literal["CLAUSE", "DOCUMENT", "EVENT", "ENTITY"]
    attributes: Dict[str, Any]
