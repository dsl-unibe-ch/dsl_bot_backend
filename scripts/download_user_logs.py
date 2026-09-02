"""Download prod logs from Azure Blob Storage and split by customer."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

import pandas as pd
from azure.storage.blob import BlobServiceClient

# Default to prod env when run as a standalone utility.
os.environ.setdefault("ENV", "prod")

from app.config import settings


def _extract_json_payload(raw_text: str) -> dict | None:
    """Return a parsed JSON object from blob content, if present."""
    stripped = raw_text.strip()
    if not stripped:
        return None

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None

    if isinstance(payload, dict):
        return payload
    return None


def _safe_customer_name(name: str) -> str:
    """Create a filename-safe customer identifier."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") or "unknown_customer"


def download_and_split_logs(
    container_name: str,
    output_dir: Path,
    prefix: str = "rag_logs/",
    max_blobs: int | None = None,
) -> tuple[int, int]:
    """Fetch blob logs, filter prod payloads, and write them by customer as Excel."""
    blob_service_client = BlobServiceClient.from_connection_string(
        settings.AZURE_STORAGE_ACCOUNT_PRIMARY_CONNECTION_STRING
    )
    container_client = blob_service_client.get_container_client(container_name)

    output_dir.mkdir(parents=True, exist_ok=True)
    customer_rows: dict[str, list[dict]] = {}
    total_prod = 0

    blob_iter = container_client.list_blobs(name_starts_with=prefix)
    for index, blob in enumerate(blob_iter, start=1):
        if max_blobs is not None and index > max_blobs:
            break

        blob_client = container_client.get_blob_client(blob.name)
        blob_content = blob_client.download_blob().readall().decode("utf-8")
        payload = _extract_json_payload(blob_content)
        if payload is None:
            continue

        if str(payload.get("environment", "")).lower() != "prod":
            continue

        customer = _safe_customer_name(
            str(payload.get("customer_name", "unknown_customer"))
        )
        customer_rows.setdefault(customer, []).append(payload)
        total_prod += 1

    for customer, rows in customer_rows.items():
        field_names = sorted({key for row in rows for key in row.keys()})
        file_path = output_dir / f"{customer}.xlsx"
        normalized_rows: list[dict] = []
        for row in rows:
            normalized_row = {}
            for key in field_names:
                value = row.get(key, "")
                if isinstance(value, (dict, list)):
                    normalized_row[key] = json.dumps(value, ensure_ascii=True)
                else:
                    normalized_row[key] = value
            normalized_rows.append(normalized_row)

        df = pd.DataFrame(normalized_rows, columns=field_names)
        df.to_excel(file_path, index=False)

    return total_prod, len(customer_rows)


def parse_args() -> argparse.Namespace:
    """Parse CLI args."""
    parser = argparse.ArgumentParser(
        description="Download kiosk-bot prod logs from Azure Blob and split by customer."
    )
    parser.add_argument(
        "--container",
        default=settings.AZURE_CONTAINER_STORAGE_NAME or "kioskbot-logs",
        help="Azure Blob container name (default: AZURE_CONTAINER_STORAGE_NAME).",
    )
    parser.add_argument(
        "--output-dir",
        default="tests/data/downloaded_prod_logs",
        help="Directory where per-customer log files are written.",
    )
    parser.add_argument(
        "--prefix",
        default="rag_logs/",
        help="Blob name prefix to scan (default: rag_logs/).",
    )
    parser.add_argument(
        "--max-blobs",
        type=int,
        default=None,
        help="Optional limit for number of blobs to scan.",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entrypoint."""
    args = parse_args()
    total_prod, customer_count = download_and_split_logs(
        container_name=args.container,
        output_dir=Path(args.output_dir),
        prefix=args.prefix,
        max_blobs=args.max_blobs,
    )
    print(
        f"Wrote {total_prod} prod log entries into {customer_count} customer file(s) "
        f"under '{args.output_dir}'."
    )


if __name__ == "__main__":
    main()
