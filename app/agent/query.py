"""Schemas for the query integration."""

from pydantic import BaseModel


class QueryInput(BaseModel):
    """Input for the query.

    Args:
        text: The text of the query
        session_id: The session ID
    """

    text: str
    session_id: str


class Source(BaseModel):
    """Source for the query.

    Args:
        document_location: The location of the document in the local file system
        page_content: The content of the page
        document_url: The URL of the document
    """

    document_location: str
    page_content: str
    document_url: str
    category: str
    title: str
    gathered_on: str
    modified: str
    score: float


class QueryOutput(BaseModel):
    """Output for the query.

    Args:
        output: The output of the query
        sources: List of query sources where each entry is an object of Source class
        session_id: The session ID
    """

    output: str
    sources: list[Source]
    session_id: str
