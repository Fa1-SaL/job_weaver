"""Deterministic content-policy helpers shared by parsers and formatters."""

import re


_NUMBER_WORD = (
    r"one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
    r"twenty(?:[-\s](?:one|two|three|four|five|six|seven|eight|nine))?"
)

_ELIGIBILITY_SUBJECT = (
    r"(?:candidates?|applicants?|contributors?|contractors?|workers?|"
    r"individuals?|persons?|professionals?|you)"
)
_AGE_NUMBER = rf"(?:\d{{1,3}}|{_NUMBER_WORD})"
_AGE_VALUE = (
    rf"(?:at\s+least\s+)?{_AGE_NUMBER}"
    rf"(?:\s*\+|\s+years?\s+(?:old|of\s+age)|"
    rf"(?:\s+years?)?\s+(?:or|and)\s+(?:older|over|above))"
    rf"|(?:over|under|older\s+than)\s+(?:the\s+age\s+of\s+)?{_AGE_NUMBER}"
    rf"|between\s+{_AGE_NUMBER}\s+and\s+{_AGE_NUMBER}\s+years?\s+(?:old|of\s+age)"
)

# Age language is prohibited only when it describes candidate eligibility.
# Domain content about patients, products, datasets, or users must remain.
_AGE_PATTERNS = (
    re.compile(
        rf"(?ix)\b(?:minimum\s+age(?:\s+of)?|age\s+(?:requirement|limit|range)(?:\s+is)?|required\s+age)"
        rf"\s*:?\s*{_AGE_NUMBER}(?:\s*\+|(?:\s+years?)?\s+(?:or|and)\s+(?:older|over|above))?\b"
    ),
    re.compile(
        rf"(?ix)\b{_ELIGIBILITY_SUBJECT}\s+"
        rf"(?:(?:must|should|required\s+to|need(?:s)?\s+to)\s+(?:be\s+)?|(?:are|is)\s+)?"
        rf"(?:aged?\s+)?(?:{_AGE_VALUE}|adults?\b)"
    ),
    re.compile(
        rf"(?ix)\b{_ELIGIBILITY_SUBJECT}\s+(?:must|should|required\s+to|need(?:s)?\s+to)\s+"
        rf"have\s+reached\s+(?:the\s+)?age(?:\s+of)?\s+{_AGE_NUMBER}\b"
    ),
    re.compile(
        rf"(?ix)^\s*(?:must|should|required\s+to|need\s+to)\s+be\s+"
        rf"(?:{_AGE_VALUE}|(?:an?\s+)?adult|of\s+legal\s+age)\b"
    ),
    re.compile(r"(?ix)^\s*(?:only\s+)?adults?\s+only\b|^\s*only\s+adults?\s+(?:may|can)\s+apply\b"),
)

_GEO_ACTION = (
    r"(?:based|located|living|reside|residing|resident|live|work|"
    r"be\s+(?:in|within|from))"
)
_IMMIGRATION_TERM = (
    r"(?:visa\s+sponsorship|work\s+visa|citizenship|work\s+permit|"
    r"h-?1b|stem\s+opt|authori[sz](?:ed|ation)\s+to\s+work)"
)

# Geography/domain terms are contextual: only candidate eligibility and role
# availability constraints are removed. Legal, immigration, and population
# analysis responsibilities are preserved.
_GEO_PATTERNS = (
    re.compile(
        rf"(?ix)\b{_ELIGIBILITY_SUBJECT}\b.{{0,24}}"
        rf"\b(?:must|required|need(?:s)?|should|only|currently)\b.{{0,20}}\b{_GEO_ACTION}\b"
    ),
    re.compile(
        rf"(?ix)\b{_ELIGIBILITY_SUBJECT}\s+(?:who\s+are\s+)?"
        rf"(?:based|located|living|residing|resident|from|in|within)\b.{{0,45}}\b(?:only|may\s+apply|required)\b"
    ),
    re.compile(
        r"(?ix)\b(?:only\s+)?(?:candidates?|applicants?|contributors?)\s+"
        r"(?:who\s+are\s+)?(?:from|in|within)\b"
    ),
    re.compile(r"(?ix)\bopen\s+to\s+(?:candidates?|applicants?)\s+(?:from|in|within)\b"),
    re.compile(
        rf"(?ix)^\s*(?:must|required\s+to|need\s+to|should)\s+"
        rf"(?:currently\s+)?(?:be\s+)?{_GEO_ACTION}\b"
    ),
    re.compile(r"(?ix)\bremote\s+(?:only\s+)?within\b"),
    re.compile(r"(?ix)\b(?:this\s+)?role\s+is\s+(?:open|available)\s+only\s+(?:in|within|to)\b"),
    re.compile(r"(?ix)\bwork\s+(?:for\s+this\s+role\s+)?must\s+be\s+(?:performed|completed|done)\s+(?:in|within|from)\b"),
    re.compile(r"(?ix)^\s*(?:must|required\s+to|need\s+to|should)\s+be\s+in\s+(?:the\s+)?[A-Z]{2,5}\s+time\s*zone\b"),
    re.compile(r"(?ix)\b(?:must|required\s+to|need\s+to|should)\s+(?:work|be\s+available)\s+(?:in|during)\s+(?:the\s+)?[A-Z]{2,5}\s+time\s*zone\b"),
    re.compile(
        rf"(?ix)\b{_ELIGIBILITY_SUBJECT}\b.{{0,30}}"
        rf"\b(?:must|required|need(?:s)?|should|only|eligible)\b.{{0,24}}\b{_IMMIGRATION_TERM}\b"
    ),
    re.compile(
        rf"(?ix)^\s*(?:must|required\s+to|need\s+to|should)\s+"
        rf"(?:have|hold|obtain|be\s+eligible\s+for)?\s*{_IMMIGRATION_TERM}\b"
    ),
    re.compile(r"(?ix)^\s*(?:no|without)\s+(?:visa\s+sponsorship|work\s+visa|h-?1b|stem\s+opt)\b"),
    re.compile(r"(?ix)\blocation\s+requirements?\b"),
    re.compile(
        r"(?ix)^\s*(?:united\s+states|u\.?s\.?(?:a\.?)?|canada|united\s+kingdom|u\.?k\.?|"
        r"india|australia|germany|france|brazil)\s+citizens?\s+only\b"
    ),
)


def is_age_eligibility(text: str) -> bool:
    """Return True only for age eligibility language, not experience duration."""
    value = str(text or "")
    return any(pattern.search(value) for pattern in _AGE_PATTERNS)


def is_geography_constraint(text: str) -> bool:
    """Detect location/residency eligibility without treating ``US`` as a bare keyword."""
    value = str(text or "")
    return any(pattern.search(value) for pattern in _GEO_PATTERNS)


def is_prohibited_eligibility(text: str) -> bool:
    return is_age_eligibility(text) or is_geography_constraint(text)


def remove_prohibited_sentences(text: str) -> str:
    """Drop full age/geography eligibility sentences while retaining ordinary prose."""
    if not text:
        return text
    pieces = re.split(r"(?<=[.!?])\s+|[\r\n]+", str(text))
    kept = [piece.strip() for piece in pieces if piece.strip() and not is_prohibited_eligibility(piece)]
    return " ".join(kept).strip()


def sanitize_scalar_eligibility(text: str) -> str:
    """Remove compact eligibility qualifiers from rendered scalar fields."""
    if not text:
        return text
    value = str(text).strip()
    value = re.sub(
        r"(?ix)^\s*(?:\d{1,2}\s*\+|adults?\s+only)\s*[-–—|:]?\s*",
        "",
        value,
    )
    value = re.sub(
        r"(?ix)\s*(?:[-–—|,]|\bfor\b)\s*"
        r"(?:united\s+states|u\.?s\.?(?:a\.?)?|canada|united\s+kingdom|u\.?k\.?|"
        r"india|australia|germany|france|brazil|europe|new\s+york|berlin|bangalore|bengaluru)"
        r"(?:\s+(?:residents?|candidates?|applicants?))?\s+only\s*$",
        "",
        value,
    )
    value = re.sub(
        r"(?ix)\s+for\s+[A-Za-z][\w.]+(?:\s+[A-Za-z][\w.]+){0,3}\s+residents?\s+only\s*$",
        "",
        value,
    )
    value = re.sub(
        r"\s*[-–—|,]\s*(?!(?:Part|Full|Weekends?|Weekdays?|Day|Night|Contract|Temporary)\b)"
        r"[A-Z][A-Za-z.]+(?:\s+[A-Z][A-Za-z.]+){0,2}\s+only\s*$",
        "",
        value,
    )
    value = remove_prohibited_sentences(value)
    return re.sub(r"\s{2,}", " ", value).strip(" \t,|–—-")
