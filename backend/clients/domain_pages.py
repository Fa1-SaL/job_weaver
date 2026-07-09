"""
Domain Pages client configurations.
All 8 Domain Pages recruit for positions at Mercor.
"""

from clients.mercor import CONFIG as MERCOR_CONFIG

CROSSING_HURDLES_CONFIG = {
    "clientId": "crossing_hurdles",
    "displayName": "Crossing Hurdles",
    "defaultCommitment": "10-40 hrs/week",
    "supportEmail": "support@mercor.com",
    "description": MERCOR_CONFIG["description"],
    "applicationProcess": MERCOR_CONFIG["applicationProcess"],
    "subjectSuffix": "Mercor x AI Labs",
    "outputFormat": "html",
}

CODEGENIUSRECRUIT_CONFIG = {
    "clientId": "codegeniusrecruit",
    "displayName": "CodeGeniusRecruit",
    "defaultCommitment": "10-40 hrs/week",
    "supportEmail": "support@mercor.com",
    "description": MERCOR_CONFIG["description"],
    "applicationProcess": MERCOR_CONFIG["applicationProcess"],
    "subjectSuffix": "Mercor",
    "outputFormat": "html",
}

CURASENSEAI_CONFIG = {
    "clientId": "curasenseai",
    "displayName": "CuraSenseAI",
    "defaultCommitment": "10-40 hrs/week",
    "supportEmail": "support@mercor.com",
    "description": MERCOR_CONFIG["description"],
    "applicationProcess": MERCOR_CONFIG["applicationProcess"],
    "subjectSuffix": "Mercor",
    "outputFormat": "html",
}

LEGALTRUSTAI_CONFIG = {
    "clientId": "legaltrustai",
    "displayName": "LegalTrustAI",
    "defaultCommitment": "10-40 hrs/week",
    "supportEmail": "support@mercor.com",
    "description": MERCOR_CONFIG["description"],
    "applicationProcess": MERCOR_CONFIG["applicationProcess"],
    "subjectSuffix": "Mercor",
    "outputFormat": "html",
}

CAPITEXAI_CONFIG = {
    "clientId": "capitexai",
    "displayName": "CapitexAI",
    "defaultCommitment": "10-40 hrs/week",
    "supportEmail": "support@mercor.com",
    "description": MERCOR_CONFIG["description"],
    "applicationProcess": MERCOR_CONFIG["applicationProcess"],
    "subjectSuffix": "Mercor",
    "outputFormat": "html",
}

STEMSYNCAI_CONFIG = {
    "clientId": "stemsyncai",
    "displayName": "STEMSyncAI",
    "defaultCommitment": "10-40 hrs/week",
    "supportEmail": "support@mercor.com",
    "description": MERCOR_CONFIG["description"],
    "applicationProcess": MERCOR_CONFIG["applicationProcess"],
    "subjectSuffix": "Mercor",
    "outputFormat": "html",
}

LINGUASENSEAI_CONFIG = {
    "clientId": "linguasenseai",
    "displayName": "LinguaSenseAI",
    "defaultCommitment": "10-40 hrs/week",
    "supportEmail": "support@mercor.com",
    "description": MERCOR_CONFIG["description"],
    "applicationProcess": MERCOR_CONFIG["applicationProcess"],
    "subjectSuffix": "Mercor",
    "outputFormat": "html",
}

DESIGNMESHAI_CONFIG = {
    "clientId": "designmeshai",
    "displayName": "DesignMeshAI",
    "defaultCommitment": "10-40 hrs/week",
    "supportEmail": "support@mercor.com",
    "description": MERCOR_CONFIG["description"],
    "applicationProcess": MERCOR_CONFIG["applicationProcess"],
    "subjectSuffix": "Mercor",
    "outputFormat": "html",
}

DOMAIN_PAGES_REGISTRY = {
    "crossing_hurdles": CROSSING_HURDLES_CONFIG,
    "codegeniusrecruit": CODEGENIUSRECRUIT_CONFIG,
    "curasenseai": CURASENSEAI_CONFIG,
    "legaltrustai": LEGALTRUSTAI_CONFIG,
    "capitexai": CAPITEXAI_CONFIG,
    "stemsyncai": STEMSYNCAI_CONFIG,
    "linguasenseai": LINGUASENSEAI_CONFIG,
    "designmeshai": DESIGNMESHAI_CONFIG,
}

DOMAIN_PAGE_KEYS = set(DOMAIN_PAGES_REGISTRY.keys())
