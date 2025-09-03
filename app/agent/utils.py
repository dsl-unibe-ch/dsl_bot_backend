"""Utility functions for the integration app."""


def truncate_for_table_storage(value: str, max_property_length: int = 32000) -> str:
    """Truncate a string value to fit within Azure Table Storage limits."""
    if isinstance(value, str) and len(value) > max_property_length:
        return value[:max_property_length] + "... [truncated]"
    return value
