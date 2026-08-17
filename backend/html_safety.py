"""Small allowlist sanitizer for generated rich-text output.

Job Weaver intentionally returns a limited HTML subset for rich clipboard
formatting. LLM-controlled and request-controlled values must not be able to
introduce executable markup or unsafe URL schemes into that subset.
"""

from __future__ import annotations

from html import escape, unescape
from html.parser import HTMLParser
import re
from typing import Iterable, Optional
from urllib.parse import urlsplit


_ALLOWED_TAGS = {
    "a",
    "b",
    "br",
    "em",
    "i",
    "li",
    "ol",
    "p",
    "span",
    "strong",
    "ul",
}
_VOID_TAGS = {"br"}
_DROP_CONTENT_TAGS = {"iframe", "math", "object", "script", "style", "svg"}
_SAFE_STYLE_PROPERTIES = {"color", "font-weight", "text-decoration"}
_SAFE_STYLE_VALUES = {
    "color": re.compile(r"^#[0-9a-f]{3,8}(?:\s*!important)?$", re.IGNORECASE),
    "font-weight": re.compile(r"^(?:normal|bold|[1-9]00)(?:\s*!important)?$", re.IGNORECASE),
    "text-decoration": re.compile(r"^(?:none|underline)(?:\s*!important)?$", re.IGNORECASE),
}


def _safe_href(value: str) -> Optional[str]:
    candidate = unescape(value).strip()
    if not candidate or any(ord(char) < 32 for char in candidate):
        return None
    if candidate.startswith("#"):
        return candidate
    parts = urlsplit(candidate)
    if parts.scheme.casefold() not in {"http", "https", "mailto"}:
        return None
    if parts.scheme.casefold() in {"http", "https"} and not parts.hostname:
        return None
    return candidate


def _safe_style(value: str) -> Optional[str]:
    declarations = []
    for declaration in value.split(";"):
        if ":" not in declaration:
            continue
        name, raw_value = declaration.split(":", 1)
        name = name.strip().casefold()
        style_value = raw_value.strip()
        if name not in _SAFE_STYLE_PROPERTIES or not _SAFE_STYLE_VALUES[name].fullmatch(style_value):
            continue
        declarations.append(f"{name}: {style_value}")
    return "; ".join(declarations) or None


class _RichTextSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.output: list[str] = []
        self._drop_depth = 0

    def handle_starttag(self, tag: str, attrs: Iterable[tuple[str, Optional[str]]]) -> None:
        tag = tag.casefold()
        if tag in _DROP_CONTENT_TAGS:
            self._drop_depth += 1
            return
        if self._drop_depth or tag not in _ALLOWED_TAGS:
            return

        safe_attrs: list[tuple[str, str]] = []
        for name, value in attrs:
            if value is None:
                continue
            name = name.casefold()
            if tag == "a" and name == "href":
                href = _safe_href(value)
                if href:
                    safe_attrs.append(("href", href))
            elif tag in {"a", "span"} and name == "style":
                style = _safe_style(value)
                if style:
                    safe_attrs.append(("style", style))

        rendered_attrs = "".join(
            f' {name}="{escape(value, quote=True)}"' for name, value in safe_attrs
        )
        self.output.append(f"<{tag}{rendered_attrs}>")

    def handle_startendtag(
        self, tag: str, attrs: Iterable[tuple[str, Optional[str]]]
    ) -> None:
        self.handle_starttag(tag, attrs)
        if tag.casefold() not in _VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag in _DROP_CONTENT_TAGS:
            self._drop_depth = max(0, self._drop_depth - 1)
            return
        if self._drop_depth or tag not in _ALLOWED_TAGS or tag in _VOID_TAGS:
            return
        self.output.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self._drop_depth:
            self.output.append(escape(data, quote=False))

    def handle_entityref(self, name: str) -> None:
        if not self._drop_depth:
            self.output.append(f"&amp;{escape(name)};")

    def handle_charref(self, name: str) -> None:
        if not self._drop_depth:
            self.output.append(f"&amp;#{escape(name)};")


def sanitize_rich_html(value: object) -> object:
    if not isinstance(value, str) or not value:
        return value
    parser = _RichTextSanitizer()
    parser.feed(value)
    parser.close()
    return "".join(parser.output)


def sanitize_result_html(data: dict) -> dict:
    sanitized = dict(data)
    for field in ("jd", "email", "inmail_draft", "email_draft"):
        if field in sanitized:
            sanitized[field] = sanitize_rich_html(sanitized[field])
    return sanitized
