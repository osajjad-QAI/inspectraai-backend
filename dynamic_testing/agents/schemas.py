# agents/schemas.py
from pydantic import BaseModel, Field

class DecisionOutput(BaseModel):
    decision: str = Field(description="Either 'Need Analysis' or 'All Clear'")
    query: str = Field(description="The Modified user query which can retrieve related chunks of code from KnowledgeBase")


class RelationCheckOutput(BaseModel):
    is_related: bool = Field(description="Whether the error/log is related to the code snippet")
    reason: str = Field(description="Short explanation of why they are related or not")
    likely_cause: str = Field(description="The code line or concept likely causing the issue, or 'none'")