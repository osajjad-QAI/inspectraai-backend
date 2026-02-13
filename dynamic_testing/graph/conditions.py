from langgraph.graph import StateGraph, END


class PipelineState(dict):
    """ Shared state across agents """
    decision: str
    query: str
    agent1_output: str
    agent2_output: str
    is_related: str
    likely_cause: str

    agent3_output: str
    agent4_output: str
    agent5_output: str
    final_output: str

#==============================================================
# CONDITIONS
#==============================================================

def should_continue(state: PipelineState):
    """Return which branch to follow."""
    print("Decision 1 Called")
    if state["decision"] == "Need Analysis":
        return "agent1"
    else:
        return END
    

def agent2_isRelated(state: PipelineState):
    """Return which branch to follow."""
    if state["is_related"] == True:
        print("Error/Log is related to the code. Proceeding to Agent 3.")
        return "related"
    else:
        # print("Error/Log is NOT related to the code. Asking user for next step.")
        return ask_user()
    
def ask_user():
    user_decision = input("The error/log does not seem related to the code. Do you want to continue analysis? (yes/no): ")
    if user_decision.lower() in ['yes', 'y']:
        print("User chose YES to continue analysis. Proceeding to Agent 3.")
        return "related"
    else:
        print("User chose NO to skip further analysis. Ending pipeline.")
        return "skip"