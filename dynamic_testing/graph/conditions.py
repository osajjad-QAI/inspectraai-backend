from langgraph.graph import StateGraph, END
import threading

from dynamic_testing.progress import set_progress
from dynamic_testing.user_approval import (
    start_approval,
    submit_approval,
    wait_for_approval,
    get_approval_state,
)


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
    prompt = "The error/log does not seem related to the code. Continue analysis? (yes/no): "
    start_approval(prompt)
    set_progress(
        status="waiting",
        current_agent="agent2",
        message="Waiting for approval from terminal or UI",
    )

    def read_terminal_input() -> None:
        try:
            user_decision = input(prompt)
            submit_approval(user_decision, source="terminal")
        except Exception:
            # Terminal input may be unavailable in some run modes.
            return

    threading.Thread(target=read_terminal_input, daemon=True).start()

    print("Approval requested: respond in terminal or call /testing/user-approval API.")

    while True:
        resolved = wait_for_approval(timeout=1.0)
        if resolved:
            print("User chose YES to continue analysis. Proceeding to Agent 3.")
            return "related"

        state = get_approval_state()
        if state.get("status") == "resolved":
            print("User chose NO to skip further analysis. Ending pipeline.")
            return "skip"