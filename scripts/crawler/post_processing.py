import json
import os
import re
import logging
from pathlib import Path
from app.config import settings
from openai import AzureOpenAI
from pydantic import BaseModel
import requests
import pandas as pd
from tqdm import tqdm


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

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
    
    logger.info("="*80)
    logger.info("FILTERING EMPTY OR SHORT CONTENT")
    logger.info("="*80)
    
    filtered_out = []
    valid_data = []
    
    for row in all_data:
        content = row.get('content')
        url = row.get('url', 'Unknown URL')
        if content is None or len(content) < 10:
            filtered_out.append({'url': url, 'content_length': len(content) if content else 0})
        else:
            valid_data.append(row)
    if filtered_out:
        logger.warning(f"Found {len(filtered_out)} entries with empty or short content (< 10 chars):")
        for i, item in enumerate(filtered_out, start=1):
            logger.warning(f"  {i}. {item['url']} (content length: {item['content_length']})")
    else:
        logger.info("No entries with empty or short content found.")
    
    logger.info(f"Processing {len(valid_data)} valid entries out of {len(all_data)} total entries")
    logger.info("="*80)
    
    processed_data = []
    for idx, row in tqdm(enumerate(valid_data), total=len(valid_data), desc="Processing data"):
        DocumentID = f"{customer_name}_{idx}"
        url = row.get('url', 'None')
        text = row['content']  
        
        if url.endswith(".html"):
            Title = text.split("\n\n")[0] if text else "Untitled"
            Category = "Website"
        elif url.endswith(".pdf"):
            Title = row.get('filename', 'Untitled')
            Category = "PDF"
        elif url=="None":
            Title = "Untitled"  
            Category = "Other"
        else:
            Title = text.split("\n\n")[0] if text else "Untitled"
            Category = "Website"
            
        Local_Path = "Not Specified"
        Local_Path_PDF = "Not Specified"
        Date_Last_Modified = "Not Specified"
        Data_Gathered_On = row.get('timestamp', 'Not Specified')
        page_type = find_page_type(text)
        prompt = keyword_question_generation_system_prompt.format(url=url, page_type=page_type, text=text)
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
            "Link": url,
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

def extract_urls_from_text(text: str) -> set:
    """Extract all URLs from text content."""
    url_pattern = r'https?://[^\s\)\]<>]+'
    urls = re.findall(url_pattern, text)
    return set(url.rstrip('.,;:') for url in urls)


def check_url_valid(url: str, timeout: int = 10) -> bool:
    """Check if a URL is valid and accessible."""
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        if response.status_code == 405:
            response = requests.get(url, timeout=timeout, allow_redirects=True, stream=True)
        return 200 <= response.status_code < 400
    except Exception:
        return False


def verify_urls_in_processed_data(processed_file: Path) -> list:
    """Read processed data, extract URLs from text, and check validity."""
    logger.info("="*80)
    logger.info("VERIFYING URLs IN PROCESSED DATA")
    logger.info("="*80)
    
    all_urls = set()
    
    df = pd.read_excel(processed_file, engine='openpyxl')
    for text in df['text']:
        if pd.notna(text):  
            urls = extract_urls_from_text(str(text))
            all_urls.update(urls)
    
    logger.info(f"Found {len(all_urls)} unique URLs in processed data")
    

    invalid_urls = []
    for i, url in tqdm(enumerate(sorted(all_urls)), total=len(all_urls), desc="Checking URLs"):
        if not check_url_valid(url):
            invalid_urls.append(url)
    return invalid_urls

def find_empty_text_content(processed_file: Path) -> list:
    """Find entries with empty text content."""
    logger.info("="*80)
    logger.info("FINDING EMPTY TEXT CONTENT")
    logger.info("="*80)
    df = pd.read_excel(processed_file, engine='openpyxl')
    empty_text_content = df[df['text'].isna()]
    return empty_text_content


def main():
    jsonl_file = Path("scripts/crawler/data/qse/qse_content.jsonl")
    customer_name = "qse"
    logger.info("Starting post-processing...")
    all_data = post_process_data(jsonl_file, customer_name)
    output_file = Path(f"scripts/crawler/data/{customer_name}/processed_data.xlsx")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(all_data)
    df.to_excel(output_file, index=False, engine='openpyxl')
    logger.info(f"Processed {len(all_data)} entries and saved to {output_file}")
    invalid_urls = verify_urls_in_processed_data(output_file)
    
    logger.info("="*80)
    logger.info("URL VERIFICATION RESULTS")
    logger.info("="*80)
    if invalid_urls:
        logger.warning(f"Found {len(invalid_urls)} URLs which may be broken. It is recommended to verify manually and remove from website.:")
        for i, url in enumerate(invalid_urls, start=1):
            logger.warning(f"  {i}. {url}")
    else:
        logger.info("All URLs are valid!")
    logger.info("="*80)

    empty_text_content = find_empty_text_content(output_file)
    logger.info("="*80)
    logger.info("EMPTY TEXT CONTENT")
    logger.info("="*80)
    if not empty_text_content.empty:
        logger.warning(f"Found {len(empty_text_content)} entries with empty text content.")
        for i, row in empty_text_content.iterrows():
            logger.warning(f"  {i+1}. {row['Link']}")
    else:
        logger.info("No entries with empty text content found.")

if __name__ == "__main__":
    main()
    