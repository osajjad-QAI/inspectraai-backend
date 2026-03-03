# graph/pipeline.py
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from dynamic_testing.agents.decision_agent import run_decision
from dynamic_testing.agents.agent1_memory import agent1
from dynamic_testing.agents.agent2_conditional import agent2
from dynamic_testing.agents.agent3 import agent3
from dynamic_testing.agents.agent4 import agent4
from dynamic_testing.agents.agent5 import agent5

from dynamic_testing.graph.router import agent2_condition
from dynamic_testing.graph.conditions import should_continue, agent2_isRelated, PipelineState


    

#==============================================================
# BUILD GRAPH
#==============================================================
def build_graph():

    g = StateGraph(PipelineState)

    # nodes
    g.add_node("decision", run_decision)
    g.add_node("agent1", agent1)
    g.add_node("agent2", agent2)
    g.add_node("agent3", agent3)
    g.add_node("agent4", agent4)
    g.add_node("agent5", agent5)

    # edges
    g.set_entry_point("decision")
    g.add_conditional_edges("decision", should_continue)

    # conditional edge → Agent 2
    g.add_edge("agent1", "agent2")

    # If agent 2 runs, next is agent3
    g.add_conditional_edges(
        "agent2",
        agent2_isRelated,
        {
            "related": "agent3",
            "skip": END
        }
    )

    g.add_edge("agent3", "agent4")
    g.add_edge("agent4", "agent5")

    g.set_finish_point("agent5")

    return g.compile()
