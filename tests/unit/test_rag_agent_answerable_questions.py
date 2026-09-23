"""Test RAG agent correctness on answerable questions via Langfuse experiment."""

import os
from collections.abc import Callable
from datetime import datetime
from typing import Any

import pytest
from langchain_openai import AzureChatOpenAI
from langfuse import get_client as get_langfuse_client
from langfuse.experiment import Evaluation

from app.config import settings
from tests.conftest import invoke_agent
from tests.dataset_config import langfuse_answerable_dataset_name

_CUSTOMER_GUIDELINES: dict[str, str] = {
    "bnf": (
        "- If the question is not related to BNF Nationales Qualifizierungsprogramm  (e.g., IT, HR, holidays),"
        " apologize and offer to help with something else.\n"
        " refer the user to: info.bnf@unibe.ch"
    ),
}

_PROMPT_TEMPLATE = """You are an expert data labeler evaluating model outputs for correctness. Your task is to assign a score based on the following rubric:

    <Rubric>
    A correct answer:
    - Provides accurate and complete information
    - Contains no factual errors
    - Addresses all parts of the question
    - Is logically consistent
    - Uses precise and accurate terminology

    When scoring, you should penalize:
    - Factual errors or inaccuracies
    - Incomplete or partial answers
    - Misleading or ambiguous statements
    - Incorrect terminology
    - Logical inconsistencies
    - Missing key information

    Note that the RAG agent has these additional behavioral guidelines:
    - If the question is vague, ask the user for more specific information.
    {customer_guidelines}

        Make sure to follow these guidelines when evaluating the agent's responses.
    </Rubric>

    <Instructions>
    - Carefully read the input and output
    - Check for factual accuracy and completeness
    - Focus on correctness of information rather than style or verbosity
    </Instructions>

    <Reminder>
    The goal is to evaluate factual correctness and completeness of the response.
    </Reminder>

    <input>
    {{inputs}}
    </input>

    <output>
    {{outputs}}
    </output>

    Use the reference outputs below to help you evaluate the correctness of the response:

    <reference_outputs>
    {{reference_outputs}}
    </reference_outputs>
    """  # noqa: E501


@pytest.fixture(scope="session")
def prompt() -> str:
    """Construct the customer-specific prompt for the correctness evaluator."""
    customer = os.environ.get("CUSTOMER_NAME", "").strip() or settings.FALLBACK_CUSTOMER_ID
    guidelines = _CUSTOMER_GUIDELINES.get(customer, _CUSTOMER_GUIDELINES["quality"])
    return _PROMPT_TEMPLATE.format(customer_guidelines=guidelines)


@pytest.mark.langfuse
def test_correctness_experiment(
    correctness_evaluator: Callable[..., Any],
    judge_model: AzureChatOpenAI,  # noqa: ARG001
    prompt: str,  # noqa: ARG001
) -> None:
    """Run answerable-question correctness as a Langfuse experiment."""
    customer = os.environ.get("CUSTOMER_NAME", "").strip() or settings.FALLBACK_CUSTOMER_ID
    dataset_name = langfuse_answerable_dataset_name(customer)
    langfuse = get_langfuse_client()

    try:
        dataset = langfuse.get_dataset(dataset_name)
    except Exception as exc:
        pytest.skip(
            f"Could not load Langfuse dataset '{dataset_name}': {exc}\n"
            f"Run: make generate-assessment-dataset CUSTOMER_NAME={customer}"
        )

    if not dataset.items:
        pytest.skip(
            f"Langfuse dataset '{dataset_name}' is empty. "
            f"Run: make generate-assessment-dataset CUSTOMER_NAME={customer}"
        )

    def task(*, item, **_kwargs) -> dict:  # type: ignore[misc]
        question = item.input["question"]
        output = invoke_agent(question, customer_name=customer)
        return {
            "agent_output": output["output"],
            "sources": [
                {
                    "document_url": s.document_url,
                    "document_location": s.document_location,
                    "page_content": s.page_content,
                    "score": s.score,
                }
                for s in (output.get("sources") or [])
            ],
        }

    def evaluator_correctness(
        *, input, output, expected_output, **_kwargs
    ) -> Evaluation:  # type: ignore[misc]
        result = correctness_evaluator(
            inputs=input["question"],
            outputs=output["agent_output"],
            reference_outputs=expected_output["groundtruth_answer"],
        )
        return Evaluation(
            name="correctness",
            value=float(result["score"]),
            comment=result.get("comment"),
        )

    run_name = f"pytest-{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}"
    result = langfuse.run_experiment(
        name=dataset_name,
        run_name=run_name,
        data=dataset.items,
        task=task,
        evaluators=[evaluator_correctness],
    )

    scores = [
        float(e.value)  # type: ignore[arg-type]
        for ir in result.item_results
        for e in ir.evaluations
        if e.name == "correctness"
    ]

    if result.dataset_run_url:
        print(f"\nLangfuse experiment: {result.dataset_run_url}")

    if scores:
        accuracy = sum(scores) / len(scores)
        if accuracy < 0.7:
            pytest.fail(
                f"Correctness accuracy {accuracy:.1%} < 70% threshold "
                f"({int(sum(scores))}/{len(scores)} correct)",
                pytrace=False,
            )
