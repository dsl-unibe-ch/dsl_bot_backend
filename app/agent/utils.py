"""Utility functions for the integration app."""

customer_name_root_url_mapping = {
    "quality": ["https://www.unibe.ch/universitaet/portraet/selbstverstaendnis/qualitaet/",
            "https://www.unibe.ch/university/portrait/self_image/quality/",
            "https://www.unibe.ch/universitaet/organisation/rechtliches/rechtssammlung/qualitaet/",
            "https://www.unibe.ch/university/organization/legal_matters/legal_collection/quality/",
            "https://www.unibe.ch/universitaet/organisation/leitung_und_zentralbereich/vizerektorat_qualitaet_und_nachhaltige_entwicklung/",
            "https://www.unibe.ch/university/organization/executive_board_and_central_administration/vice_rectorate_quality_and_sustainable_development/"
            "https://www.unibe.ch/studium/werkzeuge_und_arbeitshilfen/fuer_lehrende/lehrveranstaltungsevaluation/",
            "https://www.unibe.ch/studies/tools_and_work_aids/for_lecturers/lehrveranstaltungsevaluation/",
            "https://lead.unibe.ch/dienstleistungen/zwischenfeedback/"],
    "innovation": ["https://www.unibe.ch/universitaet/organisation/leitung_und_zentralbereich/vizerektorat_forschung_und_innovation/innovation_office/",
            "https://www.unibe.ch/university/organization/executive_board_and_central_administration/vice_rectorate_research_and_innovation/innovation_office/"
            "https://www.unibe.ch/innovation/"
            ]
    }

def get_customer_name_from_url(url: str) -> str | None:
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
