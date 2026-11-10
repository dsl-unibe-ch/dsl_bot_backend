"""Tests for customer registry storage providers."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from azure.storage.blob import BlobServiceClient

from app.customer_registry_provider import AzureBlobCustomerRegistryProvider


def _config(customer_id: str) -> bytes:
    values = {
        "CUSTOMER_ID": customer_id,
        "CUSTOMER_FULL_NAME": f"Customer {customer_id}",
        "CUSTOMER_CONTACT_EMAIL": f"{customer_id}@example.org",
        "CUSTOMER_ROOT_URLS": f'["https://{customer_id}.example.org/"]',
        "BACKEND_PROMPT": "Answer using customer content.",
        "BACKEND_AGENTIC_MAX_NUM_RETRIEVALS": "3",
        "BACKEND_AGENTIC_MAX_NUM_ACTIONS": "12",
        "BACKEND_AGENTIC_MAX_LATENCY": "8",
        "BACKEND_AGENTIC_MAX_TOKEN_BUDGET": "10000",
        "BACKEND_AGENTIC_RECURSION_LIMIT": "25",
        "BACKEND_ENABLE_AGENTIC_SEARCH": "true",
        "ETL_ENABLED": "false",
        "FRONTEND_ORIGIN": f"https://chat-{customer_id}.example.org",
        "FRONTEND_LOGIN_REQUIRED": "true",
        "SEARCH_INDEX_NAME": f"index-{customer_id}",
        "LIFECYCLE_STATUS": "active",
    }
    return "".join(f"{key}={value}\n" for key, value in values.items()).encode()


def _service_client(payloads: dict[tuple[str, str], bytes]) -> MagicMock:
    service_client = MagicMock(spec=BlobServiceClient)

    def get_blob_client(*, container: str, blob: str) -> MagicMock:
        blob_client = MagicMock()
        blob_client.download_blob.return_value.readall.return_value = payloads[
            (container, blob)
        ]
        return blob_client

    service_client.get_blob_client.side_effect = get_blob_client
    return service_client


def test_azure_provider_loads_manifest_and_customer_configs() -> None:
    payloads = {
        ("customer-registry", "customers.json"): json.dumps(
            {"customer_ids": ["alpha", "beta"]}
        ).encode(),
        ("customer-alpha", "config.env"): _config("alpha"),
        ("customer-beta", "config.env"): _config("beta"),
    }
    provider = AzureBlobCustomerRegistryProvider(
        service_client=_service_client(payloads),
        manifest_container="customer-registry",
        customer_container_prefix="customer-",
    )

    registry = provider.load(fallback_customer_id="alpha")

    assert sorted(registry) == ["alpha", "beta"]
    assert registry["beta"].SEARCH_INDEX_NAME == "index-beta"


def test_azure_provider_does_not_fall_back_when_download_fails() -> None:
    service_client = MagicMock(spec=BlobServiceClient)
    service_client.get_blob_client.side_effect = RuntimeError("Azure unavailable")
    provider = AzureBlobCustomerRegistryProvider(
        service_client=service_client,
        manifest_container="customer-registry",
        customer_container_prefix="customer-",
    )

    with pytest.raises(RuntimeError, match="Azure unavailable"):
        provider.load(fallback_customer_id="default")