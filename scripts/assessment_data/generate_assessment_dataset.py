"""Generate answerable Q&A assessment dataset from knowledge base."""

import argparse
import json
import logging
from pathlib import Path

import pandas as pd
from openai import AzureOpenAI
from pydantic import BaseModel

from app.config import Settings
from langfuse._client.client import Langfuse as LangfuseClient
from tests.dataset_config import (
    answerable_questions_source_path,
    generated_answerable_questions_path,
    langfuse_answerable_dataset_name,
)

logger = logging.getLogger("assessment-dataset-generator")
logger.setLevel(logging.DEBUG)
logger.propagate = False
_handler = logging.StreamHandler()
_handler.setLevel(logging.DEBUG)
_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(_handler)

NUMBER_OF_QUESTIONS = 100
# Stay well under the 272K token model limit (~4 chars/token, leave room for prompt + response)
MAX_CHARS_PER_CHUNK = 750_000


class QuestionAnswer(BaseModel):
    """Answerable question with ground-truth answer and supporting sentences."""

    question: str
    answer: str
    supporting_sentences: list[str] = []


class QuestionAnswerList(BaseModel):
    """List of answerable Q&A pairs."""

    questions_answers: list[QuestionAnswer]


def make_client(config: Settings) -> AzureOpenAI:
    """Create Azure OpenAI client."""
    return AzureOpenAI(
        azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
        api_key=config.AZURE_OPENAI_PRIMARY_KEY,
        api_version=config.AZURE_OPENAI_CHAT_API_VERSION,
    )


def _split_into_chunks(texts: list[str], max_chars: int) -> list[str]:
    """Bucket rows into chunks where each chunk's combined text stays under max_chars."""
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for text in texts:
        text_len = len(text) + 2  # +2 for the "\n\n" separator
        if current_len + text_len > max_chars and current:
            chunks.append("\n\n".join(current))
            current = [text]
            current_len = text_len
        else:
            current.append(text)
            current_len += text_len
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _generate_from_chunk(
    text: str, *, client: AzureOpenAI, config: Settings, n_questions: int
) -> list[dict]:
    """Call the LLM for a single text chunk."""
    prompt = (
        f"Generate {n_questions} relevant questions and their answers "
        "based on the provided text. "
        "Every answer must be directly supported by the text — do not include questions "
        "whose answers are not present. "
        "For each answer, also extract the verbatim supporting sentences from the text. "
        "Return only the structured JSON — no extra commentary."
    )
    completion = client.beta.chat.completions.parse(
        model=config.AZURE_OPENAI_CHAT_DEPLOYMENT,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
        response_format=QuestionAnswerList,
        temperature=0,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        return []
    return [
        {
            "question": qa.question,
            "groundtruth_answer": qa.answer,
            "supporting_sentences": qa.supporting_sentences,
        }
        for qa in parsed.questions_answers
    ]


def generate_answerable_questions(
    texts: list[str], *, client: AzureOpenAI, config: Settings
) -> list[dict]:
    """Generate answerable Q&A pairs from a list of document texts, chunking as needed."""
    chunks = _split_into_chunks(texts, MAX_CHARS_PER_CHUNK)
    n_per_chunk = max(1, NUMBER_OF_QUESTIONS // len(chunks))
    logger.info(
        "Generating Q&A from %d chunk(s), ~%d questions each", len(chunks), n_per_chunk
    )
    all_cases: list[dict] = []
    for i, chunk in enumerate(chunks, 1):
        logger.info("Processing chunk %d/%d (%d chars)...", i, len(chunks), len(chunk))
        cases = _generate_from_chunk(chunk, client=client, config=config, n_questions=n_per_chunk)
        all_cases.extend(cases)
        logger.info("Chunk %d: got %d questions (total so far: %d)", i, len(cases), len(all_cases))
    return all_cases


def upload_to_langfuse(
    cases: list[dict],
    *,
    customer_name: str,
    dataset_name: str,
    config: Settings,
) -> None:
    """Upload answerable Q&A cases to a Langfuse dataset."""
    langfuse = LangfuseClient(
        public_key=config.LANGFUSE_PUBLIC_KEY,
        secret_key=config.LANGFUSE_API_KEY,
        host=config.LANGFUSE_HOST,
    )
    try:
        langfuse.create_dataset(
            name=dataset_name,
            description=f"Answerable Q&A pairs generated from the {customer_name} knowledge base.",
        )
        logger.info("Created Langfuse dataset '%s'", dataset_name)
    except Exception:
        logger.info("Langfuse dataset '%s' already exists, continuing...", dataset_name)

    for case in cases:
        langfuse.create_dataset_item(
            dataset_name=dataset_name,
            input={"question": case["question"]},
            expected_output={"groundtruth_answer": case["groundtruth_answer"]},
            metadata={"customer_name": customer_name},
        )
    langfuse.flush()
    logger.info("Uploaded %d cases to Langfuse dataset '%s'", len(cases), dataset_name)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate answerable Q&A dataset from knowledge base."
    )
    parser.add_argument(
        "--customer-name",
        required=True,
        help="Customer name, e.g. quality or innovation",
    )
    args = parser.parse_args()
    customer_name = args.customer_name

    config = Settings()  # type: ignore[call-arg]

    source_path = answerable_questions_source_path(customer_name)
    output_path = generated_answerable_questions_path(customer_name)
    dataset_name = langfuse_answerable_dataset_name(customer_name)

    logger.info("Reading source: %s", source_path)
    if not source_path.exists():
        raise FileNotFoundError(
            f"Source workbook not found: {source_path}\n"
            f"Expected: tests/data/{customer_name}/processed_data.xlsx"
        )

    df = pd.read_excel(source_path)
    if "text" not in df.columns:
        raise ValueError(
            f"Expected a 'text' column in {source_path}, found: {list(df.columns)}"
        )

    texts = df["text"].dropna().astype(str).tolist()
    total_chars = sum(len(t) for t in texts)
    logger.info("Loaded %d rows, total text length: %d chars", len(texts), total_chars)

    client = make_client(config)
    cases = generate_answerable_questions(texts, client=client, config=config)
    logger.info("Generated %d answerable questions", len(cases))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")
    logger.info("Written: %s", output_path)

    logger.info("Uploading to Langfuse dataset '%s'", dataset_name)
    upload_to_langfuse(
        cases, customer_name=customer_name, dataset_name=dataset_name, config=config
    )
    logger.info("Done")


if __name__ == "__main__":
    main()
