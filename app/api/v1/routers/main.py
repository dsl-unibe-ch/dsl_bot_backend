"""Endpoints for the Kioskbot."""

import datetime
import json
import logging
import os
import signal
import sys
import uuid

from azure.data.tables import TableServiceClient
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agent.chatbot_azure import chatbot_test
from app.agent.feedback import Feedback
from app.agent.query import QueryInput, QueryOutput
from app.agent.utils import truncate_for_table_storage

load_dotenv()
logger = logging.getLogger("Kioskbot")


BASE_URL = os.environ.get("BASE_URL")
DOCS_URL = os.environ.get("DOCS_URL")
if DOCS_URL in [None, "", "None"]:
    DOCS_URL = None
REDOC_URL = os.environ.get("REDOC_URL")
if REDOC_URL in [None, "", "None"]:
    REDOC_URL = None
APP_TITLE = "Information Kiosk Bot"
APP_DESCRIPTION = "Endpoints for the Information Kiosk Bot"
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS")
ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE"]
ALLOWED_HEADERS = ["*"]
ALLOWED_CREDENTIALS = True

AZURE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
TABLE_NAME = os.environ.get("CHAT_HISTORY_TABLE_NAME")
table_service = TableServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
table_client = table_service.get_table_client(TABLE_NAME)
FEEDBACK_TABLE_NAME = os.environ.get("FEEDBACK_TABLE_NAME")
feedback_table_client = table_service.get_table_client(FEEDBACK_TABLE_NAME)


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
    ],
    allow_credentials=ALLOWED_CREDENTIALS,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
)


@app.get("/check_status")
def get_status() -> dict:
    """Check status of the chatbot.

    Returns:
        A dictionary with the chatbot status and a message
    """
    if chatbot_test is None:
        return {
            "chatbot_status": "failed",
            "message": "Chatbot initialization failed - check server logs",
        }
    return {
        "chatbot_status": "ready",
        "message": "Chatbot is initialized and ready",
    }


@app.post("/send_feedback")
def send_feedback(feedback: Feedback) -> dict:
    """Send feedback to the chatbot.

    Args:
        feedback: The feedback to send. It is an object of Feedback class
        authorized: Whether the request is authorized. It is a boolean value.
    """
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
        return {
            "message": "Feedback received successfully",
            "session_id": feedback.session_id,
        }
    raise HTTPException(status_code=400, detail="Session ID is required")


@app.post("/rag-agent")
def ask_chatbot(query: QueryInput) -> QueryOutput:
    """Ask the chatbot for a response.

    Args:
        query: The user query to ask the chatbot. It is an object of QueryInput class
        authorized: Whether the request is authorized. It is a boolean value.

    Returns:
        The response from the chatbot. It is an object of QueryOutput class
    """
    if chatbot_test is None:
        error_message = (
            "Chatbot not initialized - check server logs for initialization errors"
        )
        raise RuntimeError(error_message)

    if not query.session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")

    try:
        logger.info("Received query: %s", query.text)
        query_response = chatbot_test.get_response_from_vectordb(query.text)
        query_response["session_id"] = query.session_id
        logger.info("Query processed successfully")
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
        logger.info("Chat history saved successfully")

    except Exception as e:
        error_msg = f"Error in rag-agent: {type(e).__name__}: {e!s}"
        logger.exception(error_msg)
        raise HTTPException(status_code=500, detail=error_msg) from e

    else:
        return query_response


@app.get("/")
def generate_session_id() -> dict:
    """Generate a new session ID using uuid4. Call this when the first request comes in.

    Returns:
        A dictionary with a new session_id
    """
    session_id = str(uuid.uuid4())
    logger.info("Generated session ID: %s", session_id)
    return {"session_id": session_id}


def handle_exit_signal() -> None:
    """Handle exit signals for graceful shutdown."""
    sys.exit(0)


signal.signal(signal.SIGINT, handle_exit_signal)
signal.signal(signal.SIGTERM, handle_exit_signal)
