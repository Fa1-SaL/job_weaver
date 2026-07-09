"""
Formatter registry — maps client IDs to their formatter instances.

Usage:
    from formatters import get_formatter

    fmt = get_formatter("turing")
    jd_text = fmt.format_jd(data)
"""

from typing import Dict
from formatters.base import ClientFormatter
from formatters.mercorFormatter import MercorFormatter
from formatters.micro1Formatter import Micro1Formatter
from formatters.turingFormatter import TuringFormatter

from formatters.domainPagesFormatter import (
    CrossingHurdlesFormatter,
    CodeGeniusRecruitFormatter,
    CuraSenseAIFormatter,
    LegalTrustAIFormatter,
    CapitexAIFormatter,
    STEMSyncAIFormatter,
    LinguaSenseAIFormatter,
    DesignMeshAIFormatter,
)

# Singleton instances — formatters are stateless, so one instance per client is fine
_FORMATTER_REGISTRY: Dict[str, ClientFormatter] = {
    "mercor": MercorFormatter(),
    "micro1": Micro1Formatter(),
    "turing": TuringFormatter(),
    "crossing_hurdles": CrossingHurdlesFormatter(),
    "codegeniusrecruit": CodeGeniusRecruitFormatter(),
    "curasenseai": CuraSenseAIFormatter(),
    "legaltrustai": LegalTrustAIFormatter(),
    "capitexai": CapitexAIFormatter(),
    "stemsyncai": STEMSyncAIFormatter(),
    "linguasenseai": LinguaSenseAIFormatter(),
    "designmeshai": DesignMeshAIFormatter(),
}



def get_formatter(client_id: str) -> ClientFormatter:
    """
    Return the formatter for *client_id* (case-insensitive).

    Raises:
        ValueError: if no formatter is registered for the client.
    """
    key = client_id.strip().lower()
    if key not in _FORMATTER_REGISTRY:
        supported = list(_FORMATTER_REGISTRY.keys())
        raise ValueError(
            f"No formatter registered for client '{client_id}'. "
            f"Supported clients: {supported}"
        )
    return _FORMATTER_REGISTRY[key]
