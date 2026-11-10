# Copyright (c) 2026, University of Bern, Data Science Lab
"""Extract human-annotated Excel cases, save JSON, and upload to Langfuse.

Running this script uploads to human_annotated_dataset by default. The local
JSON uses the assessment dataset's existing field names. Langfuse items store
question and question_id in input, groundtruth_answer in expected_output, and
question_id in metadata. supporting_sentences is a placeholder, not source evidence.
The manually reviewed human_annotations_remaining_ids.txt file controls which
questions are excluded. It must be provided locally, like the source workbook.
The script reads this file without overwriting it or judging answer wording.
Excluding an ID skips its upload; it does not remove an item already in Langfuse.

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
DEFAULT_REMAINING_IDS = (
    REPO_ROOT / "tests/data/langfuse_datasets/human_annotations_remaining_ids.txt"
)
DEFAULT_DATASET_NAME = "human_annotated_dataset"
REQUIRED_COLUMNS = ("Question/Prompt", "Question ID", "Expected Answer")


def extract_cases(source: Path) -> list[dict[str, object]]:
    """Read the Content Testing template, preserving text and validating rows."""
    sheet_name = "Content Testing"
    workbook = load_workbook(source, read_only=True, data_only=True)
    try:
        rows = workbook[sheet_name].iter_rows(values_only=True)
        headers = [str(value).strip() for value in next(rows, ())]
        indices = [headers.index(column) for column in REQUIRED_COLUMNS]
        cases: list[dict[str, object]] = []
        seen_ids: set[str] = set()
        for row_number, row in enumerate(rows, start=2):
            # Ignore empty/formatted rows, but never silently drop partial cases.
            if all(value is None or value == "" for value in row):
                continue
            question, question_id, answer = (row[index] for index in indices)
            if any(
                value is None or not str(value).strip()
                for value in (question, question_id, answer)
            ):
                message = (
                    f"Excel row {row_number}: missing question, ID or expected answer."
                )
                raise ValueError(message)
            if str(question_id) in seen_ids:
                message = (
                    f"Excel row {row_number}: duplicate Question ID {question_id!r}."
                )
                raise ValueError(message)
            seen_ids.add(str(question_id))
            cases.append(
                {
                    "question": question,
                    "question_id": question_id,
                    "groundtruth_answer": answer,
                    "supporting_sentences": ["na"],
                },
            )
        return cases
    finally:
        workbook.close()


def upload_to_langfuse(cases: list[dict[str, object]], dataset_name: str) -> None:
    """Upload cases with stable IDs so rerunning updates rather than duplicates."""
    env_name = os.environ.get("ENV", "dev")
    values = {**dotenv_values(REPO_ROOT / f".env.{env_name}"), **os.environ}
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
                input={
                    "question": case["question"],
                    "question_id": case["question_id"],
                },
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
    parser.add_argument(
        "--remaining-ids-file", type=Path, default=DEFAULT_REMAINING_IDS
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    remaining_ids = {
        line.strip()
        for line in args.remaining_ids_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    cases = [
        case
        for case in extract_cases(args.input)
        if str(case["question_id"]) not in remaining_ids
    ]
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with DEFAULT_OUTPUT.open("w", encoding="utf-8") as output:
        json.dump(cases, output, ensure_ascii=False, indent=2, allow_nan=False)
        output.write("\n")
    LOGGER.info("Wrote %d cases to %s.", len(cases), DEFAULT_OUTPUT)
    if cases:
        upload_to_langfuse(cases, DEFAULT_DATASET_NAME)
    else:
        LOGGER.warning("No reference answers available; nothing uploaded.")


if __name__ == "__main__":
    main()
