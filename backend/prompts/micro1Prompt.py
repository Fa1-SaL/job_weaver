"""
Micro1 LLM extraction prompt.

Micro1 uses the same JSON extraction logic as Mercor.
Client name substitution ({CLIENT_NAME}) is handled by the orchestrator.
"""

# Micro1 uses the same extraction prompt as Mercor — imported for DRY-ness.
# If Micro1-specific rules are needed in the future, override PROMPT_TEMPLATE here.
from prompts.mercorPrompt import PROMPT_TEMPLATE  # noqa: F401
