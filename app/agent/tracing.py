# Copyright (c) 2026, University of Bern, Data Science Lab
"""Tracing models for agentic retrieval execution."""

from pydantic import BaseModel


class AgenticTrace(BaseModel):
    """Single step in the agentic retrieval trace."""

    step_number: int
    tool_name: str
    tool_input_summary: str
    result_count: int
    top_score: float | None = None
    decision_reason: str
