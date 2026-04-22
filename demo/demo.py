"""Demo script of kioskbot."""

from argparse import ArgumentParser

from app.agent.chatbot_rag import ChatBot, sessions
from app.agent.feedback import Feedback
from app.agent.query import QueryInput
from app.config import settings
from app.logging_config import close_kafka
from app.logging_config import kioskbot_logger as logger
from scripts.assessment_data.generate_assessment_dataset import german2english


def main() -> None:
    """Main function."""
    arg_parser = ArgumentParser(description="Run the kioskbot demo.")
    arg_parser.add_argument(
        "--customer_name",
        type=str,
        required=False,
        default=settings.DEFAULT_CUSTOMER,
        help="Optional customer name. Defaults to DEFAULT_CUSTOMER.",
    )
    arg_parser.add_argument(
        "--enable_agentic_search",
        type=bool,
        required=False,
        default=False,
        help="Enable agentic search. Defaults to False.",
    )
    args = arg_parser.parse_args()
    if not args.customer_name:
        args.customer_name = settings.DEFAULT_CUSTOMER
    chatbot = ChatBot(customer_name=args.customer_name)
    start_session_response = chatbot.initialize_agent_wrapper(sessions)

    while True:
        query = input("\nYou: ")
        if query.lower() in ["exit", "quit", "bye"]:
            print("Exiting...")  # noqa: T201
            break

        query_input = QueryInput(
            text=query, session_id=start_session_response.session_id
        )

        query_response = chatbot.invoke_agent_wrapper(query_input)
        print(f"Output: {query_response['output']}")  # noqa: T201
        translated_text = german2english(query_response["output"])
        print(f"Translated output: {translated_text}")  # noqa: T201

    my_feedback = Feedback(
        rating=5,
        comments="Great chatbot!",
        session_id=start_session_response.session_id,
    )

    feedback_response = my_feedback.send_feedback_wrapper(chatbot.interaction_count)
    logger.debug("Feedback response: %s", feedback_response.message)
    logger.debug("Session ID: %s", feedback_response.session_id)

    close_kafka()  # closing kafka gracefully


if __name__ == "__main__":
    main()
