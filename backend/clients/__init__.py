"""
Client registry — single source of truth for all supported clients.

Usage:
    from clients import get_client_config, CLIENT_REGISTRY

    config = get_client_config("turing")
    print(config["displayName"])  # "Turing"
"""

from typing import Dict, Any, Set

from clients.mercor import CONFIG as MERCOR_CONFIG
from clients.micro1 import CONFIG as MICRO1_CONFIG
from clients.turing import CONFIG as TURING_CONFIG
from clients.domain_pages import DOMAIN_PAGES_REGISTRY, DOMAIN_PAGE_KEYS

# ── Registry ──────────────────────────────────────────────────────────────────
CLIENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "mercor": MERCOR_CONFIG,
    "micro1": MICRO1_CONFIG,
    "turing": TURING_CONFIG,
    **DOMAIN_PAGES_REGISTRY,
}

SUPPORTED_CLIENTS = list(CLIENT_REGISTRY.keys())


def get_client_config(client_id: str) -> Dict[str, Any]:
    """
    Return the config dict for *client_id* (case-insensitive).

    Raises:
        ValueError: if the client is not registered.
    """
    key = client_id.strip().lower()
    if key not in CLIENT_REGISTRY:
        raise ValueError(
            f"Unsupported client '{client_id}'. "
            f"Supported clients: {SUPPORTED_CLIENTS}"
        )
    return CLIENT_REGISTRY[key]

