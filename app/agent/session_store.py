"""Redis-backed session store for cross-pod chat history persistence."""

import json
from uuid import UUID

import redis
from langchain_core.messages import AIMessage, HumanMessage

from app.config import settings
from app.logging_config import kioskbot_logger as logger

# Module-level Redis client — connection pool is reused across requests.
_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Return the shared Redis client, creating it on first call."""
    global _redis_client  # noqa: PLW0603
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD or None,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _redis_client


def _serialize_history(chat_history: list) -> list[dict]:
    """Serialize LangChain message objects to plain dicts for JSON storage.

    Only content is preserved — AIMessage source metadata is not needed
    for history re-injection into the chain.
    """
    result = []
    for msg in chat_history:
        if isinstance(msg, HumanMessage):
            result.append({"type": "human", "content": msg.content})
        elif isinstance(msg, AIMessage):
            result.append({"type": "ai", "content": msg.content})
    return result


def _deserialize_history(data: list[dict]) -> list:
    """Deserialize plain dicts back to LangChain message objects."""
    result = []
    for item in data:
        if item["type"] == "human":
            result.append(HumanMessage(content=item["content"]))
        elif item["type"] == "ai":
            result.append(AIMessage(content=item["content"]))
    return result


def save_session(
    session_id: UUID,
    customer_name: str,
    index_name: str,
    chat_history: list,
    interaction_count: int,
) -> None:
    """Persist session state to Redis with a sliding TTL.

    Args:
        session_id: The unique session identifier.
        customer_name: The customer associated with this session.
        index_name: The Azure AI Search index name for this session.
        chat_history: List of HumanMessage / AIMessage objects.
        interaction_count: Number of completed interactions so far.
    """
    payload = json.dumps({
        "customer_name": customer_name,
        "index_name": index_name,
        "interaction_count": interaction_count,
        "chat_history": _serialize_history(chat_history),
    })
    key = f"session:{session_id}"
    get_redis().setex(key, settings.REDIS_SESSION_TTL_SECONDS, payload)
    logger.debug("Session %s saved to Redis (%d messages)", session_id, len(chat_history))


def load_session(session_id: UUID) -> dict | None:
    """Load session state from Redis.

    Returns:
        Dict with keys ``customer_name``, ``interaction_count``,
        ``chat_history`` (deserialized), or ``None`` if the key is missing.
    """
    key = f"session:{session_id}"
    raw = get_redis().get(key)
    if raw is None:
        return None
    data = json.loads(raw)
    data["chat_history"] = _deserialize_history(data["chat_history"])
    # Refresh TTL on access so active sessions don't expire mid-conversation.
    get_redis().expire(key, settings.REDIS_SESSION_TTL_SECONDS)
    logger.debug("Session %s loaded from Redis (%d messages)", session_id, len(data["chat_history"]))
    return data
