# Copyright (c) 2026, University of Bern, Data Science Lab
"""Endpoints for the Bot."""

import logging
import tomllib
from pathlib import Path
from typing import Annotated
from uuid import UUID  # noqa: TC003

from fastapi import Cookie, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agent import session_store
from app.agent.chatbot_agent import ChatBot

# Runtime imports (not TYPE_CHECKING): FastAPI/Pydantic must resolve these
# annotations at runtime to build request/response models, but Python 3.14's
# deferred annotation evaluation (PEP 649) means TYPE_CHECKING-only imports
# aren't available when that happens.
from app.agent.feedback import Feedback  # noqa: TC001
from app.agent.query import QueryInput, QueryOutput  # noqa: TC001
from app.agent.schemas import FeedbackResponse, StartSessionResponse  # noqa: TC001
from app.agent.utils import get_customer_name_from_url
from app.config import settings

logger = logging.getLogger("Bot")


def get_version() -> str:
    """Read version from pyproject.toml."""
    pyproject_path = Path(__file__).parents[4] / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    docs_url=settings.DOCS_URL,
    redoc_url=settings.REDOC_URL,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL] if settings.FRONTEND_URL else [],
    allow_credentials=settings.ALLOWED_CREDENTIALS,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
)


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log unexpected exceptions with stack traces."""
    logger.error(
        "Unhandled exception at %s",
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/health")
def health_check() -> dict:
    """Health check endpoint for Kubernetes probes and monitoring."""
    return {"status": "healthy", "version": get_version()}


@app.get("/initialize-agent")
def initialize_agent(
    response: Response, origin: str | None = None
) -> StartSessionResponse:
    """Create a new chatbot session and set a session cookie.

    This endpoint initializes a new ChatBot instance, stores it in the session dictionary,
    and sets a ``session_id`` cookie so the browser automatically identifies itself in
    subsequent requests (/invoke-agent, /send-feedback).

    Returns:
        StartSessionResponse: An object containing the generated session_id and customer_name.
    """  # noqa: E501
    if origin:
        customer_name = get_customer_name_from_url(origin)
        if not customer_name:
            customer_name = settings.DEFAULT_CUSTOMER
    else:
        customer_name = settings.DEFAULT_CUSTOMER
    chatbot = ChatBot(customer_name=customer_name)
    result = chatbot.initialize_agent_wrapper()
    response.set_cookie(
        key="session_id",
        value=str(result.session_id),
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        max_age=settings.REDIS_SESSION_TTL_SECONDS,
    )
    return result


@app.post("/invoke-agent")
def invoke_agent(
    query: QueryInput, session_id: Annotated[UUID | None, Cookie()] = None
) -> QueryOutput:
    """Query the chatbot for an answer using the session cookie and user input.

    Session identified via the ``session_id`` cookie set by GET /initialize-agent.

    Args:
        query (QueryInput): The user's question and optional origin.
        session_id: Extracted automatically from the ``session_id`` cookie.

    Returns:
        QueryOutput: The chatbot's response including sources.
    """
    if session_id is None:
        raise HTTPException(
            status_code=401,
            detail="No session cookie found. Call GET /initialize-agent first.",
        )
    state = session_store.load_session(session_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found. Call GET /initialize-agent to start a session.",
        )
    chatbot = ChatBot(customer_name=state["customer_name"])
    chatbot.chat_history = state["chat_history"]
    chatbot.interaction_count = state["interaction_count"]
    return chatbot.invoke_agent_wrapper(query, session_id)


@app.post("/send-feedback")
def send_feedback(
    feedback: Feedback,
    session_id: Annotated[UUID | None, Cookie()] = None,
) -> FeedbackResponse:
    """Submit user feedback for a chatbot session.

    The session is identified via the ``session_id`` cookie set by GET /initialize-agent.

    Args:
        feedback (Feedback): The feedback object containing rating and optional comments.
        session_id: Extracted automatically from the ``session_id`` cookie.

    Returns:
        FeedbackResponse: Confirmation message if feedback is stored successfully.
    """  # noqa: E501
    if session_id is None:
        raise HTTPException(
            status_code=401,
            detail="No session cookie found. Call GET /initialize-agent first.",
        )
    state = session_store.load_session(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    interaction_count = state["interaction_count"]
    index_name = state["index_name"]
    origin = feedback.origin
    resolved_customer = get_customer_name_from_url(origin) if origin else None
    if not resolved_customer and index_name and index_name.startswith("index_"):
        resolved_customer = index_name.removeprefix("index_")
    return feedback.send_feedback_wrapper(
        session_id,
        interaction_count,
        origin=origin,
        index_name=index_name,
        customer_name=resolved_customer,
    )
