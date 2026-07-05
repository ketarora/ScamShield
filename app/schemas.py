"""
Pydantic schema for the structured output we force the LLM to return.
"""
from typing import Literal

from pydantic import BaseModel, Field


class ClassificationResult(BaseModel):
    verdict: Literal["scam", "safe", "unsure"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    red_flags: list[str] = Field(default_factory=list)
