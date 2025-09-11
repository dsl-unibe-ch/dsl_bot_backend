"""Test RAG agent."""

import json
from pathlib import Path

import pytest
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langsmith import testing as t
from openevals.llm import create_llm_as_judge
from openevals.prompts import CORRECTNESS_PROMPT

from app.agent.chatbot_azure import ChatBot
from app.agent.query import QueryInput
from app.config import settings

load_dotenv()


def load_questions_groundtruth_answers() -> dict:
    """Load questions and groundtruth answers from a JSON file."""
    with Path.open(
        "tests/data/processed/data_overview_ver4(quality_new)_questions_answers.json",
        encoding="utf-8-sig",
    ) as f:
        return json.load(f)


def invoke_agent(input_: str) -> str:
    """Invoke the RAG agent with the given input and return the output."""
    chatbot = ChatBot()
    query_input = QueryInput(text=input_, session_id="test_session")
    query_response = chatbot.ask_chatbot_wrapper(query_input)
    return query_response["output"]


questions_groundtruth_answers = load_questions_groundtruth_answers()


@pytest.mark.langsmith
@pytest.mark.parametrize(
    "question_groundtruth_answer_pair", questions_groundtruth_answers
)
def test_correctness(question_groundtruth_answer_pair: dict) -> None:
    """Test the correctness of the RAG agent's answers."""
    input_ = question_groundtruth_answer_pair["question"]
    reference_output = question_groundtruth_answer_pair["groundtruth_answer"]
    output = invoke_agent(input_)

    result = correctness_evaluator(
        inputs=input_, outputs=output, reference_outputs=reference_output
    )

    t.log_outputs({"answer": output})
    t.log_outputs({"correctness_explanation": result.get("comment")})


judge_model = AzureChatOpenAI(
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
    api_version=settings.AZURE_OPENAI_CHAT_API_VERSION,
    api_key=settings.AZURE_OPENAI_CHAT_KEY,
    openai_api_type="azure_ad",
    max_tokens=300,
    temperature=0.5,
)

correctness_evaluator = create_llm_as_judge(
    prompt=CORRECTNESS_PROMPT,
    feedback_key="correctness",
    judge=judge_model,
)
