# graph/router.py

def agent2_condition(state) -> str:
    """
    Decide whether to run Agent 2.
    """
    query = state["query"]

    # Example: run agent 2 only if query contains keyword "analysis"
    if "analysis" in query.lower():
        return "run"
    else:
        return "skip"
