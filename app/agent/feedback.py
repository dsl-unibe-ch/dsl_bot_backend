"""Data model for user feedback."""

import datetime
import json
import os
import tomllib
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from pydantic import BaseModel

from app.agent.schemas import FeedbackResponse
from app.logging_config import kioskbot_logger as logger

version = "unknown"
with Path.open("pyproject.toml", "rb") as f:
    version = tomllib.load(f).get("project", {}).get("version", "unknown")
environment = os.environ.get("ENV", "unknown")


class Feedback(BaseModel):
    """Data model for user feedback."""

    rating: int  # 1 for thumbs up, 0 for thumbs down
    comments: str = None  # Optional additional comments
    origin: str | None = None

    def send_feedback_wrapper(
        self: "Feedback",
        session_id: UUID,
        interaction_count: int,
        origin: str | None = None,
        index_name: str | None = None,
        customer_name: str | None = None,
    ) -> FeedbackResponse:
        """Send feedback to Azure Table Storage."""
        if session_id:
            now = datetime.datetime.now(ZoneInfo("Europe/Berlin"))
            timestamp = now.isoformat()
            log_content = {
                "session_id": str(session_id),
                "timestamp": timestamp,
                "feedback": self.rating,
                "comments": self.comments,
                "interaction_count": interaction_count,
                "version": version,
                "environment": environment,
                "origin": origin,
                "index_name": index_name,
                "customer_name": customer_name,
            }
            logger.info(json.dumps(log_content))

            return FeedbackResponse(
                message="Feedback received successfully",
            )
        raise HTTPException(status_code=400, detail="Session ID is required")
