"""Generate assessment dataset for RAG Agent."""

import json
import logging
import time
from pathlib import Path

import pandas as pd
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
    """Question, answer, and supporting sentences for each document."""

    question: str
    answer: str
    supporting_sentences: list[str] = []


# wrapper model to hold multiple question/answer pairs
class QuestionAnswerList(BaseModel):
    """List of pairs of open questions and answerable questions."""

    questions_answers: list[QuestionAnswer]  # relevant questions and their answers
    open_questions: list[str]  # relevant questions with no answer in the text


number_of_questions = 100
open_question_answer = "The document does not provide an answer to this question."


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
        api_key=settings.AZURE_OPENAI_PRIMARY_KEY,
    )

    translation_chain = translation_prompt | chat_client

    return translation_chain.invoke({"input": text}).content


def generate_questions_answers(text: str) -> list:
    """Generate questions and answers, open questions, and supporting sentences from text."""  # noqa: E501
    questions_answers_list = []

    client = AzureOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_key=settings.AZURE_OPENAI_PRIMARY_KEY,
        api_version=settings.AZURE_OPENAI_CHAT_API_VERSION,
    )

    prompt_content = (
        f"Generate {number_of_questions} relevant questions and answers based on the provided text. "  # noqa: E501
        f"For each answer, also extract the exact sentences from the text that were used to generate the answer and return them as a list of strings in a field called 'supporting_sentences'. "  # noqa: E501
        f"Important: When extracting supporting sentences, copy them verbatim from the original text. Do not change punctuation, spacing, or new lines. "  # noqa: E501
        f"If multiple sentences are needed, store each as a separate element in the list, do not merge or join them with '[...]' or any other characters. "  # noqa: E501
        f"Do not add, remove, or modify any words; only extract sentences exactly as they appear in the original text. "  # noqa: E501
        f"Think step by step: First identify the answer, then carefully locate and copy the exact supporting sentences from the text, ensuring they are verbatim and formatted as in the original. "  # noqa: E501
        f"Also generate {number_of_questions} additional relevant questions whose answers are NOT present in the text (these should be open-ended/follow-up questions). "  # noqa: E501
        f"Return them as a JSON object with a top-level array named 'questions_answers' (each entry containing 'question', 'answer', and 'supporting_sentences') and an array named 'open_questions' containing {number_of_questions} question strings whose answers are not in the text."  # noqa: E501
    )

    completion = client.beta.chat.completions.parse(
        model=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": prompt_content,
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
            "supporting_sentences": getattr(
                question_answer_pair, "supporting_sentences", []
            ),
        }
        questions_answers_list.append(tmp)

    for question_answer_pair in getattr(llm_answer, "open_questions", []):
        tmp = {
            "question": question_answer_pair,
            "groundtruth_answer": open_question_answer,
            "supporting_sentences": [],
        }
        questions_answers_list.append(tmp)

    return questions_answers_list


def extract(file_name: str, sheet_name: str) -> list:
    """Extract data from source."""
    full_path = Path("tests/data/raw") / file_name
    df = pd.read_excel(full_path, sheet_name=sheet_name)
    return df.to_dict(orient="records")


def transform(datasets: list) -> dict:
    """Transform the input data by translating the `text` entry (dataset_with_translation) and generating Q&A (questions_answers)."""  # noqa: E501
    for dict_ in tqdm(datasets):
        text = dict_["text"]
        time.sleep(5)
        dict_["text_translated"] = german2english(text)

    entire_translated_text = " ".join([dict_["text_translated"] for dict_ in datasets])
    questions_answers = generate_questions_answers(entire_translated_text)

    # validate supporting sentences
    for question_answer_pair in questions_answers:
        if question_answer_pair["groundtruth_answer"] == open_question_answer:
            if len(question_answer_pair["supporting_sentences"]) == 0:
                continue
            logger.debug(
                "Supporting sentences for question '%s' should be empty: %s",
                question_answer_pair["question"],
                question_answer_pair["supporting_sentences"],
            )
        else:
            valid_sentences = []
            if len(question_answer_pair["supporting_sentences"]) == 0:
                valid_sentences.append("The supporting sentences were not extracted.")
                logger.debug(
                    "Supporting sentences not extracted for question '%s'",
                    question_answer_pair["question"],
                )
            for supporting_sentence in question_answer_pair["supporting_sentences"]:
                if supporting_sentence.lower() in entire_translated_text.lower():
                    valid_sentences.append(supporting_sentence)
                else:
                    valid_sentences.append(
                        "Cannot find the supporting sentence in the text."
                    )
                    logger.debug(
                        "Supporting sentence not found in text for question '%s': %s",
                        question_answer_pair["question"],
                        supporting_sentence,
                    )
            question_answer_pair["supporting_sentences"] = valid_sentences

    return {
        "entire_translated_text": entire_translated_text,
        "dataset_with_translation": datasets,
        "questions_answers": questions_answers,
    }


def store(transformed_dataset: dict, file_name: str) -> None:
    """Store transformed data."""
    entire_translated_text = transformed_dataset["entire_translated_text"]
    dataset_with_translation = transformed_dataset["dataset_with_translation"]
    questions_answers = transformed_dataset["questions_answers"]

    file_name_extension = Path(file_name).suffix

    new_file_name = file_name.replace(
        file_name_extension, "_entire_translated_text.txt"
    )
    full_path = Path("tests/data/processed") / new_file_name
    with Path.open(full_path, "w") as f:
        f.write(entire_translated_text)

    new_file_name = file_name.replace(file_name_extension, "_with_translation.json")
    full_path = Path("tests/data/processed") / new_file_name
    with Path.open(full_path, "w") as f:
        json.dump(dataset_with_translation, f, ensure_ascii=False, indent=2)

    new_file_name = file_name.replace(file_name_extension, "_questions_answers.json")
    full_path = Path("tests/data/processed") / new_file_name
    with Path.open(full_path, "w") as f:
        json.dump(questions_answers, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    datasets = [
        {
            "file_name": "data_overview_ver4.xlsx",
            "sheet_name": "quality_new",
        }
    ]

    for file_name, sheet_name in [(d["file_name"], d["sheet_name"]) for d in datasets]:
        logger.debug("Processing file: %s | sheet name: %s", file_name, sheet_name)
        extracted_data = extract(file_name, sheet_name)
        transformed_datasets = transform(extracted_data)
        store(transformed_datasets, file_name)
