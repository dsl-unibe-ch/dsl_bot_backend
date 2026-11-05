# Copyright (c) 2026, University of Bern, Data Science Lab
"""Versioned customer registry contract and cross-file validation."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, Json

if TYPE_CHECKING:
    from pathlib import Path


class LifecycleStatus(StrEnum):
    """Supported customer lifecycle states."""

    DRAFT = "draft"
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    DEPROVISIONING = "deprovisioning"
    ARCHIVED = "archived"


class CustomerRegistryEntry(BaseModel):
    """Canonical schema for one customer registry file."""

    CUSTOMER_ID: str = Field(
        min_length=2,
        max_length=63,
        pattern=r"^[a-z][a-z0-9-]+$",
    )
    CUSTOMER_FULL_NAME: str = Field(min_length=1)
    CUSTOMER_CONTACT_EMAIL: str = Field(min_length=1)
    CUSTOMER_ROOT_URLS: Json[list[HttpUrl]] = Field(min_length=1)
    BACKEND_PROMPT: str = Field(min_length=1)
    BACKEND_AGENTIC_MAX_NUM_RETRIEVALS: int
    BACKEND_AGENTIC_MAX_NUM_ACTIONS: int
    BACKEND_AGENTIC_MAX_LATENCY: int
    BACKEND_AGENTIC_MAX_TOKEN_BUDGET: int
    BACKEND_AGENTIC_RECURSION_LIMIT: int
    BACKEND_ENABLE_AGENTIC_SEARCH: bool
    ETL_ENABLED: bool
    FRONTEND_ORIGIN: HttpUrl
    FRONTEND_LOGIN_REQUIRED: bool
    SEARCH_INDEX_NAME: str = Field(min_length=1)
    LIFECYCLE_STATUS: LifecycleStatus

    model_config = ConfigDict(extra="forbid")


def load_customer_registry(
    config_dir: Path,
    *,
    fallback_customer_id: str,
) -> dict[str, CustomerRegistryEntry]:
    """Load every registry file and enforce all cross-customer rules."""
    if not config_dir.is_dir():
        message = f"Customer config directory not found: {config_dir}"
        raise FileNotFoundError(message)

    configs: dict[str, CustomerRegistryEntry] = {}
    frontend_origins: dict[str, str] = {}
    index_names: dict[str, str] = {}
    for env_file in sorted(config_dir.glob("*.env")):
        config = load_customer_registry_file(env_file)
        customer_id = config.CUSTOMER_ID
        if customer_id in configs:
            message = f"Duplicate CUSTOMER_ID '{customer_id}'"
            raise ValueError(message)
        if env_file.stem != customer_id:
            message = (
                f"Invalid customer registry entry '{customer_id}': filename "
                f"'{env_file.name}' must be '{customer_id}.env'"
            )
            raise ValueError(message)
        configs[customer_id] = config

        if config.FRONTEND_ORIGIN is not None:
            record_unique(
                frontend_origins,
                origin_key(str(config.FRONTEND_ORIGIN)),
                customer_id,
                "FRONTEND_ORIGIN",
            )
        if config.SEARCH_INDEX_NAME is not None:
            record_unique(
                index_names,
                config.SEARCH_INDEX_NAME,
                customer_id,
                "SEARCH_INDEX_NAME",
            )

    if not configs:
        message = f"No customer config files found in {config_dir}"
        raise FileNotFoundError(message)
    if fallback_customer_id not in configs:
        message = (
            f"FALLBACK_CUSTOMER_ID '{fallback_customer_id}' does not exist in "
            f"{config_dir}"
        )
        raise ValueError(message)
    return configs


def load_customer_registry_file(path: Path) -> CustomerRegistryEntry:
    """Load one dotenv file and add customer/file context to schema errors."""
    raw_config = dict(dotenv_values(path, interpolate=False))
    try:
        return CustomerRegistryEntry.model_validate(raw_config)
    except ValueError as exc:
        customer = raw_config.get("CUSTOMER_ID", path.stem)
        message = f"Invalid customer registry entry '{customer}' in {path.name}: {exc}"
        raise ValueError(message) from exc


def origin_key(origin: str) -> str:
    """Return a comparison key without changing the configured origin."""
    parts = urlsplit(origin)
    host = parts.hostname
    if host is None:
        message = f"Invalid FRONTEND_ORIGIN '{origin}'"
        raise ValueError(message)
    default_port = 80 if parts.scheme == "http" else 443
    port = parts.port or default_port
    return f"{parts.scheme.lower()}://{host.lower()}:{port}"


def record_unique(
    seen: dict[str, str], value: str, customer_id: str, field: str
) -> None:
    """Record a globally unique value or identify both conflicting customers."""
    if previous_customer := seen.get(value):
        message = (
            f"Duplicate {field} '{value}' for customers "
            f"'{previous_customer}' and '{customer_id}'"
        )
        raise ValueError(message)
    seen[value] = customer_id
