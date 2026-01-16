"""Load test for Kioskbot API using Locust."""

import logging

from locust import HttpUser, between, task

# Use simple logging for load tests (avoid Kafka dependency)
logger = logging.getLogger("LoadTest")
logger.setLevel(logging.DEBUG)

SUCCESS_STATUS_CODES = [200]


class KioskbotUser(HttpUser):
    """The KioskbotUser class simulates a user interacting with the Kioskbot API.

    It defines tasks for starting a session, asking the chatbot questions, and sending feedback.
    """  # noqa: E501

    wait_time = between(
        1, 3
    )  # random wait time between tasks (invoke_agent and send_feedback)

    def on_start(self: "KioskbotUser") -> None:
        """This method is called when a simulated user starts.

        It initializes a new chatbot session by calling the root endpoint.
        """
        response = self.client.get("/initialize-agent")
        if response.status_code in SUCCESS_STATUS_CODES:
            self.session_id = response.json().get("session_id")
            logger.debug("[on_start] Got session_id: %s", self.session_id)
        else:
            logger.debug(
                "[on_start] Failed to get session_id, status: %s, body: %s",
                response.status_code,
                response.text,
            )
            self.session_id = None

    @task(3)
    def rag_agent(self: "KioskbotUser") -> None:
        """This task simulates asking the chatbot a question.

        It will be chosen three times as often as send_feedback.
        """
        if not self.session_id:  # if no session_id is available, skip this task
            logger.debug("[rag_agent] No session_id, skipping task.")
            return
        payload = {
            "session_id": self.session_id,
            "text": "What is the email address of the QSE Department?",
        }
        response = self.client.post("/invoke-agent", json=payload)
        if response.status_code in SUCCESS_STATUS_CODES:
            logger.debug("[rag_agent] status: %s", response.status_code)
        else:
            logger.debug(
                "[rag_agent] status: %s, body: %s",
                response.status_code,
                response.text,
            )

    @task(1)
    def send_feedback(self: "KioskbotUser") -> None:
        """This task simulates sending feedback for a chatbot session.

        It will be chosen one time for every three times invoke_agent is chosen.
        """
        if not self.session_id:  # If no session_id is available, skip this task
            logger.debug("[send_feedback] No session_id, skipping task.")
            return
        payload = {
            "session_id": self.session_id,
            "rating": 5,
            "comments": "Works well",
        }
        response = self.client.post("/send-feedback", json=payload)
        if response.status_code in SUCCESS_STATUS_CODES:
            logger.debug("[send_feedback] status: %s", response.status_code)
        else:
            logger.debug(
                "[send_feedback] status: %s, body: %s",
                response.status_code,
                response.text,
            )
