"""Regression tests from per-customer JSONL (scope, retrieval, language)."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import pytest
from langchain_openai import AzureChatOpenAI
from langfuse import get_client
from langfuse.experiment import Evaluation

from app.config import settings
from tests.conftest import invoke_agent
from tests.dataset_config import langfuse_regression_dataset_name, regression_cases_path

logger = logging.getLogger(__name__)

CLASSIFIER_PROMPT_NAME = os.getenv(
    "LANGFUSE_ROUTING_PROMPT_NAME", "routing-language-scope-classifier"
)

def _resolved_customer_name() -> str:
    return (
        os.environ.get("CUSTOMER_NAME", "").strip() or settings.DEFAULT_CUSTOMER
    ).strip()


def _regression_cases_path() -> Path:
    return regression_cases_path(_resolved_customer_name())


def _langfuse_dataset_name() -> str:
    return os.getenv(
        "LANGFUSE_REGRESSION_DATASET_NAME",
        langfuse_regression_dataset_name(_resolved_customer_name()),
    )


def _load_regression_cases_from_langfuse() -> list[dict]:
    """Load regression cases from the Langfuse dataset."""
    dataset_name = _langfuse_dataset_name()
    langfuse = get_client()
    dataset = langfuse.get_dataset(dataset_name)
    return [
        {
            "id": (item.metadata or {}).get("case_id", item.id),
            "input": item.input,
            "expected": item.expected_output,
        }
        for item in dataset.items
    ]


def _load_regression_cases() -> list[dict]:
    try:
        cases = _load_regression_cases_from_langfuse()
        if cases:
            logger.debug(
                "Loaded %d cases from Langfuse dataset '%s'",
                len(cases),
                _langfuse_dataset_name(),
            )
            return cases
    except Exception as exc:
        logger.debug(
            "Langfuse dataset load failed (%s), falling back to JSONL", exc
        )
    path = _regression_cases_path()
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


_REGRESSION_CASES = _load_regression_cases()
_REGRESSION_PATH = _regression_cases_path()

_PARAM_CASES = _REGRESSION_CASES or [
    pytest.param(None, id="missing-regression-cases-file"),
]
_CASE_IDS = (
    [str(case["id"]) for case in _REGRESSION_CASES]
    if _REGRESSION_CASES
    else ["missing-regression-cases-file"]
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


def _assert_retrieval_hint(output: dict, expected: dict) -> None:
    if "should_retrieve" not in expected:
        return
    if expected.get("scope_label") == "unclear":
        return
    sources = output.get("sources") or []
    if not bool(expected.get("should_retrieve")):
        assert len(sources) == 0, (
            "should_retrieve=false but response included sources; "
            f"count={len(sources)}"
        )


@pytest.mark.regression
@pytest.mark.parametrize("case", _PARAM_CASES, ids=_CASE_IDS)
def test_chatbot_regression_case(
    case: dict | None,
    judge_model: AzureChatOpenAI,
    request: pytest.FixtureRequest,
) -> None:
    """Langfuse classifier for scope/language + retrieval assertions."""
    if case is None:
        pytest.skip(
            f"No regression cases (missing or empty): {_REGRESSION_PATH} "
            f"(set CUSTOMER_NAME and generate tests/data/<customer>/regression_cases.jsonl)"
        )

    customer = _resolved_customer_name()
    user_message = case["input"]["message"]
    history = case["input"].get("history") or []
    expected = case["expected"]

    expected_scope = expected["scope_label"]
    expected_same_language = bool(expected["same_language"])

    output = invoke_agent(user_message, customer_name=customer, history=history)
    response_text = output["output"]

    langfuse = get_client()
    compiled = _compile_classifier_prompt(
        langfuse,
        user_message=user_message,
        assistant_response=response_text,
    )

    judge_raw = judge_model.invoke(compiled)
    judge_content = (
        judge_raw.content if hasattr(judge_raw, "content") else str(judge_raw)
    ).strip()

    classification = _parse_json_object(judge_content)

    if hasattr(request.config, "_regression_results"):
        request.config._regression_results.append({
            "expected_scope": expected_scope,
            "actual_scope": classification.get("scope_label"),
            "expected_language": expected_same_language,
            "actual_language": classification.get("same_language"),
            "expected_retrieve": expected.get("should_retrieve"),
            "actual_retrieve": bool(output.get("sources")),
        })

    assert classification["same_language"] is expected_same_language, classification.get(
        "reason", "same_language mismatch"
    )
    assert classification["scope_label"] == expected_scope, classification.get(
        "reason", "scope_label mismatch"
    )

    _assert_retrieval_hint(output, expected)


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

