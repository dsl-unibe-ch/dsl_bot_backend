"""Validate and upload the local customer registry to Azure Blob Storage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from app.customer_registry import load_customer_registry


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account-url", required=True)
    parser.add_argument("--config-dir", type=Path, default=Path("customer_config"))
    parser.add_argument("--fallback-customer-id", default="default")
    parser.add_argument("--manifest-container", default="customer-registry")
    parser.add_argument("--customer-container-prefix", default="customer-registry-")
    return parser.parse_args()


def main() -> None:
    """Validate local entries, then upload configs followed by the manifest."""
    args = parse_args()
    registry = load_customer_registry(
        args.config_dir,
        fallback_customer_id=args.fallback_customer_id,
    )
    service_client = BlobServiceClient(
        account_url=args.account_url,
        credential=DefaultAzureCredential(),
    )

    for customer_id in sorted(registry):
        config_path = args.config_dir / f"{customer_id}.env"
        service_client.get_blob_client(
            container=f"{args.customer_container_prefix}{customer_id}",
            blob="config.env",
        ).upload_blob(config_path.read_bytes(), overwrite=True)

    manifest = json.dumps({"customer_ids": sorted(registry)}, indent=2).encode()
    service_client.get_blob_client(
        container=args.manifest_container,
        blob="customers.json",
    ).upload_blob(manifest, overwrite=True)
    print(f"Uploaded {len(registry)} customer registry entries.")  # noqa: T201


if __name__ == "__main__":
    main()