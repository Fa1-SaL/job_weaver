"""
Prompt registry — maps client IDs to their LLM extraction prompt templates.

Usage:
    from prompts import get_prompt

    prompt_text = get_prompt("turing")
"""

from typing import Dict

import prompts.mercorPrompt as _mercor
import prompts.micro1Prompt as _micro1
import prompts.turingPrompt as _turing

from clients import DOMAIN_PAGE_KEYS

_PROMPT_REGISTRY: Dict[str, str] = {
    "mercor": _mercor.PROMPT_TEMPLATE,
    "micro1": _micro1.PROMPT_TEMPLATE,
    "turing": _turing.PROMPT_TEMPLATE,
}
for dp_key in DOMAIN_PAGE_KEYS:
    _PROMPT_REGISTRY[dp_key] = _mercor.PROMPT_TEMPLATE



def get_prompt(client_id: str) -> str:
    """
    Return the LLM extraction prompt template for *client_id* (case-insensitive).

    Raises:
        ValueError: if no prompt is registered for the client.
    """
    key = client_id.strip().lower()
    if key not in _PROMPT_REGISTRY:
        supported = list(_PROMPT_REGISTRY.keys())
        raise ValueError(
            f"No prompt registered for client '{client_id}'. "
            f"Supported clients: {supported}"
        )
    return _PROMPT_REGISTRY[key]
