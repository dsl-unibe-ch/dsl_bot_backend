#!/usr/bin/env python3
"""Generate chatbot regression cases from Excel logs.
"""

import argparse
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from langfuse._client.client import Langfuse as LangfuseClient
from openai import AzureOpenAI
from pydantic import BaseModel, ConfigDict, Field
from tqdm import tqdm

from app.config import Settings
from tests.dataset_config import (
    langfuse_regression_dataset_name,
    prod_logs_path,
    regression_cases_path,
)

logger = logging.getLogger("chatbot-regression-generator")
logger.setLevel(logging.DEBUG)
logger.propagate = False

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(handler)


ScopeLabel = Literal["in_scope", "out_of_scope", "unclear"]
AnswerabilityLabel = Literal["answerable_from_docs", "unanswerable_from_docs"]
ExpectedActionLabel = Literal["answer", "clarify", "defer_or_decline"]

fallback_email_address_list = {
        "innovation": ["innovationoffice@unibe.ch", "ideenlabor@unibe.ch"],
        "quality": ["info.qualitaet@unibe.ch", "lehrevaluation@unibe.ch"],
    }

domain_descriptions = {
    "innovation": """Innovation Office
                        Your first point of contact for questions related to innovation and entrepreneurship.

                        Contact
                        Innovation Office
                        Vice-Rectorate Research and Innovation
                        University of Bern
                        Hochschulstrasse 6
                        Office 259
                        3012 Bern
                        General inquiries:
                        E-Mail-Address
                        innovationoffice@unibe.ch
                        Sébastien Hug
                        Phone
                        +41 31 684 48 97
                        E-Mail-Address
                        sebastien.hug@unibe.ch
                        The Innovation Office on LinkedIn
                        As part of a dynamic culture of innovation, the Innovation Office supports students, researchers and clinicians in translating ideas, research and inventions into innovations. It thus strengthens the University’s role of creating value through knowledge for the benefit of society and economy. 
                        For Ideenlabor (Ideas Lab) related questions the address is ideenlabor@unibe.ch, VonRoll A002, Fabrikstrasse 8, 3012 Bern 
                        Services include advise and feedback on:
                        - Early ideas and entrepreneurial projects
                        - Innovation funding (Innosuisse, BRIDGE and Eurostars/EUREKA)
                        - Development of business model and market analysis, preparation of pitches, etc. (via personalized workshops)
                        - Establishment and founding of startups or innovation collaborations 
                        - Innovation impact: identify the impact areas (social, environmental, economic, or specific SDGs) of your innovation and how they can be measured and communicated
                        """,

    "quality": """ Office for Quality Assurance and Development (QAD Office):
                        The University of Bern pursues quality management as a participatory culture that permeates all areas of the university at the university-wide level.
                        It has a university commission, a department for quality assurance and development, the Accreditation Working Group (AKKRED) and faculty quality commissions. It is responsible for institutional accreditation, ensures the implementation of the quality strategy and networks and accompanies stakeholders in quality-related matters.
                        Services
                        The Department of Quality Assurance and Development (QSE Department) supports university members in quality assurance and development (QSE), promotes the university's quality culture and helps with the development and implementation of QSE measures with a range of evaluation tools and processes:

                        Course evaluations and evaluation of performance assessments
                        Study Program Evaluations
                        Research Evaluations
                        Evaluation of the strategic centers
                        Evaluation of the Central Division
                        Graduate Study
                        Internal control circuit
                        Institutional accreditation
                        Commission for Quality Assurance and Development
                        Accreditation Working Group (AKKRED)
                        Advice and support for further evaluation projects. """
                        }


class RegressionInput(BaseModel):
    """User input for one regression case."""

    class HistoryTurn(BaseModel):
        """One prior turn in conversation history."""

        model_config = ConfigDict(extra="forbid")
        role: Literal["user", "assistant"]
        message: str

    message: str
    history: list[HistoryTurn] = Field(default_factory=list)


class RegressionExpected(BaseModel):
    """Expected chatbot behavior."""
    scope_label: ScopeLabel
    answerability: AnswerabilityLabel | None = None
    expected_action: ExpectedActionLabel | None = None
    same_language: bool = True
    should_retrieve: bool | None = None


class RegressionCase(BaseModel):
    """One chatbot regression case."""

    id: str
    input: RegressionInput
    expected: RegressionExpected


class RegressionCaseList(BaseModel):
    """LLM-generated list of regression cases."""
    cases: list[RegressionCase]


SYSTEM_PROMPT_TEMPLATE = """
You generate high-quality behavior regression test cases for a RAG chatbot.

The chatbot belongs to this domain:

Domain name:
{customer_name}

Domain description:
{domain_description}

Fallback email addresses:
{fallback_email_addresses}

Your task:
Given real chatbot log rows, select useful user messages and convert them into
regression test cases. 

Each case must follow this structure:

{{
    "id": "{case_id_prefix}_0001",
  "input": {{
    "message": "Was ist das Innovation Office?",
    "history": []
  }},
  "expected": {{
    "scope_label": "in_scope",
    "answerability": "answerable_from_docs",
    "expected_action": "answer",
    "same_language": true,
    "should_retrieve": true
  }}
}}

Definitions:

1. scope_label

- "in_scope":
  The question belongs to {customer_name} and should normally be answerable
  using the domain knowledge base. 

- "out_of_scope":
  The question belongs to another department, general university administration,
  HR, admissions, salary, unrelated services, web research, or any topic outside
  the bot's responsibility.

- "unclear":
  The message is too short, ambiguous, fragmentary, or context-dependent to
  classify confidently.

2. same_language
The bot should follow the user's language intent even if it differs from the knowledge base language.
- true:
  The bot should answer in the same language as the user message.

- false:
  The user explicitly asks to switch language. 

3. should_retrieve

- true:
  The bot should retrieve from the domain knowledge base.

- false:
  The bot should not retrieve. Use false for greetings, language switches,
  nonsense, meta questions, vague fragments requiring clarification, or clearly
  out-of-scope questions.

4. answerability

- "answerable_from_docs":
  The user question can be answered using the domain knowledge base content.

- "unanswerable_from_docs":
  The user question is in-scope but the knowledge base does not contain the answer.

5. expected_action

- "answer": respond directly with an answer (typically requires retrieval if in-scope).
- "clarify": ask a clarifying question (ambiguous / missing details).
- "defer_or_decline": defer to a human contact or decline (especially for in-scope but
  unanswerable questions, or policy/unsafe content).

Output constraints:
- Under "expected", include ONLY these keys:
  - scope_label
  - answerability
  - expected_action
  - same_language
  - should_retrieve
- Do not output any additional expected keys.

Selection rules:

- Use real user messages from the logs only.
- Do not invent new questions.
- Preserve the original spelling, capitalization, and typos.
- Remove duplicate or near-duplicate messages.
- Do not create cases from rows where user_message is empty.
- Do not create cases from feedback-only rows.
- Prefer messages useful for regression testing.
- Include a balanced mix of:
  - direct answer cases
  - clarify cases
  - defer-to-contact cases
  - route-to-other-unit cases
  - smalltalk/meta/no-retrieval cases
  - fallback-email-overuse prevention cases
- Keep history as [] unless a message is clearly a follow-up.
- If a message only makes sense as a follow-up, include minimal previous turns
  in history if they are available in the logs.
- IDs must be stable, lowercase, and unique.
- IDs must use this prefix and a zero-padded serial number, for example:
{case_id_prefix}_0001

Return only valid structured data matching the response schema.

Here are relevant KB excerpts for reference when inferring answerability and expected behavior:
{kb_context}
"""


def _get_index_name(config: Settings, customer_name: str) -> str:
    """Resolve the Azure AI Search index name for the selected customer."""
    if customer_name == config.DEFAULT_CUSTOMER:
        return config.AZURE_DEFAULT_AI_SEARCH_INDEX_NAME
    return f"kb-{customer_name}"


def make_search_client(*, config: Settings, customer_name: str) -> SearchClient:
    """Create an Azure AI Search client for the selected customer index."""
    return SearchClient(
        endpoint=config.AZURE_SEARCH_ENDPOINT,
        index_name=_get_index_name(config, customer_name),
        credential=AzureKeyCredential(config.AZURE_SEARCH_SERVICE_PRIMARY_ADMIN_KEY),
    )


def embed_query(*, client: AzureOpenAI, config: Settings, query_text: str) -> list[float]:
    """Embed batch query text for vector retrieval."""
    response = client.embeddings.create(
        input=[query_text],
        model=config.AZURE_OPENAI_SEARCH_EMBEDDING_DEPLOYMENT,
    )
    return response.data[0].embedding


def fetch_kb_context_for_rows(
    *,
    embedding_client: AzureOpenAI,
    search_client: SearchClient,
    config: Settings,
    rows: list[dict],
    top_k: int = 100,
    max_chars: int = 24000,
) -> str:
    """Query Azure AI Search directly and return compact relevant excerpts."""
    query_text = " ".join(str(row.get("user_message", "")).strip() for row in rows if row.get("user_message"))
    if not query_text:
        return ""

    query_embedding = embed_query(client=embedding_client, config=config, query_text=query_text)
    vectorized_query = VectorizedQuery(
        vector=query_embedding,
        kind="vector",
        fields="text_vector",
    )
    results = search_client.search(
        vector_queries=[vectorized_query],
        search_text=query_text,
        top=top_k,
        search_fields=["chunk", "Title"],
        select=["chunk", "Title", "Link"],
    )

    context_parts: list[str] = []
    current_length = 0
    for result in results:
        title = str(result.get("Title") or "Untitled")
        chunk = str(result.get("chunk") or "").strip()
        if not chunk:
            continue
        snippet = f"Title: {title}\nChunk: {chunk}"
        separator = "\n\n---\n\n" if context_parts else ""
        addition = f"{separator}{snippet}"
        if current_length + len(addition) > max_chars:
            remaining = max_chars - current_length
            if remaining > len(separator) + 200:
                context_parts.append(f"{separator}{snippet[: remaining - len(separator)]}")
            break
        context_parts.append(addition)
        current_length += len(addition)

    return "".join(context_parts)

def infer_answerability_from_kb(
    *,
    query: str,
    kb_corpus: str,
) -> AnswerabilityLabel:
    """Infer answerability by token overlap against the full KB export.
    """
    answerability_prompt = f"""
    Given the query {query}, determine if a user question can be answered using the provided knowledge base content.
    If the query is in-scope but the KB does not contain the answer, label it as "unanswerable_from_docs". 
    If the KB contains relevant information to answer the query, label it as "answerable_from_docs".
    The KB corpus is as follows:
    {kb_corpus}
    """
    if query.strip() and kb_corpus:
        return "answerable_from_docs"
    return "unanswerable_from_docs"


def make_client(config: Settings) -> AzureOpenAI:
    """Create Azure OpenAI client."""
    return AzureOpenAI(
        azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
        api_key=config.AZURE_OPENAI_PRIMARY_KEY,
        api_version=config.AZURE_OPENAI_CHAT_API_VERSION,
    )


def read_excel_logs(file_path: Path, sheet_name: str | None = None) -> pd.DataFrame:
    """Read chatbot logs from an Excel sheet."""
    df = pd.read_excel(file_path)

    required_columns = {"user_message"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    optional_columns = [
        "session_id",
        "agent_response",
        "comments",
        "feedback",
        "interaction_count",
        "timestamp",
        "sources",
        "version",
    ]

    return df



def is_feedback_only_row(row: pd.Series) -> bool:
    """Detect feedback-only rows."""
    user_message = row.get("user_message")
    agent_response = row.get("agent_response")
    feedback = row.get("feedback")

    return not user_message and not agent_response and not pd.isna(feedback)


def extract_candidate_rows(df: pd.DataFrame) -> list[dict]:
    """Extract candidate rows from chatbot logs."""

    df_cleaned = df.loc[
        lambda frame: frame["user_message"]
        .fillna("")
        .astype(str)
        .str.strip()
        .ne("")
    ]
    if "timestamp" in df_cleaned.columns:
        df_cleaned = df_cleaned.sort_values(by=["timestamp"], na_position="last")  # type: ignore[call-overload]
    df_cleaned = df_cleaned.reset_index(drop=True)
    candidates = []
    for _, row in df_cleaned.iterrows():

        message = row.get("user_message")
        candidates.append({
                "session_id": row.get("session_id"),
                "interaction_count": None
                if pd.isna(row.get("interaction_count"))
                else row.get("interaction_count"),
                "user_message": message,
                "agent_response": row.get("agent_response"),
                "comments": row.get("comments"),
                "feedback": None if pd.isna(row.get("feedback")) else row.get("feedback"),
                "sources_present": bool(row.get("sources")),
                "version": row.get("version"),
            })

    return candidates


def batch_items(items: list[dict], batch_size: int) -> list[list[dict]]:
    """Split list into batches."""
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def generate_cases_for_batch(
    *,
    client: AzureOpenAI,
    search_client: SearchClient,
    config: Settings,
    rows: list[dict],
    customer_name: str,
    domain_description: str,
    fallback_email_addresses: list[str],
    case_id_prefix: str,
    max_cases_per_batch: int,
) -> list[RegressionCase]:
    """Generate regression cases for one batch of logs."""
    kb_context = fetch_kb_context_for_rows(
        embedding_client=client,
        search_client=search_client,
        config=config,
        rows=rows,
    )
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        customer_name=customer_name,
        domain_description=domain_description,
        fallback_email_addresses=fallback_email_addresses,
        case_id_prefix=case_id_prefix,
        kb_context=kb_context,
    )

    user_payload = {
        "instruction": (
            f"Generate at most {max_cases_per_batch} high-quality regression cases "
            "from these real chatbot log rows. Prioritize cases that check whether "
            "the bot should answer, clarify, defer, route elsewhere, or avoid retrieval."
        ),
        "rows": rows,
    }

    completion = client.beta.chat.completions.parse(
        model=config.AZURE_OPENAI_CHAT_DEPLOYMENT,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False, indent=2),
            },
        ],
        response_format=RegressionCaseList,
        temperature=0,
    )

    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise ValueError("Azure OpenAI returned no parsed regression cases.")
    return parsed.cases


def normalize_message(message: str) -> str:
    """Normalize message for deduplication."""
    message = message.lower().strip()
    message = re.sub(r"\s+", " ", message)
    return message


def deduplicate_cases(cases: list[RegressionCase]) -> list[RegressionCase]:
    """Deduplicate cases by user message."""
    seen_messages = set()
    deduplicated = []

    for case in cases:
        key = normalize_message(case.input.message)
        if key in seen_messages:
            continue
        seen_messages.add(key)
        deduplicated.append(case)

    return deduplicated



def write_jsonl(cases: list[RegressionCase], output_path: Path) -> None:
    """Write cases as JSONL."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for case in cases:
            f.write(case.model_dump_json(exclude_none=False) + "\n")


def write_json(cases: list[RegressionCase], output_path: Path) -> None:
    """Write cases as pretty JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(
            [case.model_dump() for case in cases],
            f,
            ensure_ascii=False,
            indent=2,
        )

def reassign_stable_ids(cases: list[RegressionCase], customer_name: str) -> list[RegressionCase]:
    """Reassign stable IDs based on message content."""
    
    for i, case in enumerate(cases):
        case.id = f"{customer_name}_{i+1:04d}"
    return cases

def _create_langfuse_dataset_if_not_exists(
    langfuse_client, dataset_name: str
) -> None:
    """Create the Langfuse dataset if it does not already exist."""
    try:
        langfuse_client.create_dataset(
            name=dataset_name,
            description="Chatbot behavioural regression cases generated from production logs.",
        )
    except Exception:
        pass  # dataset already exists


def upload_cases_to_langfuse(
    cases: list[RegressionCase],
    *,
    customer_name: str,
    dataset_name: str,
    config: Settings,
) -> None:
    """Upload regression cases to a Langfuse dataset."""
    langfuse_client = LangfuseClient(
        public_key=config.LANGFUSE_PUBLIC_KEY,
        secret_key=config.LANGFUSE_API_KEY,
        host=config.LANGFUSE_HOST,
    )
    _create_langfuse_dataset_if_not_exists(langfuse_client, dataset_name)
    for case in cases:
        langfuse_client.create_dataset_item(
            dataset_name=dataset_name,
            input=case.input.model_dump(),
            expected_output=case.expected.model_dump(exclude_none=True),
            metadata={"case_id": case.id, "customer_name": customer_name},
        )
        logger.debug("Uploaded case %s to Langfuse dataset '%s'", case.id, dataset_name)
    langfuse_client.flush()
    logger.info(
        "Uploaded %d cases to Langfuse dataset '%s'", len(cases), dataset_name
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate chatbot regression cases from Excel logs."
    )

    parser.add_argument(
        "--customer-name",
        required=True,
        help="Customer name, e.g. innovation",
    )
    parser.add_argument(
        "--upload-to-langfuse",
        action="store_true",
        default=True,
        help="Upload generated cases to a Langfuse dataset after writing the JSONL.",
    )
    parser.add_argument(
        "--langfuse-dataset-name",
        default=None,
        help=(
            "Langfuse dataset name to upload to. "
            "Defaults to '{customer_name}_regression_cases'."
        ),
    )

    config = Settings()  # type: ignore[call-arg]
    args = parser.parse_args()
    customer_name = args.customer_name
    input_path = prod_logs_path(customer_name)
    output_jsonl_path = regression_cases_path(customer_name)
    index_name = _get_index_name(config, customer_name)
    logger.info("Using Azure AI Search index: %s", index_name)
    
    batch_size = 5
    sleep_seconds = 2.0
    max_cases_per_batch = 25
    
    logger.info("Reading Excel file: %s", input_path)
    df = read_excel_logs(input_path)

    logger.info("Extracting candidate rows")
    candidates = extract_candidate_rows(df)
    logger.info("Found %d candidate user messages", len(candidates))

    if not candidates:
        raise ValueError("No candidate user messages found.")

    client = make_client(config=config)
    search_client = make_search_client(config=config, customer_name=customer_name)

    all_cases: list[RegressionCase] = []
    batches = batch_items(candidates, batch_size)

    for batch_index, batch in enumerate(tqdm(batches), start=1):
        logger.info("Processing batch %d/%d", batch_index, len(batches))

        batch_cases = generate_cases_for_batch(
            client=client,
            search_client=search_client,
            config=config,
            rows=batch,
            customer_name=customer_name,
            domain_description=domain_descriptions[customer_name],
            fallback_email_addresses = fallback_email_address_list[customer_name],
            case_id_prefix=customer_name,
            max_cases_per_batch=max_cases_per_batch,
        )

        all_cases.extend(batch_cases)
        time.sleep(sleep_seconds)

    logger.info("Generated %d raw cases", len(all_cases))

    all_cases = deduplicate_cases(all_cases)
    all_cases = reassign_stable_ids(all_cases, customer_name)

    logger.info("Generated %d final cases", len(all_cases))

    logger.info("Writing JSONL: %s", output_jsonl_path)
    write_jsonl(all_cases, output_jsonl_path)

    if args.upload_to_langfuse:
        dataset_name = (
            args.langfuse_dataset_name
            or langfuse_regression_dataset_name(customer_name)
        )
        logger.info("Uploading cases to Langfuse dataset '%s'", dataset_name)
        upload_cases_to_langfuse(
            all_cases, customer_name=customer_name, dataset_name=dataset_name, config=config
        )

    logger.info("Done")


if __name__ == "__main__":
    main()