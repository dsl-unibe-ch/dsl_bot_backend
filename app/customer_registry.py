# Copyright (c) 2026, University of Bern, Data Science Lab
"""Customer registry contract and cross-file validation."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, Json

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
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
    """Load every local registry file and enforce all cross-customer rules."""
    if not config_dir.is_dir():
        message = f"Customer config directory not found: {config_dir}"
        raise FileNotFoundError(message)

    env_files = sorted(config_dir.glob("*.env"))
    if not env_files:
        message = f"No customer config files found in {config_dir}"
        raise FileNotFoundError(message)
    entries = (
        (env_file.stem, env_file.name, dict(dotenv_values(env_file, interpolate=False)))
        for env_file in env_files
    )
    return validate_customer_registry(
        entries,
        fallback_customer_id=fallback_customer_id,
    )


def validate_customer_registry(
    entries: Iterable[tuple[str, str, Mapping[str, str | None]]],
    *,
    fallback_customer_id: str,
) -> dict[str, CustomerRegistryEntry]:
    """Validate parsed entries and all cross-customer registry rules."""
    configs: dict[str, CustomerRegistryEntry] = {}
    frontend_origins: dict[str, str] = {}
    index_names: dict[str, str] = {}
    for expected_customer_id, source, values in entries:
        config = load_customer_registry_values(source, values)
        customer_id = config.CUSTOMER_ID
        if customer_id in configs:
            message = f"Duplicate CUSTOMER_ID '{customer_id}'"
            raise ValueError(message)
        if expected_customer_id != customer_id:
            message = (
                f"Invalid customer registry entry '{customer_id}' in {source}: "
                f"expected CUSTOMER_ID '{expected_customer_id}'"
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

    if fallback_customer_id not in configs:
        message = (
            f"FALLBACK_CUSTOMER_ID '{fallback_customer_id}' does not exist in "
            "the customer registry"
        )
        raise ValueError(message)
    return configs


def load_customer_registry_file(path: Path) -> CustomerRegistryEntry:
    """Load one dotenv file and add customer/file context to schema errors."""
    raw_config = dict(dotenv_values(path, interpolate=False))
    return load_customer_registry_values(path.name, raw_config)


def load_customer_registry_values(
    source: str, values: Mapping[str, str | None]
) -> CustomerRegistryEntry:
    """Validate one parsed registry entry and include its source in errors."""
    try:
        return CustomerRegistryEntry.model_validate(values)
    except ValueError as exc:
        customer = values.get("CUSTOMER_ID", "unknown")
        message = f"Invalid customer registry entry '{customer}' in {source}: {exc}"
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
