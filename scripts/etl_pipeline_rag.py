"""ETL pipeline for RAG."""

import json
import logging
import os
import pandas as pd
from tqdm import tqdm
import openai
from openai import AzureOpenAI

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, model_validator, ValidationError

from app.config import settings

# logger
logger = logging.getLogger("ETL")
logger.setLevel(logging.DEBUG)
logger.propagate = False
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(handler)

class QuestionAnswer(BaseModel):
    question: str
    answer: str

# wrapper model to hold multiple question/answer pairs
class QuestionAnswerList(BaseModel):
    questions_answers: list[QuestionAnswer] # relevant questions and their answers
    open_questions: list[str] # relevant questions with no answer in the text

    @model_validator(mode='after')
    def check_counts(self):
        """ensure we have `number_of_questions` relevant Q/A pairs and `number_of_questions` open questions"""
        if len(self.questions_answers) != number_of_questions:
            raise ValueError(f"Expected exactly {number_of_questions} question/answer pairs in 'questions_answers'")
        if len(self.open_questions) != number_of_questions:
            raise ValueError(f"Expected exactly {number_of_questions} items in 'open_questions'")
        return self

number_of_questions = 10 # number of question-answer pairs and open questions to generate for each document
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
        azure_endpoint = settings.AZURE_OPENAI_ENDPOINT, 
        azure_ad_token_provider=token_provider,
        api_version=settings.AZURE_OPENAI_CHAT_API_VERSION
    )

    completion = client.beta.chat.completions.parse(
        model=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
        messages=[
            {
                "role": "system", 
                "content": f"Generate {number_of_questions} relevant questions and answers based on the provided text. Also generate {number_of_questions} additional relevant questions whose answers are NOT present in the text (these should be open-ended/follow-up questions). Return them as a JSON object with a top-level array named 'questions_answers' (each entry containing 'question' and 'answer') and an array named 'open_questions' containing {number_of_questions} question strings whose answers are not in the text."
            },
            {
                "role": "user", 
                "content": text
            },
        ],
        response_format=QuestionAnswerList,
    )

    try:
        llm_answer = completion.choices[0].message.parsed
    except ValidationError as e:
        print('Validation error:', e)
        return questions_answers_list

    for question_answer_pair in getattr(llm_answer, 'questions_answers', []):
        tmp = {
            "question": question_answer_pair.question,
            "answer": question_answer_pair.answer
        }
        questions_answers_list.append(tmp)

    for question_answer_pair in getattr(llm_answer, 'open_questions', []):
        tmp = {
            "question": question_answer_pair,
            "answer": "The document does not provide an answer to this question."
        }
        questions_answers_list.append(tmp)

    return questions_answers_list

def extract(file_name: str, encoding: str) -> list:
    """Extract data from source."""
    full_path = os.path.join("data/raw/", file_name)
    df = pd.read_csv(full_path, encoding=encoding)
    extracted_data = df.to_dict(orient='records')
    return extracted_data

def transform(datasets: list) -> list:
    """Transform the input data by tranlating the `text` column and generating Q&A."""
    for dict_ in tqdm(datasets):
        text = dict_["text"]
        dict_["text_translated"] = german2english(text)
        dict_["questions_answers"] = generate_questions_answers(dict_["text_translated"])

    return datasets

def load(transformed_dataset: list, file_name: str, encoding: str) -> None:
    """Store transformed data."""
    file_name_extension = os.path.splitext(file_name)[1]
    file_name = file_name.replace(file_name_extension, '_transformed.json')
    full_path = os.path.join("data/processed/", file_name)
    with open(full_path, 'w', encoding=encoding) as f:
        json.dump(transformed_dataset, f, ensure_ascii=False, indent=2)

def test_rag() -> None:
    """Test retrievarl on RAG."""
    pass


if __name__ == "__main__":
    datasets = [
        {
            "file_name": "data_overview_ver4(quality_new).csv",
            "encoding": "utf-8-sig",
        }
    ]

    for file_name, encoding in [(d["file_name"], d["encoding"]) for d in datasets]:
        logger.debug(f"Processing file: {file_name} with encoding: {encoding}")
        extracted_data = extract(file_name, encoding)
        rag_data = transform(extracted_data)
        load(rag_data, file_name, encoding)
        test_rag()