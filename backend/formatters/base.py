"""
Abstract base class for all client formatters.

Every formatter must implement:
  - format_jd(data: dict) -> str   — renders the job description
  - format_email(data: dict) -> str — renders the outreach email
"""

from abc import ABC, abstractmethod
from html import escape
import re
from urllib.parse import urlsplit

try:
    from ..policy_utils import sanitize_scalar_eligibility
except ImportError:
    from policy_utils import sanitize_scalar_eligibility


class SafeHTML(str):
    """Marker type used to prevent accidental double escaping."""


def escape_html(value) -> SafeHTML:
    """Escape a dynamic value for HTML text or attribute interpolation."""
    if isinstance(value, SafeHTML):
        return value
    return SafeHTML(escape(str(value), quote=True))


def sanitize_http_url(value) -> str:
    """Return a trimmed absolute HTTP(S) URL, or an empty string when unsafe."""
    if not isinstance(value, str):
        return ""
    url = value.strip()
    if not url or any(ch.isspace() or ord(ch) < 32 for ch in url):
        return ""
    try:
        parsed = urlsplit(url)
    except ValueError:
        return ""
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return ""
    return url


def safe_href(value) -> SafeHTML:
    """Validate and escape a URL for use in an HTML ``href`` attribute."""
    if isinstance(value, SafeHTML):
        return value
    return escape_html(sanitize_http_url(value))


def prepare_html_data(data: dict) -> dict:
    """Return a shallow, HTML-safe formatter payload with a safe link and Remote location."""
    prepared = {}
    for key, value in dict(data or {}).items():
        if key == "link":
            prepared[key] = safe_href(value)
        elif isinstance(value, str):
            prepared[key] = escape_html(sanitize_scalar_eligibility(value))
        elif isinstance(value, list):
            prepared[key] = [
                escape_html(cleaned)
                for item in value
                if item is not None
                for cleaned in [sanitize_scalar_eligibility(str(item))]
                if cleaned
            ]
        else:
            prepared[key] = value
    prepared["location"] = SafeHTML("Remote")
    return prepared


def omit_empty_html_sections(value: str) -> str:
    """Remove formatter headings, rows, and lists whose dynamic content is empty."""
    if not value:
        return value
    cleaned = str(value)
    cleaned = re.sub(
        r"(?is)<b>[^<]+</b>\s*(?:<br>\s*)?<ul>\s*</ul>\s*<br>",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"(?im)^[ \t]*<b>[^<]+:</b>[ \t]+<br>[ \t]*(?:\r?\n)?",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"(?is)<b>[^<]+</b><br>\s*(?:<br>\s*){2,}",
        "",
        cleaned,
    )
    return re.sub(r"(?:\r?\n){3,}", "\n\n", cleaned).strip()


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
