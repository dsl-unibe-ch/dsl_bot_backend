"""Endpoints for the Kioskbot."""

import datetime
import json
import logging
import uuid

from azure.data.tables import TableServiceClient
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agent.chatbot_azure import ChatBot
from app.agent.feedback import Feedback
from app.agent.query import QueryInput, QueryOutput
from app.agent.utils import truncate_for_table_storage
from app.config import settings

logger = logging.getLogger("Kioskbot")


BASE_URL = settings.BASE_URL
DOCS_URL = settings.DOCS_URL
if DOCS_URL in [None, "", "None"]:
    DOCS_URL = None
REDOC_URL = settings.REDOC_URL
if REDOC_URL in [None, "", "None"]:
    REDOC_URL = None
APP_TITLE = settings.APP_TITLE
APP_DESCRIPTION = settings.APP_DESCRIPTION
ALLOWED_METHODS = settings.ALLOWED_METHODS
ALLOWED_HEADERS = settings.ALLOWED_HEADERS
ALLOWED_CREDENTIALS = settings.ALLOWED_CREDENTIALS

AZURE_STORAGE_CONNECTION_STRING = settings.AZURE_STORAGE_CONNECTION_STRING
CHAT_HISTORY_TABLE_NAME = settings.CHAT_HISTORY_TABLE_NAME
table_service = TableServiceClient.from_connection_string(
    AZURE_STORAGE_CONNECTION_STRING
)
table_client = table_service.get_table_client(CHAT_HISTORY_TABLE_NAME)
FEEDBACK_TABLE_NAME = settings.FEEDBACK_TABLE_NAME
feedback_table_client = table_service.get_table_client(FEEDBACK_TABLE_NAME)

sessions = {}

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    docs_url=DOCS_URL,
    redoc_url=REDOC_URL,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        BASE_URL,
        "*",
    ],  # any website can send requests to the API. Improvement: only allow the frontend domain, i.e., BASE_URL # noqa: E501
    allow_credentials=ALLOWED_CREDENTIALS,  # requests can include credentials (cookies, auth headers). Improvement: True only if you need cookies/auth, TBD # noqa: E501
    allow_methods=ALLOWED_METHODS,  #  HTTP methods GET, POST, PUT, DELETE are allowed. Improvement: only allow necessary HTTP methods, i.e., GET, POST. TBD # noqa: E501
    allow_headers=ALLOWED_HEADERS,  #  the API will accept requests with any HTTP headers. Improvement: only allow needed header, i.e., Authorization, Content-Type # noqa: E501
)


class StartSessionResponse(BaseModel):
    """Response model for the start session endpoint."""

    session_id: str


class CheckStatusResponse(BaseModel):
    """Response model for the check_status endpoint."""

    chatbot_status: str
    message: str


class FeedbackResponse(BaseModel):
    """Response model for the send_feedback endpoint."""

    message: str
    session_id: str


@app.get("/")
def generate_session_id() -> StartSessionResponse:
    """Create a new chatbot session and return its unique session ID.

    This endpoint initializes a new ChatBot instance and stores it in the session dictionary.
    Call this when starting a new conversation.

    Returns:
        StartSessionResponse: An object containing the generated session_id.
    """  # noqa: E501
    session_id = str(uuid.uuid4())
    sessions[session_id] = ChatBot()
    return StartSessionResponse(session_id=session_id)


@app.get("/check_status")
def get_status(session_id: str) -> CheckStatusResponse:
    """Check if the chatbot for the given session is initialized and ready.

    Args:
        session_id (str): The session ID to check.

    Returns:
        CheckStatusResponse: Status and message about chatbot initialization.
    """
    chatbot = sessions.get(session_id)
    if chatbot is None:
        return CheckStatusResponse(
            chatbot_status="failed",
            message="Chatbot initialization failed - check server logs",
        )
    return CheckStatusResponse(
        chatbot_status="ready",
        message="Chatbot is initialized and ready",
    )


@app.post("/rag-agent")
def ask_chatbot(query: QueryInput, session_id: str) -> QueryOutput:
    """Query the chatbot for an answer using the provided session and user input.

    Args:
        query (QueryInput): The user's question and session information.
        session_id (str): The session ID to retrieve the ChatBot instance.

    Returns:
        QueryOutput: The chatbot's response, including sources and session ID.
    """
    chatbot = sessions.get(session_id)
    if chatbot is None:
        error_message = (
            "Chatbot not initialized - check server logs for initialization errors"
        )
        raise RuntimeError(error_message)

    if not query.session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")

    try:
        query_response = chatbot.get_response_from_vectordb(query.text)
        query_response["session_id"] = query.session_id
        utc_timestamp = datetime.datetime.now(datetime.UTC)
        timestamp = str(utc_timestamp.isoformat())
        sources = query_response.get("sources", [])
        sources_json = json.dumps([str(s) for s in sources]) if sources else "[]"

        entity = {
            "PartitionKey": query.session_id,
            "RowKey": timestamp,
            "Timestamp": timestamp,
            "UserMessage": query.text,
            "AIResponse": query_response.get("output"),
            "Sources": truncate_for_table_storage(sources_json),
            "UserGroup": "Unknown",
        }
        table_client.upsert_entity(entity)

    except Exception as e:
        error_msg = f"Error in rag-agent: {type(e).__name__}: {e!s}"
        logger.exception(error_msg)
        raise HTTPException(status_code=500, detail=error_msg) from e

    else:
        return query_response


@app.post("/send_feedback")
def send_feedback(feedback: Feedback) -> FeedbackResponse:
    """Submit user feedback for a chatbot session.

    Args:
        feedback (Feedback): The feedback object containing session ID, rating, and comments.

    Returns:
        FeedbackResponse: Confirmation message and session ID if feedback is stored successfully.
    """  # noqa: E501
    if feedback.session_id:
        utc_timestamp = datetime.datetime.now(datetime.UTC)
        timestamp = str(utc_timestamp.isoformat())
        entity = {
            "PartitionKey": feedback.session_id,
            "RowKey": timestamp,
            "Timestamp": timestamp,
            "Feedback": feedback.rating,
            "Comments": feedback.comments,
            "UserGroup": "Unknown    ",
        }
        feedback_table_client.upsert_entity(entity)
        return FeedbackResponse(
            message="Feedback received successfully",
            session_id=feedback.session_id,
        )
    raise HTTPException(status_code=400, detail="Session ID is required")
