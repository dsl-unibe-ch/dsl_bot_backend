"""Schemas for the query integration."""

from pydantic import BaseModel


class QueryInput(BaseModel):
    """Input for the query.

    Args:
        text: The text of the query
        origin: Optional origin for customer resolution
    """

    text: str
    origin: str | None = None


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
    """

    output: str
    sources: list[Source]
