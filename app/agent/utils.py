# Copyright (c) 2026, University of Bern, Data Science Lab
"""Utility functions for the integration app."""

from app.customer_config import get_customer_id_from_url


def get_customer_name_from_url(url: str) -> str | None:
    """Get the customer name from the URL, resolved via the customer_config registry."""
    return get_customer_id_from_url(url)


def truncate_for_table_storage(value: str, max_property_length: int = 32000) -> str:
    """Truncate a string value to fit within Azure Table Storage limits."""
    if isinstance(value, str) and len(value) > max_property_length:
        return value[:max_property_length] + "... [truncated]"
    return value
