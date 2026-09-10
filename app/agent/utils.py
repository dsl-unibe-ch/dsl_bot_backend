# Copyright (c) 2026, University of Bern, Data Science Lab
"""Utility functions for the integration app."""

# This is URL and customer name mapping, used as the postfix in the search index name

customer_name_root_url_mapping = {
    "bnf": ["https://www.bnf.unibe.ch/"],
}

customer_name_contact_dict = {
    "bnf": "info.bnf@unibe.ch",
}

customer_full_name_dict = {
    "bnf": "BNF - Nationales Qualifizierungsprogramm",
}

customer_prompt_mapping = {
    "bnf": (
        "If the query is specifically related to Zentrale Administration"
        "use info.bnf@unibe.ch"
        "if related to BNF­-Geschäftsleitung use fritz.moser@unibe.ch"
        "barbara.huse@unibe.ch"
        "Wherever suitable if the user is from Basel, Bern, Lausanne or Zurich,"
        "Redirect to respective regional contacts, use basel.bnf@unibe.ch"
        "for Basel, bern.bnf@unibe.ch for Bern, lausanne.bnf@unibe.ch for"
        "Lausanne, and zuerich.bnf@unibe.ch for Zurich."
    ),
}


def get_customer_name_from_url(url: str) -> str | None:
    """Get the customer name from the URL."""
    for customer_name, url_list in customer_name_root_url_mapping.items():
        for url_root in url_list:
            if url_root in url:
                return customer_name
    return None


def truncate_for_table_storage(value: str, max_property_length: int = 32000) -> str:
    """Truncate a string value to fit within Azure Table Storage limits."""
    if isinstance(value, str) and len(value) > max_property_length:
        return value[:max_property_length] + "... [truncated]"
    return value
