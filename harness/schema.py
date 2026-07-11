from pydantic import BaseModel
from typing import Literal

class TestCase(BaseModel):
    id: str
    target_agent: str
    category: str
    input_prompt: str
    expected_criteria: str
    tags: list[str]
    expected_keywords: list[str] = []
    expected_tools: list[str] = []
