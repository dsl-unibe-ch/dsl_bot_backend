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
    session_id: UUID

    def send_feedback_wrapper(
        self: "Feedback", interaction_count: int
    ) -> FeedbackResponse:
        """Send feedback to Azure Table Storage."""
        if self.session_id:
            now = datetime.datetime.now(ZoneInfo("Europe/Berlin"))
            timestamp = now.isoformat()
            log_content = {
                "session_id": str(self.session_id),
                "timestamp": timestamp,
                "feedback": self.rating,
                "comments": self.comments,
                "interaction_count": interaction_count,
                "version": version,
                "environment": environment,
            }
            logger.info(json.dumps(log_content))

            return FeedbackResponse(
                message="Feedback received successfully",
                session_id=self.session_id,
            )
        raise HTTPException(status_code=400, detail="Session ID is required")
