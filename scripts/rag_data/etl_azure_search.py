"""ETL script to create an Azure Cognitive Search."""

import json
import logging
from pathlib import Path

import pandas as pd
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
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

from app.config import settings
from scripts.assessment_data.generate_assessment_dataset import german2english

logger = logging.getLogger("ETL Azure Search")
logger.setLevel(logging.DEBUG)
logger.propagate = False
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(handler)


class AzureEmbeddingWrapper:
    """Wrapper for Azure OpenAI embeddings to be used with SemanticChunker.

    SemanticChunker expects methods `embed_documents` and `embed_query`.
    """

    def embed_documents(self: "AzureEmbeddingWrapper", texts: list) -> list:
        """Return a list of embeddings for a list of texts."""
        return [get_embedding(text) for text in texts]

    def embed_query(self: "AzureEmbeddingWrapper", text: str) -> list:
        """Return a single embedding for a query."""
        return get_embedding(text)


def get_embedding(text: str) -> list:
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
        azure_ad_token_provider=token_provider,
    )

    title_generation_chain = title_generation_prompt | chat_client

    return title_generation_chain.invoke({"input": chunk}).content


# text splitter used to chunk documents
azure_embeddings = AzureEmbeddingWrapper()
text_splitter = SemanticChunker(azure_embeddings)

# embedding model
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
)
embedding_client = AzureOpenAI(
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    azure_deployment=settings.AZURE_OPENAI_SEARCH_EMBEDDING_DEPLOYMENT,
    api_version=settings.AZURE_OPENAI_SEARCH_EMBEDDING_API_VERSION,
    azure_ad_token_provider=token_provider,
)

# initialize azure search client
index_client = SearchIndexClient(
    settings.AZURE_SEARCH_ENDPOINT, AzureKeyCredential(settings.AZURE_AI_SEARCH_API_KEY)
)

# configure vectorizer
vectorizer = AzureOpenAIVectorizer(
    vectorizer_name="myTextEmbedding3LargeVectorizer",
    parameters=AzureOpenAIVectorizerParameters(
        resource_url=settings.AZURE_OPENAI_ENDPOINT,
        deployment_name=settings.AZURE_OPENAI_SEARCH_EMBEDDING_DEPLOYMENT,
        api_key=settings.AZURE_OPENAI_CHAT_KEY,
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
    SearchableField(name="Data_Gathered_On", type=SearchFieldDataType.DateTimeOffset),
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
index_name = "qualitat-dev"
index = SearchIndex(
    name=index_name,
    fields=fields,
    vector_search=vector_search,
    semantic_search=semantic_search,
)

# create the index
try:
    result = index_client.create_index(index)
    logger.debug("Index %s created successfully", index_name)
except HttpResponseError as e:
    logger.debug("Azure API error creating index: %s", e)
except (ValueError, TypeError) as e:
    logger.debug("Local error creating index: %s", e)


# process the row data to generate the fields that will be pushed to the index
documents = []
xlsx_file_path = "tests/data/raw/"
xlsx_file_name = "data_overview_ver4"
df = pd.read_excel(
    Path(xlsx_file_path) / f"{xlsx_file_name}.xlsx", sheet_name="quality_new"
)
chunk_id = 0
for i, row in df.iterrows():
    logger.debug("Processing row %d", i)
    list_of_chunks = text_splitter.create_documents([row["text"]])
    for chunk in list_of_chunks:
        chunk_content = chunk.page_content.strip()
        if not chunk_content:
            continue
        document = {
            "chunk_id": f"doc_{chunk_id}",
            "DocumentID": row["DocumentID"],
            "Link": row["Link"],
            "Title": row["Title"],
            "Title_Chunk": generate_title(chunk_content),
            "Category": row["Category"],
            "Local_Path": row["Local_Path"],
            "Local_Path_PDF": row["Local_Path_PDF"],
            "Date_Last_Modified": row["Date_Last_Modified"],
            "Data_Gathered_On": row["Data_Gathered_On"],
            "chunk": chunk_content,
            "chunk_translated": german2english(chunk_content),
            "Keyword": row["Keyword"],
            "Example_Questions": row["Example_Questions"].split(","),
            "text_vector": get_embedding(chunk_content),
        }
        documents.append(document)
        chunk_id += 1

# store the data locally as json (for debugging purposes)
processed_data_path = Path("scripts/rag_data/data/processed/")
with Path.open(
    processed_data_path / f"{xlsx_file_name}_azure_semantic_search.json", "w"
) as f:
    json.dump(documents, f, indent=2, ensure_ascii=False)


# upload the processed data to the index
search_client = SearchClient(
    settings.AZURE_SEARCH_ENDPOINT,
    index_name,
    AzureKeyCredential(settings.AZURE_AI_SEARCH_API_KEY),
)
try:
    result = search_client.upload_documents(documents)
    logger.debug("Uploaded %d documents", len(documents))
    for res in result:
        logger.debug("Document %s: %s", res.key, res.succeeded)
except HttpResponseError as e:
    logger.debug("Azure API error uploading documents: %s", e)
except (ValueError, TypeError) as e:
    logger.debug("Local error uploading documents: %s", e)
