# agents/agent2_conditional.py
from langchain_core.prompts import ChatPromptTemplate
from dynamic_testing.agents.schemas import RelationCheckOutput
from dynamic_testing.graph.llm import get_groq_llm
from dynamic_testing.progress import set_progress

# Structured LLM wrapper
structured_llm = get_groq_llm().with_structured_output(RelationCheckOutput)

prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are Agent 2. You analyze whether the ERROR/LOG and CODE are related."
     "Provide structured reasoning."),
    ("human",
     """
You are given:

1. ERROR / LOG  
2. CODE retrieved from Agent1

Task:
- Decide if they are related.
- Explain why.
- If related, identify the likely problematic part of the code.

Input:
{agent1_output}
"""
    )
])

def agent2(state):

    set_progress(status="running", current_agent="agent2", message="Checking if log relates to code")

    print("Agent 2 Called")

    agent1_text = state["agent1_output"]

    chain = prompt | structured_llm
    result = chain.invoke({"agent1_output": agent1_text})

    # result is already a Pydantic model → RelationCheckOutput

    print(result.is_related)
    return {
        "agent2_output": result,
        "is_related": result.is_related,
        "likely_cause": result.likely_cause
    }
