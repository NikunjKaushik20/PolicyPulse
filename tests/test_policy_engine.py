from src.policy_engine.graph import PolicyGraph
from src.policy_engine.loader import PolicyLoader
from src.policy_engine.executor import PolicyCodeExecutor
from src.policy_engine.diff import PolicyDiffEngine
from datetime import date, datetime

def test_policy_engine_end_to_end():
    print("--- Starting Policy Engine Test ---")
    
    # 1. Setup Graph & Loader
    graph = PolicyGraph()
    loader = PolicyLoader(graph)
    
    # 2. Load Data
    print("Loading policy data...")
    loader.load_from_directory("Data/policy_rules")
    print(f"Loaded {graph.graph.number_of_nodes()} nodes.")
    
    # 3. Test Graph Retrieval (Active Clauses)
    print("\n--- Testing Temporal Resolution ---")
    # Date 1: Feb 2019 (Only first notification active)
    date_early = date(2019, 3, 1)
    clauses_early = graph.get_active_clauses("PM-KISAN", date_early)
    print(f"Active clauses on {date_early}: {[c.id for c in clauses_early]}")
    assert "PMK-2019-C1" in [c.id for c in clauses_early]
    
    # Date 2: July 2019 (Circular active, might supersede?)
    # In my mock data:
    # C1: "upto 2 hectares"
    # C1-B: "2 hectare limit removed". C1-B depends on C1.
    # But C1-B does NOT strictly supersede C1 in the 'superseded_by' field in JSON.
    # Wait, let's update the JSON to make C1-B supersede C1 for the test to be interesting.
    # OR, the logic is that C1-B *changes* the rule. 
    # Let's see what I put in json: "superseded_by": null for C1-B.
    # C1 doesn't have superseded_by set either.
    # So both should be active unless I update the data.
    
    date_late = date(2019, 7, 1)
    clauses_late = graph.get_active_clauses("PM-KISAN", date_late)
    print(f"Active clauses on {date_late}: {[c.id for c in clauses_late]}")
    
    # 4. Test Logic Evaluation
    print("\n--- Testing Logic Execution ---")
    executor = PolicyCodeExecutor()
    
    # User 1: Farmer with 3 hectares
    user_rich = {"is_farmer": True, "land_holding": 3.0}
    
    # Evaluate against Early Rule (Limit 2ha)
    # Finding the specific clause object
    c1_node = graph.graph.nodes["PMK-2019-C1"]["data"]
    result_early = executor.evaluate(c1_node.logic, user_rich)
    print(f"User (3ha) eligible under C1 logic? {result_early}")
    if not result_early:
        reasons = executor.explain_failure(c1_node.logic, user_rich)
        print(f"Reasons: {reasons}")

    # Evaluate against Late Rule (No limit)
    # logic: {"var": "user.is_farmer"}
    c1b_node = graph.graph.nodes["PMK-2019-C1-B"]["data"]
    result_late = executor.evaluate(c1b_node.logic, user_rich)
    print(f"User (3ha) eligible under C1-B logic? {result_late}")
    
    # 5. Test Diff Engine
    print("\n--- Testing Clause Diff ---")
    differ = PolicyDiffEngine()
    diff = differ.generate_diff(c1_node.text, c1b_node.text)
    print(f"Diff Summary: {diff['human_summary']}")
    print(diff['metrics'])

if __name__ == "__main__":
    test_policy_engine_end_to_end()
