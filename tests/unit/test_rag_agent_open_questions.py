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

all_questions_groundtruth_answers = load_questions_groundtruth_answers()
open_question_groundtruth_answer = (
    "The document does not provide an answer to this question."
)

open_questions = [
    q
    for q in all_questions_groundtruth_answers
    if q["groundtruth_answer"] == open_question_groundtruth_answer
]


@pytest.mark.langsmith
@pytest.mark.parametrize("open_question_unknown_answer_pair", open_questions)
def test_correctness_of_open_questions(
    open_question_unknown_answer_pair: dict,
    correctness_evaluator: SimpleEvaluator | Callable[..., Any],
) -> None:
    """Test the correctness of the RAG agent's answers on open questions."""
    input_ = open_question_unknown_answer_pair["question"]
    reference_output = open_question_unknown_answer_pair["groundtruth_answer"]
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
        pytest.fail("RAG agent failed to handle open question correctly", pytrace=False)
