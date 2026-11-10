# Copyright (c) 2026, University of Bern, Data Science Lab
"""Extract human-annotated Excel cases, save JSON, and upload to Langfuse.

Running this script uploads to human_annotated_dataset by default. The local
JSON uses the assessment dataset's existing field names. Langfuse items store
question in input, groundtruth_answer in expected_output, and question_id in
metadata. supporting_sentences is a placeholder, not source evidence.
Feedback-only entries and incomplete course-list templates are excluded. Their
question IDs are saved beside the JSON in a *_remaining_ids.txt file.

Run from the repository root:
    python scripts/assessment_data/upload_human_annotations_to_langfuse.py
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from dotenv import dotenv_values
from langfuse import Langfuse
from langfuse.api import NotFoundError
from openpyxl import load_workbook

LOGGER = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = REPO_ROOT / "tests/data/raw/Content Testing_Chatbot.xlsx"
DEFAULT_OUTPUT = REPO_ROOT / "tests/data/langfuse_datasets/human_annotations.json"
DEFAULT_DATASET_NAME = "human_annotated_dataset"
REQUIRED_COLUMNS = ("Question/Prompt", "Question ID", "Expected Answer")
# Reviewed text markers from this workbook, not a general answer-quality judge.
# Matching content rather than IDs allows corrected references to be included
# automatically when the workbook is updated.
NON_REFERENCE_MARKERS = (
    "Die Antwort des Bots ist vollständig, korrekt und verständlich.",
    "Ich liste Ihnen die Kurse auf, die nächste Woche stattfinden",
    "[Kursname gemäss aktueller Kursübersicht]",
)


def _column_indices(headers: list[str]) -> list[int]:
    """Locate each required column once, ignoring unrelated workbook columns."""
    for column in REQUIRED_COLUMNS:
        if headers.count(column) != 1:
            message = f"Expected exactly one column named {column!r}."
            raise ValueError(message)
    return [headers.index(column) for column in REQUIRED_COLUMNS]


def extract_cases(source: Path, sheet_name: str) -> list[dict[str, object]]:
    """Read the agreed columns, preserving text and rejecting incomplete rows."""
    workbook = load_workbook(source, read_only=True, data_only=True)
    try:
        if sheet_name not in workbook.sheetnames:
            message = f"Sheet {sheet_name!r} not found in {source}."
            raise ValueError(message)
        rows = workbook[sheet_name].iter_rows(values_only=True)
        headers = [str(value).strip() for value in next(rows, ())]
        indices = _column_indices(headers)
        cases: list[dict[str, object]] = []
        seen_ids: set[int | str] = set()
        for row_number, row in enumerate(rows, start=2):
            # Ignore empty/formatted rows, but never silently drop partial cases.
            if all(value is None or value == "" for value in row):
                continue
            question, question_id, answer = (row[index] for index in indices)
            for label, value in (
                ("Question/Prompt", question),
                ("Expected Answer", answer),
            ):
                if not isinstance(value, str) or not value.strip():
                    message = f"Excel row {row_number}: {label} must contain text."
                    raise ValueError(message)
            if (
                isinstance(question_id, bool)
                or not isinstance(question_id, (int, str))
                or (isinstance(question_id, str) and not question_id.strip())
            ):
                message = (
                    f"Excel row {row_number}: Question ID must be an integer or text."
                )
                raise ValueError(message)
            if question_id in seen_ids:
                message = (
                    f"Excel row {row_number}: duplicate Question ID {question_id!r}."
                )
                raise ValueError(message)
            seen_ids.add(question_id)
            cases.append(
                {
                    "question": question,
                    "question_id": question_id,
                    "groundtruth_answer": answer,
                    "supporting_sentences": ["na"],
                },
            )
        if not cases:
            message = "No test cases found in the selected sheet."
            raise ValueError(message)
        return cases
    finally:
        workbook.close()


def select_reference_answers(
    cases: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[int | str]]:
    """Separate substantive references from known feedback and template entries."""
    selected: list[dict[str, object]] = []
    remaining_ids: list[int | str] = []
    for case in cases:
        answer = " ".join(str(case["groundtruth_answer"]).split())
        if any(marker in answer for marker in NON_REFERENCE_MARKERS):
            remaining_ids.append(case["question_id"])
        else:
            selected.append(case)
    return selected, remaining_ids


def upload_to_langfuse(cases: list[dict[str, object]], dataset_name: str) -> None:
    """Upload cases with stable IDs so rerunning updates rather than duplicates."""
    env_name = os.environ.get("ENV", "dev")
    values = {**dotenv_values(REPO_ROOT / f".env.{env_name}"), **os.environ}
    keys = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_API_KEY", "LANGFUSE_HOST")
    for key in keys:
        if not values.get(key) or "your-" in values[key]:
            message = f"Configure {key} in .env.{env_name} or your environment."
            raise ValueError(message)
    client = Langfuse(
        public_key=values["LANGFUSE_PUBLIC_KEY"],
        secret_key=values["LANGFUSE_API_KEY"],
        base_url=values["LANGFUSE_HOST"],
        tracing_enabled=False,
    )
    try:
        try:
            client.get_dataset(dataset_name)
        except NotFoundError:
            client.create_dataset(
                name=dataset_name,
                description="Human-annotated BNF questions and expected answers.",
            )
        for case in cases:
            item_id = str(
                uuid5(
                    NAMESPACE_URL,
                    json.dumps([dataset_name, case["question_id"]], ensure_ascii=False),
                ),
            )
            client.create_dataset_item(
                dataset_name=dataset_name,
                id=item_id,
                input={"question": case["question"]},
                expected_output={
                    "groundtruth_answer": case["groundtruth_answer"],
                    "supporting_sentences": case["supporting_sentences"],
                },
                metadata={"question_id": case["question_id"]},
            )
    finally:
        client.shutdown()
    LOGGER.info("Uploaded %d cases to Langfuse dataset %r.", len(cases), dataset_name)


def main() -> None:
    """Convert the workbook and upload its cases without generating answers."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--sheet", default="Content Testing")
    parser.add_argument("--dataset-name", default=DEFAULT_DATASET_NAME)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.output.suffix.lower() != ".json":
        parser.error("--output must have a .json extension.")
    try:
        all_cases = extract_cases(args.input, args.sheet)
        cases, remaining_ids = select_reference_answers(all_cases)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as output:
            json.dump(cases, output, ensure_ascii=False, indent=2, allow_nan=False)
            output.write("\n")
        LOGGER.info("Wrote %d cases to %s.", len(cases), args.output)
        remaining_path = args.output.with_name(f"{args.output.stem}_remaining_ids.txt")
        remaining_path.write_text(
            "These questions are not included yet because their Expected Answer "
            "contains feedback about the bot's response rather than a reference "
            "answer, or an incomplete course-list template without actual course "
            "details (currently IDs 58 and 59). "
            "They need a usable reference answer before they can be included "
            "in the dataset.\n\n"
            + "".join(f"{question_id}\n" for question_id in remaining_ids),
            encoding="utf-8",
        )
        LOGGER.info(
            "Set aside %d feedback/template entries; IDs saved to %s.",
            len(remaining_ids),
            remaining_path,
        )
        if cases:
            upload_to_langfuse(cases, args.dataset_name)
        else:
            LOGGER.warning("No reference answers available; nothing uploaded.")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
