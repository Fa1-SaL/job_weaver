"""
Mercor client configuration.
"""

CONFIG = {
    "clientId": "mercor",
    "displayName": "Mercor",
    "defaultCommitment": "10-40 hrs/week",
    "supportEmail": "support@mercor.com",
    "description": (
        "Mercor partners with leading AI labs and enterprises to train frontier AI models, "
        "offering competitive pay, collaboration with top researchers, and the opportunity "
        "to shape next generation AI systems using deep domain expertise."
    ),
    "applicationProcess": [
        "Upload resume",
        "Interview",
        "Submit form",
    ],
    # Subject line suffix used in generate_subject()
    "subjectSuffix": "Mercor x AI Labs",
    # Output format: "html" | "plain"
    "outputFormat": "html",
}
