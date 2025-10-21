"""Configuration file of tests."""

import json
import os
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from langchain_openai import AzureChatOpenAI
from openevals import create_llm_as_judge
from openevals.types import SimpleEvaluator

from app.agent.chatbot_azure import ChatBot
from app.agent.query import QueryInput
from app.config import settings

os.environ.setdefault("LANGSMITH_TRACING", str(settings.LANGSMITH_TRACING).lower())
os.environ.setdefault("LANGSMITH_TEST_TRACKING", "true")
os.environ.setdefault("LANGSMITH_API_KEY", settings.LANGSMITH_API_KEY)
os.environ.setdefault("LANGSMITH_PROJECT", settings.LANGSMITH_PROJECT)
if getattr(settings, "LANGSMITH_ENDPOINT", None):
    os.environ.setdefault("LANGSMITH_ENDPOINT", settings.LANGSMITH_ENDPOINT)


def load_questions_groundtruth_answers() -> dict:
    """Load questions and groundtruth answers from a JSON file."""
    with Path.open(
        "tests/data/processed/data_overview_ver4_questions_answers.json"
    ) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def judge_model() -> AzureChatOpenAI:
    """Provide the AzureChatOpenAI judge model."""
    return AzureChatOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
        api_version=settings.AZURE_OPENAI_CHAT_API_VERSION,
        api_key=settings.AZURE_OPENAI_CHAT_KEY,
        openai_api_type="azure_ad",
        max_tokens=300,
        temperature=0.5,
    )


@pytest.fixture(scope="session")
def correctness_evaluator(
    judge_model: AzureChatOpenAI,
    prompt: str,
) -> SimpleEvaluator | Callable[..., Any]:
    """Provide the correctness evaluator."""
    return create_llm_as_judge(
        prompt=prompt,
        feedback_key="correctness",
        judge=judge_model,
    )


def invoke_agent(input_: str) -> dict:
    """Invoke the RAG agent with the given input and return the output."""
    chatbot = ChatBot()
    session_id = uuid.uuid4()
    query_input = QueryInput(text=input_, session_id=session_id)
    query_response = chatbot.ask_chatbot_wrapper(query_input)
    return {"output": query_response["output"], "sources": query_response["sources"]}


@pytest.fixture(scope="session")
def documentid_to_text_translated() -> dict:
    """Load DocumentID to text_translated mapping from the translation JSON file."""
    with Path.open(
        "tests/data/processed/data_overview_ver4_with_translation.json"
    ) as f:
        data = json.load(f)
    return {item["DocumentID"]: item["text_translated"] for item in data}
