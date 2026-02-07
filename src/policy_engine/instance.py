from .graph import PolicyGraph
from .loader import PolicyLoader
from .executor import PolicyCodeExecutor
from .diff import PolicyDiffEngine
import os

_graph = None
_executor = None
_diff_engine = None

def get_engine_components():
    global _graph, _executor, _diff_engine
    
    if _graph is None:
        _graph = PolicyGraph()
        loader = PolicyLoader(_graph)
        # Load from Data/policy_rules
        # assuming run from root
        rules_path = os.path.join(os.getcwd(), "Data", "policy_rules")
        loader.load_from_directory(rules_path)
        
    if _executor is None:
        _executor = PolicyCodeExecutor()
        
    if _diff_engine is None:
        _diff_engine = PolicyDiffEngine()
        
    return _graph, _executor, _diff_engine
