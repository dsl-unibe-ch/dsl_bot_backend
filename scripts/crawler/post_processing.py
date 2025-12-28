import json
import os
from pathlib import Path
from app.config import settings
from openai import AzureOpenAI
from pydantic import BaseModel

keyword_question_generation_system_prompt = """

You are generating metadata for a RAG knowledge base entry.

Goal:
1) Propose 3-5 KEYWORDS that help retrieval.
2) Propose 2-3 MATCHING QUESTIONS that real users might ask and that are answerable from the provided data.

Strict rules:
- Do NOT invent facts.
- Every question must be answerable from either (a) structured_facts or (b) cleaned_text.
- If the page is mostly a contact/ service list, prioritize "who/whom/contact/email/role/responsible" questions.
- If the page is mostly a form/ resource list, prioritize "form/ resource/ download/ pdf" questions.
- If the page is mostly a deadline list, prioritize "deadline/ frist/ due date" questions.
- Output JSON only, matching the schema.

Inputs:
URL: {url}
PAGE_TYPE: {page_type}
TEXT: {text}

Output schema:
{{
  "keywords": ["kw1", "kw2", "kw3"],
  "questions": [
    "q1",
    "q2",
    "q3"
  ]
}}

"""


class KeywordQuestionResponse(BaseModel):
    """Schema for keyword and question generation response."""
    keywords: list[str]
    questions: list[str]


def find_page_type(text: str) -> str:
    text = text.lower()
    page_type = []
    count_emails = text.count("@unibe.ch")
    count_pdfs = text.count("pdf")
    count_downloads = text.count("download")
    count_formulars = text.count("formular")
    count_contacts = text.count("kontakt")
    count_beratungen = text.count("beratung")
    count_zustaendig = text.count("zuständig")
    count_ansprechpartner = text.count("ansprechpartner")
    count_deadlines = text.count("fristen")

    if count_emails>0 or count_contacts>0 or count_zustaendig>0 or count_ansprechpartner>0 or count_beratungen>0:
        page_type.append("contact/service")
    if count_pdfs>0 or count_downloads>0 or count_formulars>0:
        page_type.append("forms/resources")
    if count_deadlines>0:
        page_type.append("deadlines")
    if len(page_type) == 0:
        page_type.append("other")
    return page_type
   

def post_process_data(jsonl_file: Path, customer_name: str) -> list:

    client = AzureOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_key=settings.AZURE_OPENAI_PRIMARY_KEY,
        api_version=settings.AZURE_OPENAI_CHAT_API_VERSION,
    )
    all_data = []
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            all_data.append(data)
    
    processed_data = []
    for idx, row in enumerate(all_data):
        DocumentID = f"{customer_name}_{idx}"
        Link = row['url']
        Title = row['content'].split("\n\n")[0] if row.get('content') else "Untitled"
        Category = "Website"
        Local_Path = "Not Specified"
        Local_Path_PDF = "Not Specified"
        Date_Last_Modified = "Not Specified"
        Data_Gathered_On = row['timestamp']
        text = row['content']
        Keyword = "None"
        Example_Questions = "None"
        page_type = find_page_type(text)
        prompt = keyword_question_generation_system_prompt.format(url=Link, page_type=page_type, text=text)
        response = client.beta.chat.completions.parse(
            model=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=[
                {"role": "system", "content": prompt},
            ],
            response_format=KeywordQuestionResponse,
        )
        response_json = response.choices[0].message.parsed
        keywords = ", ".join(response_json.keywords)
        questions = ", ".join(response_json.questions)  
        new_row = {
            "DocumentID": DocumentID,
            "Link": Link,
            "Title": Title,
            "Category": Category,
            "Local_Path": Local_Path,
            "Local_Path_PDF": Local_Path_PDF,
            "Date_Last_Modified": Date_Last_Modified,
            "Data_Gathered_On": Data_Gathered_On,
            "text": text,
            "Keyword": keywords,
            "Example_Questions": questions,
            "page_type": page_type,
        }
        processed_data.append(new_row)
    return processed_data

def main():
    jsonl_file = Path("scripts/crawler/data/qse/qse_content.jsonl")
    customer_name = "qse"
    all_data = post_process_data(jsonl_file, customer_name)
    output_file = Path(f"scripts/crawler/data/{customer_name}/processed_data.jsonl")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding='utf-8') as f:
        for row in all_data:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Processed {len(all_data)} entries and saved to {output_file}")

if __name__ == "__main__":
    main()
    