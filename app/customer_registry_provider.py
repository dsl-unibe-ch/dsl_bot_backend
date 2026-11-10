# Copyright (c) 2026, University of Bern, Data Science Lab
"""Storage providers for the customer registry."""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from typing import TYPE_CHECKING, Protocol

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field

from app.customer_registry import (
    CustomerRegistryEntry,
    load_customer_registry,
    validate_customer_registry,
)

if TYPE_CHECKING:
    from pathlib import Path

    from azure.storage.blob import BlobServiceClient


class CustomerRegistryManifest(BaseModel):
    """Customer IDs available in the Azure registry."""

    customer_ids: list[str] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class CustomerRegistryProvider(Protocol):
    """Storage-independent customer registry provider."""

    def load(self, *, fallback_customer_id: str) -> dict[str, CustomerRegistryEntry]:
        """Load and validate the complete registry."""


@dataclass(frozen=True)
class LocalCustomerRegistryProvider:
    """Load the registry from local dotenv files."""

    config_dir: Path

    def load(self, *, fallback_customer_id: str) -> dict[str, CustomerRegistryEntry]:
        """Load and validate local customer files."""
        return load_customer_registry(
            self.config_dir,
            fallback_customer_id=fallback_customer_id,
        )


@dataclass(frozen=True)
class AzureBlobCustomerRegistryProvider:
    """Load the registry from a manifest and per-customer Blob containers."""

    service_client: BlobServiceClient
    manifest_container: str
    customer_container_prefix: str
    manifest_blob_name: str = "customers.json"
    config_blob_name: str = "config.env"

    def load(self, *, fallback_customer_id: str) -> dict[str, CustomerRegistryEntry]:
        """Download and validate every customer listed in the manifest."""
        manifest_payload = (
            self.service_client.get_blob_client(
                container=self.manifest_container,
                blob=self.manifest_blob_name,
            )
            .download_blob()
            .readall()
        )
        manifest = CustomerRegistryManifest.model_validate_json(manifest_payload)

        entries = []
        for customer_id in manifest.customer_ids:
            container = f"{self.customer_container_prefix}{customer_id}"
            source = f"{container}/{self.config_blob_name}"
            payload = (
                self.service_client.get_blob_client(
                    container=container,
                    blob=self.config_blob_name,
                )
                .download_blob()
                .readall()
            )
            values = dict(
                dotenv_values(
                    stream=StringIO(payload.decode("utf-8")),
                    interpolate=False,
                )
            )
            entries.append((customer_id, source, values))

        return validate_customer_registry(
            entries,
            fallback_customer_id=fallback_customer_id,
        )
