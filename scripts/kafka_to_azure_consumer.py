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
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            group_id="azure-blob-storage-writer",
            value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        )

        # Wait for partition assignment before processing messages. There's
        # a race where messages produced very early can be skipped if the
        # consumer hasn't finished joining the group and received its
        # assignment yet. Polling until assignment ensures we start from the
        # configured offset policy (earliest/latest) relative to the time of
        # assignment.
        logger.info(
            "Waiting for partition assignment for consumer group: %s",
            consumer.config.get("group_id"),
        )

        while not consumer.assignment():  # poll until the consumer has an assignment
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
