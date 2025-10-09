"""Demo script of kioskbot."""

from app.agent.chatbot_azure import ChatBot, sessions
from app.agent.feedback import Feedback
from app.agent.query import QueryInput
from app.logging_config import kioskbot_logger as logger
from scripts.assessment_data.generate_assessment_dataset import german2english


def main() -> None:
    """Main function."""
    chatbot = ChatBot()
    start_session_response = chatbot.generate_session_id_wrapper(sessions)

    while True:
        query = input("\nYou: ")
        if query.lower() in ["exit", "quit", "bye"]:
            print("Exiting...")  # noqa: T201
            break

        query_input = QueryInput(
            text=query, session_id=start_session_response.session_id
        )

        query_response = chatbot.ask_chatbot_wrapper(query_input)
        print(f"Output: {query_response['output']}")  # noqa: T201
        translated_text = german2english(query_response["output"])
        print(f"Translated output: {translated_text}")  # noqa: T201

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
