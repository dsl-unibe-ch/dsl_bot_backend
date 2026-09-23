"""Configuration file of tests."""

import json
import os
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import AzureChatOpenAI

from app.agent.chatbot_agent import ChatBot
from app.agent.query import QueryInput
from app.config import settings
from tests.dataset_config import (
    processed_questions_answers_path,
    processed_with_translation_path,
)

os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.LANGFUSE_PUBLIC_KEY or "")
os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.LANGFUSE_API_KEY or "")
os.environ.setdefault("LANGFUSE_HOST", settings.LANGFUSE_HOST or "")
os.environ.setdefault("LANGFUSE_BASE_URL", settings.LANGFUSE_HOST or "")


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register custom pytest CLI options."""
    parser.addoption(
        "--origin",
        action="store",
        default="",
        help="Optional origin URL appended to initialize-agent during E2E tests.",
    )


def load_questions_groundtruth_answers() -> dict:
    """Load questions and groundtruth answers from a JSON file."""
    with Path.open(processed_questions_answers_path()) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def judge_model() -> AzureChatOpenAI:
    """Provide the AzureChatOpenAI judge model."""
    return AzureChatOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
        api_version=settings.AZURE_OPENAI_CHAT_API_VERSION,
        api_key=settings.AZURE_OPENAI_PRIMARY_KEY,
        openai_api_type="azure_ad",
        max_tokens=300,
        temperature=0.5,
    )


def _make_judge_evaluator(
    judge_model: AzureChatOpenAI,
    prompt_template: str,
) -> Callable[..., dict[str, Any]]:
    """Build a simple LLM-as-judge evaluator backed by the provided judge model."""

    def _evaluate(
        *, inputs: str, outputs: str, reference_outputs: str, **kwargs: Any
    ) -> dict[str, Any]:
        formatted = prompt_template.format(
            inputs=inputs,
            outputs=outputs,
            reference_outputs=reference_outputs,
            **kwargs,
        )
        scoring_suffix = (
            '\n\nRespond ONLY with a JSON object: {"score": 1, "comment": "..."}'
            " where score is 1 if the output is correct/satisfactory and 0 otherwise."
        )
        response = judge_model.invoke(formatted + scoring_suffix)
        raw = response.content if hasattr(response, "content") else response
        content = (raw if isinstance(raw, str) else str(raw)).strip()
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            score = (
                1 if any(w in content.lower() for w in ("correct", "accurate")) else 0
            )
            return {"score": score, "comment": content}

    return _evaluate


@pytest.fixture(scope="session")
def correctness_evaluator(
    judge_model: AzureChatOpenAI,
    prompt: str,
) -> Callable[..., dict[str, Any]]:
    """Provide the LLM-as-judge correctness evaluator."""
    return _make_judge_evaluator(judge_model, prompt)


def invoke_agent(
    input_: str,
    customer_name: str | None = None,
    history: list[dict[str, str]] | None = None,
) -> dict:
    """Invoke the RAG agent with the given input and return the output."""
    resolved_customer = (
        customer_name or os.environ.get("CUSTOMER_NAME") or settings.FALLBACK_CUSTOMER_ID
    )
    chatbot = ChatBot(customer_name=resolved_customer)
    for turn in history or []:
        role = turn.get("role")
        message = turn.get("message", "")
        if role == "user":
            chatbot.chat_history.append(HumanMessage(content=message))
        elif role == "assistant":
            chatbot.chat_history.append(AIMessage(content=message))
    session_id = uuid.uuid4()
    query_input = QueryInput(text=input_)
    query_response = chatbot.invoke_agent_wrapper(query_input, session_id)
    return {"output": query_response["output"], "sources": query_response["sources"]}


@pytest.fixture(scope="session")
def documentid_to_text_translated() -> dict:
    """Load DocumentID to text_translated mapping from the translation JSON file."""
    with Path.open(processed_with_translation_path()) as f:
        data = json.load(f)
    return {item["DocumentID"]: item["text_translated"] for item in data}
