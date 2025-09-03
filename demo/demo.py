"""Demo script of kioskbot."""

import logging
import os

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from langchain_core.prompts import (
    ChatPromptTemplate,
)
from langchain_openai import AzureChatOpenAI

from app.agent.chatbot_azure import ChatBot

logger = logging.getLogger("Kioskbot")
logger.setLevel(logging.DEBUG)
logger.propagate = False
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(handler)


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

    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )

    chat_client = AzureChatOpenAI(
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        api_version=os.getenv("AZURE_OPENAI_CHAT_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_ad_token_provider=token_provider,
    )

    translation_chain = translation_prompt | chat_client

    return translation_chain.invoke({"input": text}).content


def main() -> None:
    """Main function."""
    load_dotenv()

    chatbot_test = ChatBot()

    while True:
        query = input("\nYou: ")
        query_response = chatbot_test.get_response_from_vectordb(query)
        logger.debug("Output: %s", query_response["output"])
        translated_text = german2english(query_response["output"])
        logger.debug("Translated output: %s", translated_text)


if __name__ == "__main__":
    main()
