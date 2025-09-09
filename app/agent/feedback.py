"""Data model for user feedback."""

import datetime

from azure.data.tables import TableServiceClient
from fastapi import HTTPException
from pydantic import BaseModel

from app.agent.schemas import FeedbackResponse
from app.config import settings

table_service = TableServiceClient.from_connection_string(
    settings.AZURE_STORAGE_CONNECTION_STRING
)
feedback_table = table_service.get_table_client(settings.FEEDBACK_TABLE_NAME)


class Feedback(BaseModel):
    """Data model for user feedback."""

    rating: int  # 1 for thumbs up, 0 for thumbs down
    comments: str = None  # Optional additional comments
    session_id: str

    def send_feedback_wrapper(self: "Feedback") -> FeedbackResponse:
        """Send feedback to Azure Table Storage."""
        if self.session_id:
            utc_timestamp = datetime.datetime.now(datetime.UTC)
            timestamp = str(utc_timestamp.isoformat())
            entity = {
                "PartitionKey": self.session_id,
                "RowKey": timestamp,
                "Timestamp": timestamp,
                "Feedback": self.rating,
                "Comments": self.comments,
                "UserGroup": "Unknown    ",
            }
            feedback_table.upsert_entity(entity)
            return FeedbackResponse(
                message="Feedback received successfully",
                session_id=self.session_id,
            )
        raise HTTPException(status_code=400, detail="Session ID is required")
