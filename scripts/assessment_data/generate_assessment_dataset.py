"""Generate assessment dataset for RAG Agent."""

import json
import logging
import time
from pathlib import Path

import pandas as pd
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from openai import AzureOpenAI
from pydantic import BaseModel
from tqdm import tqdm

from app.config import settings

# logger
logger = logging.getLogger("assessment-dataset-generator")
logger.setLevel(logging.DEBUG)
logger.propagate = False
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(handler)


class QuestionAnswer(BaseModel):
    """Question and answer pairs for each document."""

    question: str
    answer: str


# wrapper model to hold multiple question/answer pairs
class QuestionAnswerList(BaseModel):
    """List of pairs of open questions and answerable questions."""

    questions_answers: list[QuestionAnswer]  # relevant questions and their answers
    open_questions: list[str]  # relevant questions with no answer in the text


number_of_questions = 100
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
)


def german2english(text: str) -> str:
    """Translate German text to English."""
    translation_system_prompt = """Translate in English the following text.

    ** Important: **
    - do not translate links, email addresses, names of people and places.
    - keep the format of the original text (e.g. if there are bullet points, keep them).

    Text: {input}
    The translated text is: {{output}}
    """

    translation_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", translation_system_prompt),
            ("human", "{input}"),
        ]
    )

    chat_client = AzureChatOpenAI(
        azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
        api_version=settings.AZURE_OPENAI_CHAT_API_VERSION,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        azure_ad_token_provider=token_provider,
    )

    translation_chain = translation_prompt | chat_client

    return translation_chain.invoke({"input": text}).content


def generate_questions_answers(text: str) -> list:
    """Generate questions and answers, and open questions from text."""
    questions_answers_list = []

    client = AzureOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        azure_ad_token_provider=token_provider,
        api_version=settings.AZURE_OPENAI_CHAT_API_VERSION,
    )

    completion = client.beta.chat.completions.parse(
        model=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": f"Generate {number_of_questions} relevant questions and answers based on the provided text. Also generate {number_of_questions} additional relevant questions whose answers are NOT present in the text (these should be open-ended/follow-up questions). Return them as a JSON object with a top-level array named 'questions_answers' (each entry containing 'question' and 'answer') and an array named 'open_questions' containing {number_of_questions} question strings whose answers are not in the text.",  # noqa: E501
            },
            {"role": "user", "content": text},
        ],
        response_format=QuestionAnswerList,
    )

    llm_answer = completion.choices[0].message.parsed

    for question_answer_pair in getattr(llm_answer, "questions_answers", []):
        tmp = {
            "question": question_answer_pair.question,
            "groundtruth_answer": question_answer_pair.answer,
        }
        questions_answers_list.append(tmp)

    for question_answer_pair in getattr(llm_answer, "open_questions", []):
        tmp = {
            "question": question_answer_pair,
            "groundtruth_answer": "The document does not provide an answer to this question.",  # noqa: E501
        }
        questions_answers_list.append(tmp)

    return questions_answers_list


def extract(file_name: str, encoding: str) -> list:
    """Extract data from source."""
    full_path = Path("tests/data/raw") / file_name
    df = pd.read_csv(full_path, encoding=encoding)
    return df.to_dict(orient="records")[:2]


def transform(datasets: list) -> dict:
    """Transform the input data by translating the `text` entry (dataset_with_translation) and generating Q&A (questions_answers)."""  # noqa: E501
    for dict_ in tqdm(datasets):
        text = dict_["text"]
        time.sleep(5)
        dict_["text_translated"] = german2english(text)

    entire_translated_text = " ".join([dict_["text_translated"] for dict_ in datasets])
    questions_answers = generate_questions_answers(entire_translated_text)

    return {
        "dataset_with_translation": datasets,
        "questions_answers": questions_answers,
    }


def store(transformed_dataset: dict, file_name: str, encoding: str) -> None:
    """Store transformed data."""
    dataset_with_translation = transformed_dataset["dataset_with_translation"]
    questions_answers = transformed_dataset["questions_answers"]

    file_name_extension = Path(file_name).suffix

    new_file_name = file_name.replace(file_name_extension, "_with_translation.json")
    full_path = Path("tests/data/processed") / new_file_name
    with Path.open(full_path, "w", encoding=encoding) as f:
        json.dump(dataset_with_translation, f, ensure_ascii=False, indent=2)

    new_file_name = file_name.replace(file_name_extension, "_questions_answers.json")
    full_path = Path("tests/data/processed") / new_file_name
    with Path.open(full_path, "w", encoding="utf-8") as f:
        json.dump(questions_answers, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    datasets = [
        {
            "file_name": "data_overview_ver4(quality_new).csv",
            "encoding": "utf-8-sig",
        }
    ]

    for file_name, encoding in [(d["file_name"], d["encoding"]) for d in datasets]:
        logger.debug("Processing file: %s with encoding: %s", file_name, encoding)
        extracted_data = extract(file_name, encoding)
        transformed_datasets = transform(extracted_data)
        store(transformed_datasets, file_name, encoding)
