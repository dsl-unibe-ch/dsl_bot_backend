# Copyright (c) 2026, University of Bern, Data Science Lab
"""Extract human-annotated Excel cases, save JSON, and upload to Langfuse.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pandas as pd
from dotenv import dotenv_values
from langfuse import Langfuse
from langfuse.api import NotFoundError

from tests.dataset_config import (
    generated_human_annotations_path,
    human_annotations_source_path,
)

LOGGER = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_NAME = "human_annotated_dataset"
REQUIRED_COLUMNS = ("Question/Prompt", "Question ID", "Expected Answer")


def extract_cases(
    source: Path,
    sheet_name: str = "Content Testing",
) -> list[dict[str, object]]:
    """Read reviewed answers and remove incomplete rows and duplicate IDs."""
    df = pd.read_excel(source, sheet_name=sheet_name, dtype=object)
    df.columns = df.columns.str.strip()
    df = df[list(REQUIRED_COLUMNS)]
    df = df.dropna()
    df = df.drop_duplicates(subset=["Question ID"])
    df = df.rename(
        columns={
            "Question/Prompt": "question",
            "Question ID": "question_id",
            "Expected Answer": "groundtruth_answer",
        },
    )
    cases = df.to_dict(orient="records")
    for case in cases:
        case["supporting_sentences"] = ["na"]
    return cases


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
                description="Human-annotated questions and expected answers.",
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
    parser.add_argument(
        "--customer-name",
        required=True,
        help="Customer name",
    )
    args = parser.parse_args()
    customer_name = args.customer_name
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    source_path = human_annotations_source_path(customer_name)
    output_path = generated_human_annotations_path(customer_name)

    cases = extract_cases(source_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output:
        json.dump(cases, output, ensure_ascii=False, indent=2, allow_nan=False)
        output.write("\n")
    LOGGER.info("Wrote %d cases to %s.", len(cases), output_path)
    if cases:
        upload_to_langfuse(cases, DEFAULT_DATASET_NAME)
    else:
        LOGGER.warning("No reference answers available; nothing uploaded.")


if __name__ == "__main__":
    main()
