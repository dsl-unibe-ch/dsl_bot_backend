"""Regression experiment for scope, language, and retrieval (Langfuse)."""

from __future__ import annotations

import json
import os
from datetime import datetime

import pytest
from langchain_openai import AzureChatOpenAI
from langfuse import get_client
from langfuse.experiment import Evaluation

from app.config import settings
from tests.conftest import invoke_agent
from tests.dataset_config import langfuse_regression_dataset_name

CLASSIFIER_PROMPT_NAME = os.getenv(
    "LANGFUSE_ROUTING_PROMPT_NAME", "routing-language-scope-classifier"
)


def _resolved_customer_name() -> str:
    return (
        os.environ.get("CUSTOMER_NAME", "").strip() or settings.DEFAULT_CUSTOMER
    ).strip()


def _langfuse_dataset_name() -> str:
    return os.getenv(
        "LANGFUSE_REGRESSION_DATASET_NAME",
        langfuse_regression_dataset_name(_resolved_customer_name()),
    )


def _parse_json_object(raw: str) -> dict:
    """Parse model output, stripping optional markdown fences."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


def _compile_classifier_prompt(
    langfuse_client,
    *,
    user_message: str,
    assistant_response: str,
) -> str | list:
    prompt = langfuse_client.get_prompt(CLASSIFIER_PROMPT_NAME)
    return prompt.compile(
        user_message=user_message,
        assistant_response=assistant_response,
    )


@pytest.mark.langfuse
def test_regression_experiment(judge_model: AzureChatOpenAI) -> None:
    """Run regression cases as a Langfuse experiment (visible in Langfuse UI → Experiments)."""
    dataset_name = _langfuse_dataset_name()
    customer = _resolved_customer_name()
    langfuse = get_client()

    try:
        dataset = langfuse.get_dataset(dataset_name)
    except Exception as exc:
        pytest.skip(f"Could not load Langfuse dataset '{dataset_name}': {exc}")

    if not dataset.items:
        pytest.skip(f"Langfuse dataset '{dataset_name}' is empty.")

    def task(*, item, **_kwargs) -> dict:  # type: ignore[misc]
        user_message = item.input["message"]
        history = item.input.get("history") or []
        output = invoke_agent(user_message, customer_name=customer, history=history)
        compiled = _compile_classifier_prompt(
            langfuse,
            user_message=user_message,
            assistant_response=output["output"],
        )
        judge_raw = judge_model.invoke(compiled)
        content = (
            judge_raw.content if hasattr(judge_raw, "content") else str(judge_raw)
        ).strip()
        classification = _parse_json_object(content)
        return {
            "agent_output": output["output"],
            "sources_count": len(output.get("sources") or []),
            "classification": classification,
        }

    def evaluator_scope(*, output, expected_output, **_kwargs) -> Evaluation:  # type: ignore[misc]
        expected = (expected_output or {}).get("scope_label")
        actual = output["classification"].get("scope_label")
        return Evaluation(
            name="scope_correct",
            value=1 if actual == expected else 0,
            comment=f"expected={expected}, actual={actual}",
        )

    def evaluator_language(*, output, expected_output, **_kwargs) -> Evaluation:  # type: ignore[misc]
        expected = bool((expected_output or {}).get("same_language", True))
        actual = output["classification"].get("same_language")
        return Evaluation(
            name="language_correct",
            value=1 if actual == expected else 0,
            comment=f"expected={expected}, actual={actual}",
        )

    def evaluator_retrieval(*, output, expected_output, **_kwargs) -> list[Evaluation]:  # type: ignore[misc]
        if "should_retrieve" not in (expected_output or {}):
            return []
        if (expected_output or {}).get("scope_label") == "unclear":
            return []
        expected = bool(expected_output["should_retrieve"])
        actual = output["sources_count"] > 0
        return [Evaluation(
            name="retrieval_correct",
            value=1 if actual == expected else 0,
            comment=f"expected={expected}, actual={actual}",
        )]

    run_name = f"pytest-{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}"
    result = langfuse.run_experiment(
        name=dataset_name,
        run_name=run_name,
        data=dataset.items,
        task=task,
        evaluators=[evaluator_scope, evaluator_language, evaluator_retrieval],
    )

    scope_scores: list[float] = [
        float(e.value)  # type: ignore[arg-type]
        for ir in result.item_results
        for e in ir.evaluations if e.name == "scope_correct"
    ]
    language_scores: list[float] = [
        float(e.value)  # type: ignore[arg-type]
        for ir in result.item_results
        for e in ir.evaluations if e.name == "language_correct"
    ]

    failures = []
    if scope_scores:
        scope_accuracy = sum(scope_scores) / len(scope_scores)
        if scope_accuracy < 0.7:
            failures.append(f"Scope accuracy {scope_accuracy:.1%} < 70% threshold")
    if language_scores:
        lang_accuracy = sum(language_scores) / len(language_scores)
        if lang_accuracy < 0.9:
            failures.append(f"Language accuracy {lang_accuracy:.1%} < 90% threshold")

    if result.dataset_run_url:
        print(f"\nLangfuse experiment: {result.dataset_run_url}")

    if failures:
        pytest.fail("\n".join(failures), pytrace=False)

