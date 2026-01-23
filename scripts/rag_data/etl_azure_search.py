"""ETL script to create an Azure Cognitive Search."""

import json
import logging
import sys
from pathlib import Path

import pandas as pd
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from langchain_core.prompts import ChatPromptTemplate
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import AzureChatOpenAI
from openai import AzureOpenAI
from argparse import ArgumentParser
from app.config import settings
from scripts.assessment_data.generate_assessment_dataset import german2english

logger = logging.getLogger("ETL Azure Search")
logger.setLevel(logging.DEBUG)
logger.propagate = False
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(handler)


http_status_bad_request = 400
http_status_not_found = 404


class AzureEmbeddingWrapper:
    """Wrapper for Azure OpenAI embeddings to be used with SemanticChunker.

    SemanticChunker expects methods `embed_documents` and `embed_query`.
    """

    def __init__(self: "AzureEmbeddingWrapper", embedding_client: AzureOpenAI) -> None:
        """Initialize with an AzureOpenAI embedding client."""
        self._embedding_client = embedding_client

    def embed_documents(self: "AzureEmbeddingWrapper", texts: list) -> list:
        """Return a list of embeddings for a list of texts."""
        return [get_embedding(self._embedding_client, text) for text in texts]

    def embed_query(self: "AzureEmbeddingWrapper", text: str) -> list:
        """Return a single embedding for a query."""
        return get_embedding(self._embedding_client, text)


def get_embedding(embedding_client: AzureOpenAI, text: str) -> list:
    """Get embedding for a given text using Azure OpenAI."""
    resp = embedding_client.embeddings.create(
        input=[text],
        model=settings.AZURE_OPENAI_SEARCH_EMBEDDING_DEPLOYMENT,
    )
    return resp.data[0].embedding


def generate_title(chunk: str) -> str:
    """Generate a title for a given text chunk using Azure OpenAI."""
    title_generation_system_prompt = """Given the following document chunk, generate a concise and informative title that summarizes its main topic or purpose.

    Document chunk: {input}
    The title generated is: {{output}}
    """  # noqa: E501

    title_generation_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", title_generation_system_prompt),
            ("human", "{input}"),
        ]
    )

    chat_client = AzureChatOpenAI(
        azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
        api_version=settings.AZURE_OPENAI_CHAT_API_VERSION,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_key=settings.AZURE_OPENAI_PRIMARY_KEY,
    )
    title_generation_chain = title_generation_prompt | chat_client
    try:
        return title_generation_chain.invoke({"input": chunk}).content
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Title generation failed (%s). Using 'No title generated'.",
            type(exc).__name__,
        )
        return "No title generated"



def run_etl(  # noqa: PLR0915
    xlsx_file_path: str,
    sheet_name: str,
    index_name: str,
    output_dir_path: Path,
) -> dict:
    """Run the ETL process to create index, process docs and upload them.

    Returns a dict with summary information.
    """
    # text splitter used to chunk documents

    embedding_client = AzureOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        azure_deployment=settings.AZURE_OPENAI_SEARCH_EMBEDDING_DEPLOYMENT,
        api_version=settings.AZURE_OPENAI_SEARCH_EMBEDDING_API_VERSION,
        api_key=settings.AZURE_OPENAI_PRIMARY_KEY,
    )

    azure_embeddings = AzureEmbeddingWrapper(embedding_client)
    text_splitter = SemanticChunker(azure_embeddings)

    # initialize azure search client
    index_client = SearchIndexClient(
        settings.AZURE_SEARCH_ENDPOINT,
        AzureKeyCredential(settings.AZURE_SEARCH_SERVICE_PRIMARY_ADMIN_KEY),
    )

    # configure vectorizer
    vectorizer = AzureOpenAIVectorizer(
        vectorizer_name="myTextEmbedding3LargeVectorizer",
        parameters=AzureOpenAIVectorizerParameters(
            resource_url=settings.AZURE_OPENAI_VECTORIZER_ENDPOINT,
            deployment_name=settings.AZURE_OPENAI_SEARCH_EMBEDDING_DEPLOYMENT,
            api_key=settings.AZURE_OPENAI_PRIMARY_KEY,
            model_name=settings.AZURE_OPENAI_SEARCH_EMBEDDING_DEPLOYMENT,
        ),
    )

    # configure vector search with algorithm (see vector profiles in azure search)
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="myHnswAlgorithm",
                parameters={
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500,
                    "metric": "cosine",
                },
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="myVectorProfile",
                algorithm_configuration_name="myHnswAlgorithm",
                vectorizer_name="myTextEmbedding3LargeVectorizer",
            )
        ],
        vectorizers=[vectorizer],
    )

    # configure semantic search (see semantic configurations in azure search)
    semantic_config = SemanticConfiguration(
        name="mySemanticConfig",
        prioritized_fields={
            "title_field": SemanticField(field_name="Title_Chunk"),
            "content_fields": [
                SemanticField(field_name="chunk"),
                SemanticField(field_name="Example_Questions"),
            ],
            "keywords_fields": [
                SemanticField(field_name="Keyword"),
            ],
        },
    )

    semantic_search = SemanticSearch(configurations=[semantic_config])

    # define index fields (see fields in azure search)
    fields = [
        SimpleField(
            name="chunk_id", type=SearchFieldDataType.String, key=True
        ),  # SimpleField is used for fields that are not meant to be full-text searchable, but are retrievable and can be used as keys or for tracking, filtering, or retrieving information (e.g., IDs, flags, metadata, or any field you do not want to be full-text searchable) # noqa: E501
        SearchableField(
            name="DocumentID", type=SearchFieldDataType.String
        ),  # Searchable and retrievable fields
        SearchableField(
            name="Link", type=SearchFieldDataType.String
        ),  # SearchableField is used for fields that will be full-text searchable
        SearchableField(name="Title", type=SearchFieldDataType.String),
        SearchableField(name="Title_Chunk", type=SearchFieldDataType.String),
        SearchableField(name="Category", type=SearchFieldDataType.String),
        SearchableField(name="Local_Path", type=SearchFieldDataType.String),
        SearchableField(name="Local_Path_PDF", type=SearchFieldDataType.String),
        SearchableField(name="Date_Last_Modified", type=SearchFieldDataType.String),
        SearchableField(
            name="Data_Gathered_On", type=SearchFieldDataType.DateTimeOffset
        ),
        SearchableField(name="chunk", type=SearchFieldDataType.String),
        SearchableField(name="chunk_translated", type=SearchFieldDataType.String),
        SearchableField(name="Keyword", type=SearchFieldDataType.String),
        SearchField(
            name="Example_Questions",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            facetable=False,  # False because it is used to filter expressions in search queries (e.g., with numbers, booleans, dates, etc.) # noqa: E501
            filterable=False,  # true when you need to compute facets based on field values, e.g. get a count of documents per Category # noqa: E501
        ),
        SearchField(
            name="text_vector",  # field name where vector embeddings will be stored
            type=SearchFieldDataType.Collection(
                SearchFieldDataType.Single
            ),  # defines the data type as a collection of single-precision floating-point numbers (the standard format for embeddings/vectors) # noqa: E501
            vector_search_dimensions=3072,  # text-embedding-3-large dimensions
            vector_search_profile_name="myVectorProfile",
            hidden=False,
            stored=True,
        ),  # SearchField is a more general field type that can be used for storing vectors (e.g., embeddings for semantic, list of string, etc.) or vector search. # noqa: E501
    ]

    # intialize the index
    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )

    try:
        index_client.delete_index(index_name)
        logger.info("Deleted existing index '%s'.", index_name)
    except HttpResponseError as e:
        if e.status_code != http_status_not_found:
            logger.exception("Azure API error deleting index:")
            sys.exit(1)

    # create the index
    try:
        index_client.create_index(index)
        logger.debug("Index %s created successfully", index_name)
    except HttpResponseError as e:
        if (
            e.status_code == http_status_bad_request
            and f"Message: Cannot create index '{index_name}' because it already exists."  # noqa: E501
            in str(e)
        ):
            logger.exception(
                "Index '%s' already exists. Stopping execution.", index_name
            )
        else:
            logger.exception("Azure API error creating index:")
        sys.exit(1)
    except (ValueError, TypeError):
        logger.exception("Local error creating index:")
        sys.exit(1)

    # process the row data to generate the fields that will be pushed to the index
    documents = []
    df = pd.read_excel(Path(xlsx_file_path), sheet_name=sheet_name)
    chunk_id = 0
    logger.info("Total number of %d rows", len(df))
    for i, row in df.iterrows():
        logger.debug("Processing row %d", i)
        list_of_chunks = text_splitter.create_documents([row["text"]])
        for chunk in list_of_chunks:
            chunk_content = chunk.page_content.strip()
            if not chunk_content:
                continue
            title_for_chunk = generate_title(chunk_content)
            vector = get_embedding(embedding_client, chunk_content)

            try:
                translated_text = german2english(chunk_content)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Translation failed (%s). Using empty translation.",
                    type(exc).__name__,
                )
                translated_text = ""

            document = {
                "chunk_id": f"doc_{chunk_id}",
                "DocumentID": row["DocumentID"],
                "Link": row["Link"],
                "Title": row["Title"],
                "Title_Chunk": title_for_chunk,
                "Category": row["Category"],
                "Local_Path": row["Local_Path"],
                "Local_Path_PDF": row["Local_Path_PDF"],
                "Date_Last_Modified": row["Date_Last_Modified"],
                "Data_Gathered_On": row["Data_Gathered_On"],
                "chunk": chunk_content,
                "chunk_translated": translated_text,
                "Keyword": row["Keyword"],
                "Example_Questions": row["Example_Questions"].split(","),
                "text_vector": vector,
            }
            documents.append(document)
            chunk_id += 1

    environment = getattr(settings, "ENV", "dev")
    with Path.open(
        output_dir_path
        / f"processed_data_azure_semantic_search_{environment}.json",
        "w",
    ) as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)

    # upload the processed data to the index
    search_client = SearchClient(
        settings.AZURE_SEARCH_ENDPOINT,
        index_name,
        AzureKeyCredential(settings.AZURE_SEARCH_SERVICE_PRIMARY_ADMIN_KEY),
    )
    upload_result = None
    try:
        upload_result = search_client.upload_documents(documents)
        logger.debug("Uploaded %d documents", len(documents))
        for res in upload_result:
            logger.debug("Document %s: %s", res.key, res.succeeded)
    except HttpResponseError as e:
        logger.debug("Azure API error uploading documents: %s", e)
    except (ValueError, TypeError) as e:
        logger.debug("Local error uploading documents: %s", e)

    return {
        "index_name": index_name,
        "chunk_count": len(documents),
    }


def main() -> None:
    """Simple CLI entrypoint for the ETL script."""
    arg_parser = ArgumentParser(
        description="ETL script to create an Azure Cognitive Search."
    )
    arg_parser.add_argument(
        "--customer_name",
        type=str,
        required=True,
        help="The name of the customer.",
    )
    args = arg_parser.parse_args()
    customer_name = args.customer_name
    index_name = f"kb-{customer_name}"
    output_dir = f"scripts/rag_data/data/processed/{customer_name}"
    base_dir = Path("scripts/crawler/data") / customer_name
    if not base_dir.exists():
        error_message = (
            "No crawl output found. Run the crawler first for customer "
            f"'{customer_name}'."
        )
        raise FileNotFoundError(error_message)
    timestamp_dirs = [
        entry
        for entry in base_dir.iterdir()
        if entry.is_dir() and entry.name.isdigit()
    ]
    data_dir = (
        max(timestamp_dirs, key=lambda path: int(path.name))
        if timestamp_dirs
        else base_dir
    )
    xlsx_file_path = str(data_dir / "processed_data.xlsx")
    sheet_name = "Sheet1"
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    summary = run_etl(
        xlsx_file_path,
        sheet_name,
        index_name,
        output_dir_path,
    )
    logger.info("ETL finished: %s", summary)

if __name__ == "__main__":
    main()