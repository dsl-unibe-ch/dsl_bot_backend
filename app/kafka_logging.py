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
            "timestamp": record.created,
            "level": record.levelname,
            "message": record.getMessage(),  # contains the log_content JSON from chatbot_azure.py # noqa: E501
            "logger": record.name,
            "module": record.module,
            "funcName": record.funcName,
            "lineNo": record.lineno,
        }
        self.producer.send(self.topic, value=json.dumps(log_entry).encode("utf-8"))
