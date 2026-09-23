# Copyright (c) 2026, University of Bern, Data Science Lab
"""Per-customer configuration loaded from customer_config/<customer_id>.env files."""

from __future__ import annotations

import functools
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config import settings

# app/customer_config.py -> app/ -> repo (or container) root
CUSTOMER_CONFIG_DIR = Path(__file__).resolve().parents[1] / "customer_config"


class CustomerConfig(BaseSettings):
    """Resolved, customer-scoped configuration (as opposed to app-wide config)."""

    customer_id: str = Field(validation_alias="CUSTOMER_ID")
    index_name: str = Field(validation_alias="AZURE_DEFAULT_AI_SEARCH_INDEX_NAME")
    frontend_url: str = Field(validation_alias="FRONTEND_URL")
    full_name: str = Field(validation_alias="CUSTOMER_FULL_NAME")
    contact_email: str = Field(validation_alias="CUSTOMER_CONTACT_EMAIL")
    prompt: str = Field(validation_alias="CUSTOMER_PROMPT")
    root_urls: list[str] = Field(validation_alias="CUSTOMER_ROOT_URLS")
    login_required: bool = Field(validation_alias="LOGIN_REQUIRED")
    agentic_max_num_retrievals: int = Field(
        validation_alias="AGENTIC_MAX_NUM_RETRIEVALS"
    )
    agentic_max_num_actions: int = Field(validation_alias="AGENTIC_MAX_NUM_ACTIONS")
    agentic_max_latency: int = Field(validation_alias="AGENTIC_MAX_LATENCY")
    agentic_max_token_budget: int = Field(validation_alias="AGENTIC_MAX_TOKEN_BUDGET")
    agentic_recursion_limit: int = Field(validation_alias="AGENTIC_RECURSION_LIMIT")
    enable_agentic_search: bool = Field(validation_alias="ENABLE_AGENTIC_SEARCH")

    model_config = SettingsConfigDict(extra="forbid")


def _load_customer_config_file(path: Path) -> CustomerConfig:
    return CustomerConfig(_env_file=path)


@functools.lru_cache(maxsize=1)
def _load_all_customer_configs() -> dict[str, CustomerConfig]:
    """Load and cache every customer_config/*.env file, keyed by customer_id."""
    if not CUSTOMER_CONFIG_DIR.is_dir():
        message = f"Customer config directory not found: {CUSTOMER_CONFIG_DIR}"
        raise FileNotFoundError(message)
    configs = {
        config.customer_id: config
        for env_file in sorted(CUSTOMER_CONFIG_DIR.glob("*.env"))
        for config in [_load_customer_config_file(env_file)]
    }
    if not configs:
        message = f"No customer config files found in {CUSTOMER_CONFIG_DIR}"
        raise FileNotFoundError(message)
    return configs


def get_customer_config(customer_id: str) -> CustomerConfig:
    """Return the resolved config for a customer_id, raising if unknown."""
    normalized = customer_id.strip().strip("'\"").strip()
    try:
        return _load_all_customer_configs()[normalized]
    except KeyError as exc:
        message = f"Unsupported customer_id '{normalized}'."
        raise ValueError(message) from exc


def get_customer_id_from_url(url: str) -> str | None:
    """Resolve a customer_id whose registered root URL is a substring of `url`."""
    for config in _load_all_customer_configs().values():
        for root_url in config.root_urls:
            if root_url in url:
                return config.customer_id
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
    """Return the deduplicated frontend URLs of every known customer (for CORS)."""
    seen = dict.fromkeys(
        config.frontend_url for config in _load_all_customer_configs().values()
    )
    return list(seen)
