"""Kafka consumer to write chatbot logs from Kafka to Azure Blob."""

import datetime
import json
import logging
import uuid
from zoneinfo import ZoneInfo

from azure.storage.blob import BlobServiceClient
from kafka import KafkaConsumer

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the Kafka consumer to process messages and upsert to Azure Blob Storage."""
    try:
        # Make sure the consumer doesn't miss messages produced around startup.
        # If there is no committed offset for the consumer group, 'earliest'
        # will start from the beginning of the partition (safe for local/demo runs).
        consumer = KafkaConsumer(
            settings.KAFKA_TOPIC,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            auto_offset_reset="latest",  # in case the consumer group has no committed offsets, start from the latest messages. Note that in case the group has a commited offset, this parameter is ignored # noqa: E501
            enable_auto_commit=False,  # with `enable_auto_commit=True`, Kafka automatically commits the offset at regular intervals (e.g., every 5 seconds). However, since I want to commit offsets only after the messages are actually written to the Blob, I disable auto commit (see `consumer.commit()` below) # noqa: E501
            group_id="azure-blob-storage-writer",  # name of the consumer group that is reading from a specific Kafka topic. Note that for a given topic, different consumers can use different group IDs. Each group ID will have its own set of committed offsets, so each consumer group tracks its own progress independently. # noqa: E501
            value_deserializer=lambda x: json.loads(
                x.decode("utf-8")
            ),  # tells the KafkaConsumer how to decode the message value from Kafka.
        )

        logger.info(
            "Waiting for partition assignment for consumer group: %s",
            consumer.config.get("group_id"),
        )
        while not consumer.assignment():  # ensuring that the Kafka consumer is assigned to topic partitions before it starts processing messages to avoid missing messages that could be produced before the consumer is ready to read. This is required only once at startup, since Kafka needs time to coordinate and assign partitions to consumers in a group. # noqa: E501
            consumer.poll(timeout_ms=100)
        logger.info("Assigned partitions: %s", consumer.assignment())

        container_name = settings.AZURE_CONTAINER_STORAGE_NAME
        connection_string = settings.AZURE_STORAGE_CONNECTION_STRING

        logger.info("Starting Kafka consumer for topic: %s", settings.KAFKA_TOPIC)

        for message in consumer:
            try:
                log_entry = message.value
                log_content = json.loads(log_entry["message"])

                session_id = log_content["session_id"]
                unique_id = str(uuid.uuid4())
                blob_service_client = BlobServiceClient.from_connection_string(
                    connection_string
                )
                now = datetime.datetime.now(ZoneInfo("Europe/Berlin"))
                year = now.strftime("%Y")
                month = now.strftime("%m")
                day = now.strftime("%d")
                turn_number = log_content["interaction_count"]
                turn_number = str(turn_number).zfill(3)
                blob_name = f"rag_logs/{year}/{month}/{day}/{session_id}/{turn_number}_{unique_id}.log"  # noqa: E501
                blob_client = blob_service_client.get_blob_client(
                    container=container_name, blob=blob_name
                )
                blob_client.upload_blob(json.dumps(log_content))
                consumer.commit()  # adavance the offset only after successful processing. This is important to avoid data loss when the consumer restarts or Azure Blob is not available. # noqa: E501
                logger.info(
                    "Upserted to Azure Blob Storage: %s", log_content.get("session_id")
                )
            except Exception:
                logger.exception("Error processing message:")

    except Exception:
        logger.exception("Error in consumer:")
        raise


if __name__ == "__main__":
    main()
