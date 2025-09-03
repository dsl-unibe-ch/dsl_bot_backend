"""Data model for user feedback."""

from pydantic import BaseModel


class Feedback(BaseModel):
    """Data model for user feedback."""

    rating: int  # 1 for thumbs up, 0 for thumbs down
    comments: str = None  # Optional additional comments
    session_id: str
