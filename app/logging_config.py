"""Centralized logging configuration for Kioskbot."""

import logging

from kafka import KafkaProducer

from app.config import settings
from app.kafka_logging import KafkaLoggingHandler

kioskbot_logger = logging.getLogger("Kioskbot")
producer = KafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
kafka_handler = KafkaLoggingHandler(producer, settings.KAFKA_TOPIC)
kioskbot_logger.addHandler(kafka_handler)
kioskbot_logger.setLevel(logging.INFO)
