"""
Abstract base class for all client formatters.

Every formatter must implement:
  - format_jd(data: dict) -> str   — renders the job description
  - format_email(data: dict) -> str — renders the outreach email
"""

from abc import ABC, abstractmethod


class ClientFormatter(ABC):
    """Base formatter interface. All client formatters must subclass this."""

    @abstractmethod
    def format_jd(self, data: dict) -> str:
        """
        Render the job description from structured *data*.

        Args:
            data: Normalised job data dict (see OUTPUT_SCHEMA in llm_jd_parser.py).

        Returns:
            Formatted JD string (HTML or plain-text, depending on client).
        """
        ...

    @abstractmethod
    def format_email(self, data: dict) -> str:
        """
        Render the outreach email body from structured *data*.

        Args:
            data: Normalised job data dict.

        Returns:
            Formatted email string (HTML or plain-text).
        """
        ...
