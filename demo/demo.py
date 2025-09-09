"""Demo script of kioskbot."""

import logging
import uuid

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI

from app.agent.chatbot_azure import ChatBot
from app.agent.feedback import Feedback
from app.agent.query import QueryInput
from app.config import settings

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
        azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
        api_version=settings.AZURE_OPENAI_CHAT_API_VERSION,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        azure_ad_token_provider=token_provider,
    )

    translation_chain = translation_prompt | chat_client

    return translation_chain.invoke({"input": text}).content


def main() -> None:
    """Main function."""
    chatbot = ChatBot()
    sessions = chatbot.sessions
    start_session_response = chatbot.generate_session_id_wrapper(sessions)

    while True:
        query = input("\nYou: ")
        if query.lower() in ["exit", "quit", "bye"]:
            print("Exiting...")  # noqa: T201
            break

        query_input = QueryInput(text=query, session_id=str(uuid.uuid4()))

        query_response = chatbot.ask_chatbot_wrapper(query_input)
        logger.debug("Output: %s", query_response["output"])
        translated_text = german2english(query_response["output"])
        logger.debug("Translated output: %s", translated_text)

    check_status_response = chatbot.get_status_wrapper()
    logger.debug("Status: %s", check_status_response.chatbot_status)
    logger.debug("Message: %s", check_status_response.message)

    my_feedback = Feedback(
        rating=5,
        comments="Great chatbot!",
        session_id=start_session_response.session_id,
    )

    feedback_response = my_feedback.send_feedback_wrapper()
    logger.debug("Feedback response: %s", feedback_response.message)
    logger.debug("Session ID: %s", feedback_response.session_id)


if __name__ == "__main__":
    main()
