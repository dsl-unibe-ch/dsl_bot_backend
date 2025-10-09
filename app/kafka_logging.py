"""Custom logging utilities for the Kioskbot backend."""

import json
import logging

from kafka import KafkaProducer


class KafkaLoggingHandler(logging.Handler):
    """Custom logging handler that sends log records to a Kafka topic."""

    def __init__(
        self: "KafkaLoggingHandler", producer: KafkaProducer, topic: str
    ) -> None:
        """Initialize the KafkaLoggingHandler with a Kafka producer and topic."""
        super().__init__()
        self.producer = producer
        self.topic = topic

    def emit(self: "KafkaLoggingHandler", record: logging.LogRecord) -> None:
        """Send the log record to the Kafka topic.

        This method defines exactly how to process and send each log record. It is a required method for any custom logging handler in Python's logging module. Specifically, it converts the log record to a dictionary, JSON-encodes it, and sends it to Kafka.

        The attributes of the record are defined in https://docs.python.org/3/library/logging.html#logrecord-attributes
        """  # noqa: E501
        log_entry = {
            "timestamp": record.created,  # time the log record was created
            "level": record.levelname,  # severity level of the log message (e.g., "INFO", "ERROR", "DEBUG") # noqa: E501
            "message": record.getMessage(),  # contains the log_content JSON from chatbot_azure.py # noqa: E501
            "logger": record.name,  # name of the logger that created the log record, e.g., "Kioskbot" # noqa: E501
            "module": record.module,  # name of the Python file where the log call was made, e.g., "chatbot_azure.py" # noqa: E501
            "funcName": record.funcName,  # the name of the function from which the log call originated, e.g., ask_chatbot_wrapper # noqa: E501
            "lineNo": record.lineno,  #  line number in the source code where the log call was made # noqa: E501
        }
        self.producer.send(self.topic, value=json.dumps(log_entry).encode("utf-8"))

    def close(self: "KafkaLoggingHandler") -> None:
        """Close the Kafka producer."""
        if hasattr(self, "producer") and self.producer is not None:
            self.producer.close()
        super().close()
