# Copyright (c) 2026, University of Bern, Data Science Lab
"""Per-customer configuration loaded from customer_config/<customer_id>.env files."""

from __future__ import annotations

import functools
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from app.config import settings
from app.customer_registry import CustomerRegistryEntry
from app.customer_registry_provider import (
    AzureBlobCustomerRegistryProvider,
    CustomerRegistryProvider,
    LocalCustomerRegistryProvider,
)

# app/customer_config.py -> app/ -> repo (or container) root
CUSTOMER_CONFIG_DIR = Path(__file__).resolve().parents[1] / "customer_config"


CustomerConfig = CustomerRegistryEntry


def _create_registry_provider() -> CustomerRegistryProvider:
    """Create the explicitly configured customer registry provider."""
    if settings.CUSTOMER_REGISTRY_PROVIDER == "local":
        return LocalCustomerRegistryProvider(CUSTOMER_CONFIG_DIR)
    if settings.AZURE_CUSTOMER_REGISTRY_ACCOUNT_URL is None:
        message = (
            "AZURE_CUSTOMER_REGISTRY_ACCOUNT_URL is required when "
            "CUSTOMER_REGISTRY_PROVIDER=azure"
        )
        raise ValueError(message)
    service_client = BlobServiceClient(
        account_url=settings.AZURE_CUSTOMER_REGISTRY_ACCOUNT_URL,
        credential=DefaultAzureCredential(),
    )
    return AzureBlobCustomerRegistryProvider(
        service_client=service_client,
        manifest_container=settings.AZURE_CUSTOMER_REGISTRY_MANIFEST_CONTAINER,
        customer_container_prefix=settings.AZURE_CUSTOMER_REGISTRY_CONTAINER_PREFIX,
    )


@functools.lru_cache(maxsize=1)
def _load_all_customer_configs() -> dict[str, CustomerConfig]:
    """Load and cache every validated registry entry, keyed by customer ID."""
    return _create_registry_provider().load(
        fallback_customer_id=settings.FALLBACK_CUSTOMER_ID,
    )


def get_customer_config(customer_id: str) -> CustomerConfig:
    """Return the resolved config for an exact customer ID, raising if unknown."""
    try:
        return _load_all_customer_configs()[customer_id]
    except KeyError as exc:
        message = f"Unsupported customer_id '{customer_id}'."
        raise ValueError(message) from exc


def get_customer_id_from_index_name(index_name: str) -> str | None:
    """Resolve a customer ID from its exact registered search index name."""
    for config in _load_all_customer_configs().values():
        if index_name == config.SEARCH_INDEX_NAME:
            return config.CUSTOMER_ID
    return None


def get_customer_id_from_url(url: str) -> str | None:
    """Resolve a customer ID whose registered URL is a substring of ``url``."""
    for config in _load_all_customer_configs().values():
        if config.FRONTEND_ORIGIN and str(config.FRONTEND_ORIGIN) in url:
            return config.CUSTOMER_ID
        for root_url in config.CUSTOMER_ROOT_URLS:
            if str(root_url) in url:
                return config.CUSTOMER_ID
    return None


def resolve_customer_id(url: str | None) -> str:
    """Resolve a customer_id from an origin URL, falling back to FALLBACK_CUSTOMER_ID.

    Callers should use this instead of repeating an
    "get_customer_id_from_url(...) or <default>" check themselves.
    """
    if url:
        customer_id = get_customer_id_from_url(url)
        if customer_id:
            return customer_id
    return settings.FALLBACK_CUSTOMER_ID


def all_frontend_urls() -> list[str]:
    """Return the validated, globally unique frontend origins used for CORS."""
    return [
        str(config.FRONTEND_ORIGIN)
        for config in _load_all_customer_configs().values()
        if config.FRONTEND_ORIGIN is not None
    ]
