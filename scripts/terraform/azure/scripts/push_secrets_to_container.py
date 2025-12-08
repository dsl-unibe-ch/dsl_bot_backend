"""Update .env.{ENV} file with values from Terraform outputs."""

import argparse
import logging
from pathlib import Path

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Push Secrets to Container")
logger.setLevel(logging.DEBUG)
logger.propagate = False
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(handler)

VARIABLES_TO_ANONYMIZE = ["LANGSMITH_API_KEY"]


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Update .env.{ENV} file with values from Terraform outputs"
    )
    parser.add_argument(
        "-f",
        "--file",
        required=True,
        help="file name (e.g., .env.dev, global.output)",
    )
    parser.add_argument(
        "-b",
        "--backup_file",
        required=True,
        help="backup file name containing azure variables",
    )

    return parser.parse_args()


def read_env_file(env_file: str) -> dict:
    """Read the .env.{ENV} file."""
    env_vars = {}
    with Path(env_file).open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key in VARIABLES_TO_ANONYMIZE:
                value = "********"
            env_vars[key] = value
    return env_vars


def search_azure_variable(
    variable_name: str, file_path: str, backup_file_path: str
) -> str:
    """Read KEY=VALUE file if it exists; otherwise return empty dict."""
    env_variables_dict = read_env_file(file_path)
    if variable_name in env_variables_dict:
        return env_variables_dict.get(variable_name)
    env_variables_dict = read_env_file(backup_file_path)
    if variable_name in env_variables_dict:
        return env_variables_dict.get(variable_name)
    return "Value not found in the file or backup file"


def write_env_to_blob(
    connection_string: str, container_name: str, blob_name: str, env_vars: dict
) -> None:
    """Create container if needed and upload env vars as key=value lines."""
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)

    try:
        if not container_client.exists():
            container_client.create_container()
            logger.info("Created container: %s", container_name)
    except ResourceExistsError:
        logger.info("Container already exists: %s", container_name)
    filtered_items = [
        (k, v) for k, v in env_vars.items() if not k.startswith("segment_")
    ]
    payload = "\n".join(f"{k}={v}" for k, v in filtered_items) + "\n"

    blob_client = blob_service_client.get_blob_client(
        container=container_name, blob=blob_name
    )
    blob_client.upload_blob(payload, overwrite=True)
    logger.info("Uploaded secrets blob: %s/%s", container_name, blob_name)


def main() -> None:
    """Read .env.{ENV} and push its variables to Azure Blob container."""
    args = parse_args()
    file = f"{args.file}"
    backup_file_path = f"{args.backup_file}"
    if not Path(file).exists():
        msg = f"File not found: {file}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    env_vars = read_env_file(file)

    connection_string = search_azure_variable(
        variable_name="AZURE_STORAGE_ACCOUNT_PRIMARY_CONNECTION_STRING",
        file_path=file,
        backup_file_path=backup_file_path,
    )
    container_name = search_azure_variable(
        variable_name="AZURE_CONTAINER_STORAGE_SECRETS_NAME",
        file_path=file,
        backup_file_path=backup_file_path,
    )

    if not connection_string or connection_string.startswith("Value not found"):
        msg = "AZURE_STORAGE_ACCOUNT_PRIMARY_CONNECTION_STRING is missing in env file"
        logger.error(msg)
        raise ValueError(msg)

    if not container_name or container_name.startswith("Value not found"):
        msg = "AZURE_CONTAINER_STORAGE_SECRETS_NAME is missing in env file"
        logger.error(msg)
        raise ValueError(msg)
    env_vars["AZURE_STORAGE_ACCOUNT_PRIMARY_CONNECTION_STRING"] = connection_string
    blob_file_name = Path(file).name

    write_env_to_blob(connection_string, container_name, blob_file_name, env_vars)


if __name__ == "__main__":
    main()
