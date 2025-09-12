"""Test RAG agent."""

import json
from collections.abc import Callable
from typing import Any

import pytest
from dotenv import load_dotenv
from langsmith import testing as t
from openevals.types import SimpleEvaluator

from tests.conftest import invoke_agent, load_questions_groundtruth_answers

load_dotenv()


@pytest.fixture(scope="session")
def prompt() -> str:
    """Construct the prompt for the correctness evaluator."""
    return """You are an expert data labeler evaluating model outputs for correctness. Your task is to assign a score based on the following rubric:

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
    - If the question is not related to Quality Evaluation (e.g., IT, HR, holidays), apologize and offer to help with something else.
    - For any Quality Evaluation inquiries requiring further assistance, refer the user to: info.qualitaet@unibe.ch.

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
    {inputs}
    </input>

    <output>
    {outputs}
    </output>

    Use the reference outputs below to help you evaluate the correctness of the response:

    <reference_outputs>
    {reference_outputs}
    </reference_outputs>
    """  # noqa: E501


all_questions_groundtruth_answers = load_questions_groundtruth_answers()
open_question_groundtruth_answer = (
    "The document does not provide an answer to this question."
)

questions_with_answer = [
    q
    for q in all_questions_groundtruth_answers
    if q["groundtruth_answer"] != open_question_groundtruth_answer
]


@pytest.mark.langsmith
@pytest.mark.parametrize("question_groundtruth_answer_pair", questions_with_answer)
def test_correctness_of_questions_with_answers(
    question_groundtruth_answer_pair: dict,
    correctness_evaluator: SimpleEvaluator | Callable[..., Any],
    prompt: str,  # noqa: ARG001
) -> None:
    """Test the correctness of the RAG agent's answers on answerable questions."""
    input_ = question_groundtruth_answer_pair["question"]
    reference_output = question_groundtruth_answer_pair["groundtruth_answer"]
    output = invoke_agent(input_)

    result = correctness_evaluator(
        inputs=input_, outputs=output["output"], reference_outputs=reference_output
    )

    sources = output["sources"]
    sources_json = json.dumps([str(s) for s in sources]) if sources else "[]"

    t.log_outputs({"answer": output["output"]})
    t.log_outputs({"sources": sources_json})
    t.log_outputs({"correctness_explanation": result.get("comment")})
    if not result["score"]:
        pytest.fail("RAG agent failed to answer the question correctly", pytrace=False)
