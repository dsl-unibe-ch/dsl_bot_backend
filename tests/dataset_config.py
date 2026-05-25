"""Shared configuration for test datasets and assessment-data generation scripts.

Single source of truth for filenames and paths under ``tests/data/`` consumed
by both ``tests/unit/`` and ``scripts/assessment_data/``.
"""

from __future__ import annotations

from pathlib import Path

# Directories
TESTS_DATA_DIR = Path("tests/data")
RAW_DIR = TESTS_DATA_DIR / "raw"
PROCESSED_DIR = TESTS_DATA_DIR / "processed"
DOWNLOADED_PROD_LOGS_DIR = TESTS_DATA_DIR / "downloaded_prod_logs"

# Source workbook for the assessment dataset generator
SOURCE_WORKBOOK_FILENAME = "data_overview_ver4.xlsx"

# Per-customer source workbook sheet names
SOURCE_WORKBOOK_SHEETS: dict[str, str] = {
    "quality": "quality_new",
}

# Processed dataset filename suffixes (appended to the workbook stem)
PROCESSED_SUFFIX_ENTIRE_TRANSLATED_TEXT = "_entire_translated_text.txt"
PROCESSED_SUFFIX_WITH_TRANSLATION = "_with_translation.json"
PROCESSED_SUFFIX_QUESTIONS_ANSWERS = "_questions_answers.json"


def raw_workbook_path(file_name: str = SOURCE_WORKBOOK_FILENAME) -> Path:
    """Return the path to a raw source workbook."""
    return RAW_DIR / file_name


def processed_path(file_name: str, suffix: str) -> Path:
    """Return a processed dataset path derived from a workbook file name."""
    stem = Path(file_name).stem
    return PROCESSED_DIR / f"{stem}{suffix}"


def processed_questions_answers_path(
    file_name: str = SOURCE_WORKBOOK_FILENAME,
) -> Path:
    """Return the processed Q&A JSON path for a source workbook."""
    return processed_path(file_name, PROCESSED_SUFFIX_QUESTIONS_ANSWERS)


def processed_with_translation_path(
    file_name: str = SOURCE_WORKBOOK_FILENAME,
) -> Path:
    """Return the processed translation JSON path for a source workbook."""
    return processed_path(file_name, PROCESSED_SUFFIX_WITH_TRANSLATION)


def processed_entire_translated_text_path(
    file_name: str = SOURCE_WORKBOOK_FILENAME,
) -> Path:
    """Return the processed entire-translated-text path for a source workbook."""
    return processed_path(file_name, PROCESSED_SUFFIX_ENTIRE_TRANSLATED_TEXT)


def regression_cases_path(customer_name: str) -> Path:
    """Return the regression cases JSONL path for a customer."""
    return TESTS_DATA_DIR / customer_name / "regression_cases.jsonl"


def prod_logs_path(customer_name: str, extension: str = "xlsx") -> Path:
    """Return the downloaded prod logs path for a customer."""
    return DOWNLOADED_PROD_LOGS_DIR / f"{customer_name}.{extension}"


def answerable_questions_source_path(customer_name: str) -> Path:
    """Return the source workbook for answerable-questions generation."""
    return TESTS_DATA_DIR / customer_name / "processed_data.xlsx"


def generated_answerable_questions_path(customer_name: str) -> Path:
    """Return the JSONL path for generated answerable questions."""
    return TESTS_DATA_DIR / customer_name / "generated_answerable_questions.jsonl"


def langfuse_regression_dataset_name(customer_name: str) -> str:
    """Return the Langfuse dataset name for behavioural regression cases."""
    return f"{customer_name}_regression_cases"


def langfuse_answerable_dataset_name(customer_name: str) -> str:
    """Return the Langfuse dataset name for answerable Q&A."""
    return f"{customer_name}_answerable_questions"
