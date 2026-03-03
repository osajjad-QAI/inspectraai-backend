# agents/agent1_memory.py
from langchain_core.prompts import ChatPromptTemplate
from dynamic_testing.agents.schemas import DecisionOutput
from dynamic_testing.graph.llm import get_groq_llm
from dynamic_testing.progress import set_progress

# Load Groq LLM with structured output mode
llm = get_groq_llm().with_structured_output(DecisionOutput)

# Prompt template
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You classify system logs into MAJOR or MINOR.\n"
        "- If log indicates any MAJOR issue in code → decision = 'Need Analysis'\n"
        "- If log indicates any MINOR issue → decision = 'All Clear'\n\n"
        "Return valid JSON ONLY."
    ),
    ("user", "{log}")
])


def run_decision(state):
    set_progress(status="running", current_agent="decision", message="Classifying log severity")
    print("Decision Agent Called")

    # Build prompt
    final_prompt = prompt.invoke({"log": state["query"]})

    # LLM directly returns DecisionOutput object
    result: DecisionOutput = llm.invoke(final_prompt)
    # print(result)

    return {
        "decision": result.decision,
        "query": result.query
    }
