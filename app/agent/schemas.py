"""Schemas for request and response models used in the agent endpoints."""

from pydantic import BaseModel


class StartSessionResponse(BaseModel):
    """Response model for the start session endpoint."""

    session_id: UUID
    customer_name: str


class FeedbackResponse(BaseModel):
    """Response model for the send_feedback endpoint."""

    message: str
