"""Kioskbot class definition and methods."""

import logging
import os
import re

import ftfy
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from dotenv import load_dotenv
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import AzureChatOpenAI
from openai import AzureOpenAI

from app.integration.prompt_templates import qa_prompt, translation_prompt
from app.integration.query import Source

logger = logging.getLogger("Kioskbot")
logger.setLevel(logging.DEBUG)
logger.propagate = False
handler = logging.StreamHandler()
handler.setLevel(logging.ERROR)
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(handler)

load_dotenv()
AZURE_SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT")
AZURE_AI_SEARCH_INDEX_NAME = os.environ.get("AZURE_AI_SEARCH_INDEX_NAME")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT")
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_SEARCH_EMBEDDING_DEPLOYMENT = os.environ.get(
    "AZURE_OPENAI_SEARCH_EMBEDDING_DEPLOYMENT"
)
AZURE_AI_SEARCH_API_KEY = os.environ.get("AZURE_AI_SEARCH_API_KEY")
AZURE_OPENAI_SEARCH_EMBEDDING_API_VERSION = os.environ.get(
    "AZURE_OPENAI_SEARCH_EMBEDDING_API_VERSION"
)
AZURE_OPENAI_CHAT_API_VERSION = os.environ.get("AZURE_OPENAI_CHAT_API_VERSION")

credential = DefaultAzureCredential()
search_credential = AzureKeyCredential(AZURE_AI_SEARCH_API_KEY)
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
)


class ChatBot:
    """ChatBot class to interact with Azure OpenAI and Azure AI Search."""

    def __init__(self) -> None:
        """Initialize the ChatBot with Azure clients and prompt chains."""
        logger.info("Initializing ChatBot and Azure clients")
        self.search_client = SearchClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            index_name=AZURE_AI_SEARCH_INDEX_NAME,
            credential=search_credential,
        )
        self.embedding_client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            azure_deployment=AZURE_OPENAI_SEARCH_EMBEDDING_DEPLOYMENT,
            api_version=AZURE_OPENAI_SEARCH_EMBEDDING_API_VERSION,
            azure_ad_token_provider=token_provider,
        )
        self.chat_client = AzureChatOpenAI(
            azure_deployment=AZURE_OPENAI_CHAT_DEPLOYMENT,
            api_version=AZURE_OPENAI_CHAT_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            azure_ad_token_provider=token_provider,
        )
        self.qa_chain = create_stuff_documents_chain(
            llm=self.chat_client, prompt=qa_prompt, document_variable_name="context"
        )
        self.translation_chain = translation_prompt | self.chat_client
        self.chat_history = [AIMessage(content="Hi")]
        self.interaction_count = 0
        logger.info("ChatBot initialization complete")

    def clean_and_truncate_query(self: "ChatBot", query_text: str) -> str:
        """Truncates the query text to a maximum of 100 terms."""
        max_terms = 100
        query_terms = re.findall(r"\w+", query_text)
        if len(query_terms) > max_terms:
            query_text = " ".join(query_terms[:max_terms])

        return query_text

    def embed_query(self: "ChatBot", query_text: str) -> list[float]:
        """Embeds the query text into a vector using the Azure OpenAI embedding model.

        Args:
            query_text (str): The text to embed.

        Returns:
            list: The embedding of the query text.
        """
        resp = self.embedding_client.embeddings.create(
            input=[query_text], model=AZURE_OPENAI_SEARCH_EMBEDDING_DEPLOYMENT
        )
        return resp.data[0].embedding

    def get_top_k_vector_results(self: "ChatBot", query_text: str, k: int = 4) -> list:
        """Retrieves the top k vector results from the Azure AI Search index.

        Args:
            query_text (str): The text to search for.
            k (int): The number of results to return.

        Returns:
            list: The top k vector results.
        """
        query_embedding = self.embed_query(query_text)
        vectorized_query = VectorizedQuery(
            vector=query_embedding, kind="vector", fields="text_vector"
        )
        results = self.search_client.search(
            vector_queries=[vectorized_query],
            search_text=query_text,
            top=k,
            search_fields=["chunk"],
            select=[
                "chunk",
                "DocumentID",
                "Link",
                "Category",
                "Title",
                "Date_Last_Modified",
                "Data_Gathered_On",
            ],
        )
        return list(results)

    def format_results_for_chain(self: "ChatBot", results: list) -> list[Document]:
        """Format results as LangChain Document objects for chain and chat history.

        Args:
            results (list): The results to format.

        Returns:
            list: The formatted results as a list of Document objects.
        """
        docs = []
        for document in results:
            page_content = ftfy.fix_text(document.get("chunk"))
            if not page_content:
                page_content = "Not Specified"
            metadata = {
                "score": float(document.get("@search.score")),
                "DocumentID": document.get("DocumentID"),
                "Link": document.get("Link") or "Not Specified",
                "Category": document.get("Category") or "Not Specified",
                "Title": document.get("Title") or "Not Specified",
                "Date_Last_Modified": document.get("Date_Last_Modified")
                or "Not Specified",
                "Data_Gathered_On": document.get("Data_Gathered_On") or "Not Specified",
            }
            docs.append(Document(page_content=page_content, metadata=metadata))
        return docs

    def format_results_for_frontend(
        self: "ChatBot", results: list[Document]
    ) -> list[Source]:
        """Format results as Source objects for returning to the frontend.

        Args:
            results (list): The results to format.

        Returns:
            list: The formatted results as a list of Source objects.
        """
        page_content_list = []
        for document in results:
            page_content = ftfy.fix_text(document.get("chunk"))
            if not page_content:
                page_content = "Not Specified"
            document_score = float(document.get("@search.score"))
            document_location = document.get("DocumentID")
            document_url = document.get("Link") or "Not Specified"
            document_category = document.get("Category") or "Not Specified"
            document_title = document.get("Title") or "Not Specified"
            date_last_mod = document.get("Date_Last_Modified") or "Not Specified"
            data_gathered_on = document.get("Data_Gathered_On") or "Not Specified"
            page_content_list.append(
                Source(
                    document_location=document_location,
                    page_content=page_content,
                    document_url=document_url,
                    category=document_category,
                    title=document_title,
                    gathered_on=data_gathered_on,
                    modified=date_last_mod,
                    score=document_score,
                )
            )
        return page_content_list

    def get_response_from_vectordb(self: "ChatBot", query_text: str) -> dict:
        """Retrieve respose from the vectordb and generate a response using the chain.

        The user query is first translated to german and
        responses from the Azure AI Search is retrieved and
        formatted for the frontend as well as for the QA chain.

        Args:
            query_text (str): The text to search for.

        Returns:
            dict: The response from the vectordb as a list of dict or json objects.
        """
        logger.info("Processing query: %s", query_text)
        try:
            translated_query = self.translation_chain.invoke({"input": query_text})
            if hasattr(translated_query, "content"):
                translated_query = translated_query.content
            query_text_cleaned = self.clean_and_truncate_query(translated_query)
            logger.info("translated query: %s", translated_query)
            logger.info("cleaned query: %s", query_text_cleaned)
            retrieved_docs = self.get_top_k_vector_results(query_text_cleaned)
            docs_for_chain = self.format_results_for_chain(retrieved_docs)
            docs_for_frontend = self.format_results_for_frontend(retrieved_docs)
            logger.info("Invoking QA chain for query: %s", query_text)
            response = self.qa_chain.invoke(
                {
                    "context": docs_for_chain,
                    "input": query_text,
                    "chat_history": self.chat_history,
                }
            )
            if hasattr(response, "content"):
                response = response.content
            self.add_to_chat_history(query_text, response, docs_for_chain)
            logger.info("Response generated for query: %s", query_text)
            return {"output": ftfy.fix_text(response), "sources": docs_for_frontend}
        except Exception:
            logger.exception("Error in get_response_from_vectordb:")
            raise

    def add_to_chat_history(
        self: "ChatBot", query_text: str, response: str, retrieved_docs: list
    ) -> list:
        """Add the latest interaction to the chat history."""
        self.chat_history.extend(
            [
                HumanMessage(content=query_text),
                AIMessage(content=response, metadata={"sources": retrieved_docs}),
            ]
        )
        self.interaction_count += 1
        max_pairs = 3
        while (len(self.chat_history) - 1) // 2 > max_pairs:
            del self.chat_history[1:3]
        logger.debug(
            "Chat history updated. Interaction count: %s", self.interaction_count
        )
        return self.chat_history


chatbot_test = ChatBot()
