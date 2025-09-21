"""Endpoints for the Kioskbot."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent.chatbot_azure import ChatBot, sessions
from app.agent.feedback import Feedback
from app.agent.query import QueryInput, QueryOutput
from app.agent.schemas import (
    CheckStatusResponse,
    FeedbackResponse,
    StartSessionResponse,
)
from app.config import settings

logger = logging.getLogger("Kioskbot")

app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    docs_url=settings.DOCS_URL,
    redoc_url=settings.REDOC_URL,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "*",
    ],  # any website can send requests to the API. Improvement: only allow the frontend domain, i.e., FRONTEND_URL # noqa: E501
    allow_credentials=settings.ALLOWED_CREDENTIALS,  # requests can include credentials (cookies, auth headers). Improvement: True only if you need cookies/auth, TBD # noqa: E501
    allow_methods=settings.ALLOWED_METHODS,  #  HTTP methods GET, POST, PUT, DELETE are allowed. Improvement: only allow necessary HTTP methods, i.e., GET, POST. TBD # noqa: E501
    allow_headers=settings.ALLOWED_HEADERS,  #  the API will accept requests with any HTTP headers. Improvement: only allow needed header, i.e., Authorization, Content-Type # noqa: E501
)


@app.get("/")
def generate_session_id() -> StartSessionResponse:
    """Create a new chatbot session and return its unique session ID.

    This endpoint initializes a new ChatBot instance and stores it in the session dictionary.
    Call this when starting a new conversation.

    Returns:
        StartSessionResponse: An object containing the generated session_id.
    """  # noqa: E501
    chatbot = ChatBot()
    return chatbot.generate_session_id_wrapper(sessions=sessions)


@app.get("/check_status")
def get_status(session_id: str) -> CheckStatusResponse:
    """Check if the chatbot for the given session is initialized and ready.

    Args:
        session_id (str): The session ID to check.

    Returns:
        CheckStatusResponse: Status and message about chatbot initialization.
    """
    chatbot = sessions.get(session_id)
    return chatbot.get_status_wrapper()


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
    return chatbot.ask_chatbot_wrapper(query)


@app.post("/send_feedback")
def send_feedback(feedback: Feedback) -> FeedbackResponse:
    """Submit user feedback for a chatbot session.

    Args:
        feedback (Feedback): The feedback object containing session ID, rating, and comments.

    Returns:
        FeedbackResponse: Confirmation message and session ID if feedback is stored successfully.
    """  # noqa: E501
    return feedback.send_feedback_wrapper()
