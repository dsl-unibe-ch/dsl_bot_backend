
import inspect
import json
import os
import re
import tomllib
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import ftfy
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from fastapi import HTTPException
from langchain.agents import create_agent
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage
from langchain.tools import tool
from langchain_openai import AzureChatOpenAI
from openai import AzureOpenAI

from app.agent.prompt_templates import (
    _build_system_prompt,
    get_qa_prompt,
    translation_prompt,
)
from app.agent.query import QueryInput, QueryOutput, Source
from app.agent.schemas import StartSessionResponse

from app.config import settings
from app.logging_config import kioskbot_logger as logger

azure_container_storage_name = settings.AZURE_CONTAINER_STORAGE_NAME

sessions = {}
version = "unknown"
with Path.open("pyproject.toml", "rb") as f:
    version = tomllib.load(f).get("project", {}).get("version", "unknown")
environment = os.environ.get("ENV", "unknown")

class ChatBot:
    """Agentic chatbot class to interact with Azure OpenAI and Azure AI Search."""
    def __init__(self, customer_name:str) -> None:
        """Initialize the ChatBot with Azure clients and prompt chains."""
        if not customer_name:
            raise ValueError("customer_name is required and must be non-empty.")
        self.customer_name = customer_name
        if customer_name == settings.DEFAULT_CUSTOMER:
            self.index_name = settings.AZURE_DEFAULT_AI_SEARCH_INDEX_NAME
        else:
            self.index_name = f"kb-{customer_name}"
        search_credential = AzureKeyCredential(
            settings.AZURE_SEARCH_SERVICE_PRIMARY_ADMIN_KEY
        )
        self.search_client = SearchClient(
            endpoint=settings.AZURE_SEARCH_ENDPOINT,
            index_name=self.index_name,
            credential=search_credential,
        )
        self.embedding_client = AzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            azure_deployment=settings.AZURE_OPENAI_SEARCH_EMBEDDING_DEPLOYMENT,
            api_version=settings.AZURE_OPENAI_SEARCH_EMBEDDING_API_VERSION,
            api_key=settings.AZURE_OPENAI_PRIMARY_KEY,
        )
        self.chat_client = AzureChatOpenAI(
            azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
            api_version=settings.AZURE_OPENAI_CHAT_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_PRIMARY_KEY,
        )
        self.qa_chain = create_stuff_documents_chain(
            llm=self.chat_client,
            prompt=get_qa_prompt(self.customer_name),
            document_variable_name="context",
        )
        self.translation_chain = translation_prompt | self.chat_client
        self.chat_history = []
        self.interaction_count = 0
        self.enable_agentic_search = settings.ENABLE_AGENTIC_SEARCH
        self._latest_retrieved_sources: list[Source] = []
        self._latest_retrieved_docs_for_chain: list[Document] = []
        self.tools = [
            tool(
                "rewrite_query",
                self._rewrite_query_text,
                description="Rewrite a user query into a concise search query.",
            ),
            tool(
                "check_stop_or_continue",
                self.check_stop_or_continue,
                description="Return True if agent loop should continue searching.",
            ),
            tool(
                "search_knowledge_base",
                self.search_knowledge_base,
                description="Search the vector index and return relevant snippets.",
            ),
        ]
        self.agent = create_agent(
            model=self.chat_client,
            tools=self.tools,
            system_prompt=_build_system_prompt(self.customer_name),
            name="kioskbot_agent",
        )
    
    def truncate_query(self: "ChatBot", query_text: str) -> str:
        """Truncates the query text to a maximum of 100 terms."""
        logger.debug("%s", inspect.currentframe().f_code.co_name)
        max_terms = 100
        query_terms = re.findall(r"\w+", query_text)
        if len(query_terms) > max_terms:
            query_text = " ".join(query_terms[:max_terms])
        return query_text


    def _rewrite_query_text(self: "ChatBot", query_text: str) -> str:
        """Normalizes and translates a query into a retrieval-friendly form."""
        translated_query = self.translation_chain.invoke({"input": query_text})
        if hasattr(translated_query, "content"):
            translated_query = translated_query.content
        return self.truncate_query(translated_query)

    def _render_documents_for_tool(self: "ChatBot", docs: list[Document]) -> str:
        """Converts retrieved documents into compact text for tool output."""
        if not docs:
            return "No matching documents found."
        rendered_docs = []
        for idx, doc in enumerate(docs, start=1):
            metadata = doc.metadata
            rendered_docs.append(
                (
                    f"[{idx}] Title: {metadata.get('Title', 'Not Specified')}\n"
                    f"URL: {metadata.get('Link', 'Not Specified')}\n"
                    f"Category: {metadata.get('Category', 'Not Specified')}\n"
                    f"Score: {metadata.get('score', 'Not Specified')}\n"
                    f"Content: {doc.page_content}"
                )
            )
        return "\n\n".join(rendered_docs)

    def _retrieve_documents(
        self: "ChatBot", query_text: str
    ) -> tuple[list[Document], list[Source]]:
        """Shared retrieval path for RAG and agentic tool calls."""
        rewritten_query = self._rewrite_query_text(query_text)
        retrieved_docs = self.get_top_k_vector_results(rewritten_query)
        return (
            self.format_results_for_chain(retrieved_docs),
            self.format_results_for_frontend(retrieved_docs),
        )

    def search_knowledge_base(self: "ChatBot", query: str) -> str:
        """Tool entry point for document retrieval."""
        docs_for_chain, docs_for_frontend = self._retrieve_documents(query)
        self._latest_retrieved_docs_for_chain = docs_for_chain
        self._latest_retrieved_sources = docs_for_frontend
        return self._render_documents_for_tool(docs_for_chain)

    def _extract_latest_agent_response(self: "ChatBot", agent_output: dict) -> str:
        """Extract the last assistant message from a create_agent response."""
        messages = agent_output.get("messages", [])
        for message in reversed(messages):
            if isinstance(message, AIMessage) and message.content:
                return ftfy.fix_text(str(message.content))
        return "I could not generate an answer for this request."

    def _get_response_from_agent(self: "ChatBot", query_text: str) -> dict:
        """Execute the LangChain v1 agent loop and return output plus sources."""
        self._latest_retrieved_sources = []
        self._latest_retrieved_docs_for_chain = []
        agent_output = self.agent.invoke(
            {"messages": [*self.chat_history, HumanMessage(content=query_text)]}
        )
        output_text = self._extract_latest_agent_response(agent_output)
        self.add_to_chat_history(
            query_text, output_text, self._latest_retrieved_docs_for_chain
        )
        return {
            "output": output_text,
            "sources": self._latest_retrieved_sources,
        }


    def embed_query(self: "ChatBot", query_text: str) -> list[float]:
        """Embeds the query text into a vector using the Azure OpenAI embedding model.

        Args:
            query_text (str): The text to embed.

        Returns:
            list: The embedding of the query text.
        """
        logger.debug("%s", inspect.currentframe().f_code.co_name)
        resp = self.embedding_client.embeddings.create(
            input=[query_text],
            model=settings.AZURE_OPENAI_SEARCH_EMBEDDING_DEPLOYMENT,
        )
        return resp.data[0].embedding


    def get_top_k_vector_results(self: "ChatBot", query_text: str, k: int = 10) -> list:
        """Retrieves the top k vector results from the Azure AI Search index.

        Args:
            query_text (str): The text to search for.
            k (int): The number of results to return.

        Returns:
            list: The top k vector results.
        """
        logger.debug("%s", inspect.currentframe().f_code.co_name)
        query_embedding = self.embed_query(query_text)
        vectorized_query = VectorizedQuery(
            vector=query_embedding, kind="vector", fields="text_vector"
        )
        results = self.search_client.search(
            vector_queries=[vectorized_query],
            search_text=query_text,
            top=k,
            search_fields=["chunk", "Title"],
            select=[
                "chunk",
                "DocumentID",
                "Link",
                "Category",
                "Title",
                "Date_Last_Modified",
                "Data_Gathered_On",
            ],
        )
        return list(results)

    def format_results_for_chain(self: "ChatBot", results: list) -> list[Document]:
        """Format results as LangChain Document objects for chain and chat history.

        Args:
            results (list): The results to format.

        Returns:
            list: The formatted results as a list of Document objects.
        """
        logger.debug("%s", inspect.currentframe().f_code.co_name)
        docs = []
        for document in results:
            page_content = ftfy.fix_text(document.get("chunk"))
            if not page_content:
                page_content = "Not Specified"
            metadata = {
                "score": float(document.get("@search.score")),
                "DocumentID": document.get("DocumentID"),
                "Link": document.get("Link") or "Not Specified",
                "Category": document.get("Category") or "Not Specified",
                "Title": document.get("Title") or "Not Specified",
                "Date_Last_Modified": document.get("Date_Last_Modified")
                or "Not Specified",
                "Data_Gathered_On": document.get("Data_Gathered_On") or "Not Specified",
            }
            docs.append(Document(page_content=page_content, metadata=metadata))
        return docs


    def format_results_for_frontend(
        self: "ChatBot", results: list[Document]
    ) -> list[Source]:
        """Format results as Source objects for returning to the frontend.

        Args:
            results (list): The results to format.

        Returns:
            list: The formatted results as a list of Source objects.
        """
        logger.debug("%s", inspect.currentframe().f_code.co_name)
        page_content_list = []
        for document in results:
            page_content = ftfy.fix_text(document.get("chunk"))
            if not page_content:
                page_content = "Not Specified"
            document_score = float(document.get("@search.score"))
            document_location = document.get("DocumentID")
            document_url = document.get("Link") or "Not Specified"
            document_category = document.get("Category") or "Not Specified"
            document_title = document.get("Title") or "Not Specified"
            date_last_mod = document.get("Date_Last_Modified") or "Not Specified"
            data_gathered_on = document.get("Data_Gathered_On") or "Not Specified"
            page_content_list.append(
                Source(
                    document_location=document_location,
                    page_content=page_content,
                    document_url=document_url,
                    category=document_category,
                    title=document_title,
                    gathered_on=data_gathered_on,
                    modified=date_last_mod,
                    score=document_score,
                )
            )
        return page_content_list

    def get_response_from_vectordb(self: "ChatBot", query_text: str) -> dict:
        """Retrieve respose from the vectordb and generate a response using the chain.

        1) Translate the query to German if needed.
        2) Trunkate the query.
        3) Retrieve the top k vector results from the Azure AI Search index.
        4) Format the results for the chain.
        5) Format the results for the frontend.
        6) Generate a response using the qa_chain.
        7) Add the interaction to the chat history.

        Args:
            query_text (str): The text to search for.

        Returns:
            dict: The response from the vectordb as a list of dict or json objects.
        """
        logger.debug("%s", inspect.currentframe().f_code.co_name)
        try:
            docs_for_chain, docs_for_frontend = self._retrieve_documents(query_text)
            response = self.qa_chain.invoke(
                {
                    "context": docs_for_chain,
                    "input": query_text,
                    "chat_history": self.chat_history,
                }
            )
            if hasattr(response, "content"):
                response = response.content
            self.add_to_chat_history(query_text, response, docs_for_chain)
            return {"output": ftfy.fix_text(response), "sources": docs_for_frontend}
        except Exception:
            logger.exception("Error in get_response_from_vectordb:")
            raise

    def add_to_chat_history(
        self: "ChatBot", query_text: str, response: str, retrieved_docs: list
    ) -> list:
        """Add the latest interaction to the chat history."""
        logger.debug("%s", inspect.currentframe().f_code.co_name)
        self.chat_history.extend(
            [
                HumanMessage(content=query_text),
                AIMessage(content=response, metadata={"sources": retrieved_docs}),
            ]
        )
        self.interaction_count += 1
        max_pairs = 3
        while (len(self.chat_history) - 1) // 2 > max_pairs:
            del self.chat_history[1:3]
        return self.chat_history

    def invoke_agent_wrapper(self, query: QueryInput) -> QueryOutput:
        """Process a chatbot query and optionally store chat history."""
        if self is None:
            error_message = (
                "Chatbot not initialized - check server logs for initialization errors"
            )
            raise RuntimeError(error_message)

        if not query.session_id:
            raise HTTPException(status_code=400, detail="Session ID is required")

        try:
            if self.enable_agentic_search:
                query_response = self._get_response_from_agent(query.text)
            else:
                query_response = self.get_response_from_vectordb(query.text)
            query_response["session_id"] = query.session_id
            now = datetime.now(ZoneInfo("Europe/Berlin"))
            timestamp = now.isoformat()
            sources = query_response.get("sources", [])
            sources_json = json.dumps([str(s) for s in sources]) if sources else "[]"

            log_content = {
                "session_id": str(query.session_id),
                "timestamp": timestamp,
                "user_message": query.text,
                "agent_response": query_response.get("output"),
                "interaction_count": self.interaction_count,
                "sources": sources_json,
                "version": version,
                "environment": environment,
                "origin": query.origin,
                "index_name": self.index_name,
                "customer_name": self.customer_name,
            }
            logger.info(
                json.dumps(log_content)
            )  # logger.info/debug/error/etc/ triggers KafkaLoggingHandler.emit()

        except Exception as e:
            error_msg = f"Error in invoke-agent: {type(e).__name__}: {e!s}"
            logger.exception(error_msg)
            raise HTTPException(status_code=500, detail=error_msg) from e

        else:
            return query_response

    def rewrite_query(self, query: QueryInput) -> QueryInput:
        """Rewrite the query to a more specific question."""
        return QueryInput(
            text=self._rewrite_query_text(query.text),
            session_id=query.session_id,
            origin=query.origin,
        )

    def check_stop_or_continue(self) -> bool:
        """Check if the query should be stopped or continued."""
        return self.interaction_count < settings.AGENTIC_MAX_NUM_RETRIEVALS

    def initialize_agent_wrapper(self, sessions: dict) -> StartSessionResponse:
        """Create a new chatbot session and return the session ID."""
        session_id = uuid.uuid4()
        sessions[session_id] = self
        return StartSessionResponse(
            session_id=session_id,
            customer_name=self.customer_name,
        )
