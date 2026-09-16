# Copyright (c) 2026, University of Bern, Data Science Lab
"""Agentic chatbot implementation."""

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
from langchain.tools import tool
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import AzureChatOpenAI
from openai import AzureOpenAI

from app.agent.prompt_templates import (
    _build_agentic_system_prompt,
    get_qa_prompt,
    language_alignment_prompt,
    rewrite_query_prompt,
    translation_prompt,
)
from app.agent.query import QueryInput, QueryOutput, Source
from app.agent.schemas import StartSessionResponse
from app.agent.session_store import save_session
from app.agent.tracing import AgenticTrace
from app.config import settings
from app.logging_config import kioskbot_logger as logger

azure_container_storage_name = settings.AZURE_CONTAINER_STORAGE_NAME

version = "unknown"
with Path.open("pyproject.toml", "rb") as f:
    version = tomllib.load(f).get("project", {}).get("version", "unknown")
environment = os.environ.get("ENV", "unknown")


class ChatBot:
    """Agentic chatbot class to interact with Azure OpenAI and Azure AI Search."""

    def __init__(self, customer_name: str) -> None:
        """Initialize the ChatBot with Azure clients and prompt chains."""
        if not customer_name:
            message = "customer_name is required and must be non-empty."
            raise ValueError(message)
        self.customer_name = customer_name
        self.index_name = f"index-{customer_name}"
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
        self.rewrite_query_chain = rewrite_query_prompt | self.chat_client
        self.language_alignment_chain = language_alignment_prompt | self.chat_client
        self.chat_history = []
        self.interaction_count = 0
        self.enable_agentic_search = settings.ENABLE_AGENTIC_SEARCH
        self.current_retrieval_count = 0
        self.current_agent_action_count = 0
        self._agentic_trace: list[AgenticTrace] = []
        self._agentic_step_number = 0
        self._latest_retrieved_sources: list[Source] = []
        self._latest_retrieved_docs_for_chain: list[Document] = []
        self.tools = [
            tool(
                "rewrite_query",
                self.rewrite_query_tool,
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
            system_prompt=_build_agentic_system_prompt(self.customer_name),
            name="dsl_bot_agent",
        )
        self.max_num_retrievals = settings.AGENTIC_MAX_NUM_RETRIEVALS
        self.max_agent_actions = settings.AGENTIC_MAX_NUM_ACTIONS
        self.max_latency = settings.AGENTIC_MAX_LATENCY
        self.max_token_budget = settings.AGENTIC_MAX_TOKEN_BUDGET
        self.recursion_limit = settings.AGENTIC_RECURSION_LIMIT

    def _reset_agentic_trace(self: ChatBot, query_text: str) -> None:
        """Reset and start a new per-request trace timeline."""
        self._agentic_trace = []
        self._agentic_step_number = 0
        self._append_agentic_trace(
            tool_name="agent_loop_start",
            tool_input_summary=query_text[:200],
            result_count=0,
            top_score=None,
            decision_reason="Started agentic loop for incoming query.",
        )

    def _append_agentic_trace(
        self: ChatBot,
        tool_name: str,
        tool_input_summary: str,
        result_count: int,
        decision_reason: str,
        top_score: float | None = None,
    ) -> None:
        """Append one trace step with monotonic step numbering."""
        self._agentic_step_number += 1
        self._agentic_trace.append(
            AgenticTrace(
                step_number=self._agentic_step_number,
                tool_name=tool_name,
                tool_input_summary=tool_input_summary,
                result_count=result_count,
                top_score=top_score,
                decision_reason=decision_reason,
            )
        )

    def _latest_trace_payload(self: ChatBot) -> list[dict]:
        """Return trace entries as JSON-serializable dictionaries."""
        return [entry.model_dump() for entry in self._agentic_trace]

    def truncate_query(self: ChatBot, query_text: str) -> str:
        """Truncates the query text to a maximum of 100 terms."""
        logger.debug("%s", inspect.currentframe().f_code.co_name)
        max_terms = 300
        query_terms = re.findall(r"\w+", query_text)
        if len(query_terms) > max_terms:
            query_text = " ".join(query_terms[:max_terms])
        return query_text

    def _translate_and_truncate_query_text(self: ChatBot, query_text: str) -> str:
        """Normalizes and translates a query into a retrieval-friendly form."""
        translated_query = self.translation_chain.invoke({"input": query_text})
        if hasattr(translated_query, "content"):
            translated_query = translated_query.content
        return self.truncate_query(translated_query)

    def _rewrite_query_text(self: ChatBot, query_text: str) -> str:
        """Rewrites the query.

        First, into a concise, keyword-dense German retrieval query,
        then truncates.
        """
        rewritten = self.rewrite_query_chain.invoke({"input": query_text})
        if hasattr(rewritten, "content"):
            rewritten = rewritten.content
        return self.truncate_query(rewritten)

    def _align_response_language(
        self: ChatBot, user_message: str, response: str
    ) -> str:
        """Ensures the response is in the same language as the user's message."""
        aligned = self.language_alignment_chain.invoke(
            {"user_message": user_message, "response": response}
        )
        if hasattr(aligned, "content"):
            aligned = aligned.content
        return ftfy.fix_text(str(aligned))

    def rewrite_query_tool(self: ChatBot, query_text: str) -> str:
        """Tool wrapper for query rewrite that tracks agent actions."""
        self.current_agent_action_count += 1
        rewritten = self._rewrite_query_text(query_text)
        self._append_agentic_trace(
            tool_name="rewrite_query",
            tool_input_summary=query_text[:200],
            result_count=1,
            top_score=None,
            decision_reason="Produced retrieval-friendly rewrite.",
        )
        return rewritten

    def _render_documents_for_tool(self: ChatBot, docs: list[Document]) -> str:
        """Converts retrieved documents into compact text for tool output."""
        if not docs:
            return "No matching documents found."
        rendered_docs = []
        for idx, doc in enumerate(docs, start=1):
            metadata = doc.metadata
            rendered_docs.append(
                f"[{idx}] Title: {metadata.get('Title', 'Not Specified')}\n"
                f"URL: {metadata.get('Link', 'Not Specified')}\n"
                f"Category: {metadata.get('Category', 'Not Specified')}\n"
                f"Score: {metadata.get('score', 'Not Specified')}\n"
                f"Content: {doc.page_content}"
            )
        return "\n\n".join(rendered_docs)

    def _retrieve_documents(
        self: ChatBot, query_text: str
    ) -> tuple[list[Document], list[Source]]:
        """Shared retrieval path for RAG and agentic tool calls."""
        rewritten_query = self._translate_and_truncate_query_text(query_text)
        retrieved_docs = self.get_top_k_vector_results(rewritten_query)
        docs_for_chain = []
        docs_for_frontend = []
        for document in retrieved_docs:
            page_content = ftfy.fix_text(document.get("chunk"))
            if not page_content:
                page_content = "Not Specified"
            score = float(document.get("@search.score"))
            document_id = document.get("DocumentID")
            link = document.get("Link") or "Not Specified"
            category = document.get("Category") or "Not Specified"
            title = document.get("Title") or "Not Specified"
            date_last_mod = document.get("Date_Last_Modified") or "Not Specified"
            data_gathered_on = document.get("Data_Gathered_On") or "Not Specified"

            docs_for_chain.append(
                Document(
                    page_content=page_content,
                    metadata={
                        "score": score,
                        "DocumentID": document_id,
                        "Link": link,
                        "Category": category,
                        "Title": title,
                        "Date_Last_Modified": date_last_mod,
                        "Data_Gathered_On": data_gathered_on,
                    },
                )
            )
            docs_for_frontend.append(
                Source(
                    document_location=document_id,
                    page_content=page_content,
                    document_url=link,
                    category=category,
                    title=title,
                    gathered_on=data_gathered_on,
                    modified=date_last_mod,
                    score=score,
                )
            )
        return docs_for_chain, docs_for_frontend

    def search_knowledge_base(self: ChatBot, query: str) -> str:
        """Tool entry point for document retrieval."""
        if self.current_retrieval_count >= self.max_num_retrievals:
            message = f"Retrieval limit of {self.max_num_retrievals} reached."
            self._append_agentic_trace(
                tool_name="search_knowledge_base",
                tool_input_summary=query[:200],
                result_count=0,
                top_score=None,
                decision_reason=message,
            )
            return (
                f"Retrieval limit of {self.max_num_retrievals} reached. "
                "Compose your answer from the information already retrieved."
            )
        self.current_agent_action_count += 1
        self.current_retrieval_count += 1
        docs_for_chain, docs_for_frontend = self._retrieve_documents(query)

        # Accumulate across all retrievals: deduplicate by DocumentID
        # Keep highest score.
        merged_docs: dict[str, Document] = {
            doc.metadata["DocumentID"]: doc
            for doc in self._latest_retrieved_docs_for_chain
        }
        merged_sources: dict[str, Source] = {
            s.document_location: s for s in self._latest_retrieved_sources
        }
        for doc, source in zip(docs_for_chain, docs_for_frontend, strict=True):
            doc_id = doc.metadata.get("DocumentID")
            existing = merged_docs.get(doc_id)
            if existing is None or doc.metadata.get(
                "score", 0.0
            ) > existing.metadata.get("score", 0.0):
                merged_docs[doc_id] = doc
                merged_sources[doc_id] = source
        sorted_ids = sorted(
            merged_docs,
            key=lambda d: merged_docs[d].metadata.get("score", 0.0),
            reverse=True,
        )
        self._latest_retrieved_docs_for_chain = [merged_docs[d] for d in sorted_ids]
        self._latest_retrieved_sources = [merged_sources[d] for d in sorted_ids]

        top_score = None
        if docs_for_chain:
            scored_values = [
                float(doc.metadata.get("score", 0.0))
                for doc in docs_for_chain
                if doc.metadata is not None
            ]
            top_score = max(scored_values) if scored_values else None
        self._append_agentic_trace(
            tool_name="search_knowledge_base",
            tool_input_summary=query[:200],
            result_count=len(docs_for_chain),
            top_score=top_score,
            decision_reason=(
                f"Retrieval attempt {self.current_retrieval_count} completed."
            ),
        )
        return self._render_documents_for_tool(docs_for_chain)

    def _extract_latest_agent_response(self: ChatBot, agent_output: dict) -> str:
        """Extract the last assistant message from a create_agent response."""
        messages = agent_output.get("messages", [])
        for message in reversed(messages):
            if isinstance(message, AIMessage) and message.content:
                return ftfy.fix_text(str(message.content))
        return "I could not generate an answer for this request."

    def _get_response_from_agent(self: ChatBot, query_text: str) -> dict:
        """Execute the LangChain v1 agent loop and return output plus sources."""
        self.current_retrieval_count = 0
        self.current_agent_action_count = 0
        self._reset_agentic_trace(query_text)
        self._latest_retrieved_sources = []
        self._latest_retrieved_docs_for_chain = []
        agent_output = self.agent.invoke(
            {"messages": [*self.chat_history, HumanMessage(content=query_text)]},
            config={"recursion_limit": self.recursion_limit},
        )
        output_text = self._extract_latest_agent_response(agent_output)
        output_text = self._align_response_language(query_text, output_text)
        self._append_agentic_trace(
            tool_name="agent_loop_end",
            tool_input_summary="finalize_response",
            result_count=len(self._latest_retrieved_docs_for_chain),
            top_score=(
                max(
                    (
                        float(doc.metadata.get("score", 0.0))
                        for doc in self._latest_retrieved_docs_for_chain
                    ),
                    default=None,
                )
                if self._latest_retrieved_docs_for_chain
                else None
            ),
            decision_reason="Agent returned final response.",
        )
        self.add_to_chat_history(
            query_text, output_text, self._latest_retrieved_docs_for_chain
        )
        return {
            "output": output_text,
            "sources": self._latest_retrieved_sources,
        }

    def embed_query(self: ChatBot, query_text: str) -> list[float]:
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

    def get_top_k_vector_results(self: ChatBot, query_text: str, k: int = 10) -> list:
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

    def get_response_from_vectordb(self: ChatBot, query_text: str) -> dict:
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
            response = self._align_response_language(query_text, response)
            self.add_to_chat_history(query_text, response, docs_for_chain)
        except Exception:
            logger.exception("Error in get_response_from_vectordb:")
            raise
        else:
            return {"output": response, "sources": docs_for_frontend}

    def add_to_chat_history(
        self: ChatBot, query_text: str, response: str, retrieved_docs: list
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

    def invoke_agent_wrapper(
        self, query: QueryInput, session_id: uuid.UUID
    ) -> QueryOutput:
        """Process a chatbot query and optionally store chat history."""
        if self is None:
            error_message = (
                "Chatbot not initialized - check server logs for initialization errors"
            )
            raise RuntimeError(error_message)

        try:
            request_received_at = datetime.now(ZoneInfo("Europe/Berlin")).isoformat()
            if self.enable_agentic_search:
                query_response = self._get_response_from_agent(query.text)
            else:
                query_response = self.get_response_from_vectordb(query.text)
            response_generated_at = datetime.now(ZoneInfo("Europe/Berlin")).isoformat()
            sources = query_response.get("sources", [])
            sources_json = json.dumps([str(s) for s in sources]) if sources else "[]"

            log_content = {
                "session_id": str(session_id),
                "timestamp": response_generated_at,
                "request_received_at": request_received_at,
                "response_generated_at": response_generated_at,
                "user_message": query.text,
                "agent_response": query_response.get("output"),
                "interaction_count": self.interaction_count,
                "sources": sources_json,
                "version": version,
                "environment": environment,
                "origin": query.origin,
                "index_name": self.index_name,
                "customer_name": self.customer_name,
                "agentic_search_enabled": self.enable_agentic_search,
                "retrieval_count": self.current_retrieval_count,
                "agent_action_count": self.current_agent_action_count,
                "agentic_trace": self._latest_trace_payload(),
            }

            logger.info(
                json.dumps(log_content)
            )  # logger.info/debug/error/etc/ triggers KafkaLoggingHandler.emit()

        except Exception as e:
            error_msg = f"Error in invoke-agent: {type(e).__name__}: {e!s}"
            logger.exception(error_msg)
            raise HTTPException(status_code=500, detail=error_msg) from e

        else:
            save_session(
                session_id,
                self.customer_name,
                self.index_name,
                self.chat_history,
                self.interaction_count,
            )
            return query_response

    def check_stop_or_continue(self, _: str = "") -> bool:
        """Check if the query should be stopped or continued."""
        self.current_agent_action_count += 1
        should_continue = (
            self.current_retrieval_count < self.max_num_retrievals
            and self.current_agent_action_count < self.max_agent_actions
        )
        if should_continue:
            decision_reason = "Within retrieval/action budgets. Continue."
        elif self.current_retrieval_count >= self.max_num_retrievals:
            decision_reason = (
                f"Reached AGENTIC_MAX_NUM_RETRIEVALS={self.max_num_retrievals}."
            )
        else:
            decision_reason = (
                f"Reached AGENTIC_MAX_NUM_ACTIONS={self.max_agent_actions}."
            )
        self._append_agentic_trace(
            tool_name="check_stop_or_continue",
            tool_input_summary=(
                f"retrieval_count={self.current_retrieval_count}, "
                f"agent_action_count={self.current_agent_action_count}"
            ),
            result_count=1 if should_continue else 0,
            top_score=None,
            decision_reason=decision_reason,
        )
        return should_continue

    def initialize_agent_wrapper(self) -> StartSessionResponse:
        """Create a new chatbot session.

        Persist initial state to Redis.

        Return session ID.
        """
        session_id = uuid.uuid4()
        save_session(session_id, self.customer_name, self.index_name, [], 0)
        return StartSessionResponse(
            session_id=session_id,
            customer_name=self.customer_name,
        )
