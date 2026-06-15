"""Utility functions for the integration app."""

# This is the mapping between URL and customer name which is used as the postfix in the search index name

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
            "https://www.unibe.ch/university/organization/executive_board_and_central_administration/vice_rectorate_research_and_innovation/innovation_office/",
            "https://www.unibe.ch/universite/organisation/direction_de_luniversit_et_administration_centrale/vice_rectorat_de_la_recherche_et_de_linnovation/",
            "https://www.unibe.ch/innovation/",
            "https://lead.unibe.ch/forschung/lehre_im_ideenlabor/",
            "https://lead.unibe.ch/research/lehre_im_ideenlabor/",
            ]
    }

customer_name_contact_dict={
    "quality": "info.qualitaet@unibe.ch",
    "innovation": "innovationoffice@unibe.ch",
}

customer_full_name_dict={
    "quality": "Department of Quality Assurance and Development",
    "innovation": "Ideenlabor (Ideas Lab)",
}

customer_prompt_mapping={
    "quality": """If the query is specifically related to evaluation of teaching or courses, refer the user to lehrevaluation@unibe.ch. Also lehrevaluation@unibe.ch is the best contact for training.""",
    "innovation": """If the query is specifically related to the IdeenLabor, refer the user to ideenlabor@unibe.ch. If the question is about financing, pitching an idea or the innovation process, refer the user to innovationoffice@unibe.ch""",
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
