import os
import json
import re
import time
from pathlib import Path
from typing import Tuple, Any, Dict, List
from openai import OpenAI
from dotenv import load_dotenv

# ── Registry imports ─────────────────────────────────────────────────────────
try:  # Package import (``backend.llm_jd_parser``)
    from .clients import get_client_config, CLIENT_REGISTRY, SUPPORTED_CLIENTS, DOMAIN_PAGE_KEYS
    from .formatters import get_formatter
    from .formatters.base import sanitize_http_url
    from .formatters.domainPagesFormatter import scrub_all_client_orgs_from_jd
    from .policy_utils import is_geography_constraint, is_prohibited_eligibility, remove_prohibited_sentences, sanitize_scalar_eligibility
    from .prompts import get_prompt
except ImportError:  # Script import from the backend working directory
    from clients import get_client_config, CLIENT_REGISTRY, SUPPORTED_CLIENTS, DOMAIN_PAGE_KEYS
    from formatters import get_formatter
    from formatters.base import sanitize_http_url
    from formatters.domainPagesFormatter import scrub_all_client_orgs_from_jd
    from policy_utils import is_geography_constraint, is_prohibited_eligibility, remove_prohibited_sentences, sanitize_scalar_eligibility
    from prompts import get_prompt

# Explicitly load .env from the project root without replacing deployment
# environment variables. Process-level configuration must win during rotations
# and container/orchestrator deployments.
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=False)

_openai_client = None
OUTPUT_VERSION = "v4"


def _get_openai_client() -> OpenAI:
    """Create the OpenAI client only when an LLM call is actually requested."""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in environment variables.")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client

# ── Output schema ─────────────────────────────────────────────────────────────
OUTPUT_SCHEMA = {
    "role": "",
    "type": "",
    "pay": "",
    "location": "",
    "commitment": "",
    "role_responsibilities": [],
    "requirements": [],
    "preferred_qualifications": [],
    "role_overview": "",
    "who_this_is_for": "",
    "where_you_will": "",
    "start_date": "",
    "client": "",
    "client_desc": "",
    "link": "",
    "suggested_titles": [],
    "subject": "",
    "linkedin_title": "",
    "skills": [],
    "job_functions": [],
    "industries": [],
    "justifications": {}
}

# ── 1. LLM Call ───────────────────────────────────────────────────────────────

def generate_llm_output(raw_jd: str, client_name: str = "mercor") -> str:
    """Takes a raw JD, sends to LLM, returns raw JSON response text."""
    config = get_client_config(client_name)
    prompt_template = get_prompt(client_name)

    prompt = prompt_template.replace("{CLIENT_NAME}", config["displayName"])
    prompt = prompt + raw_jd

    system_instruction = (
        "You output strict JSON only. Do not wrap in formatting blocks. "
        "CRITICAL INSTRUCTION: Remove any sort of date, turnaround deadline, or completion time limit if mentioned in the JD "
        "(for example, 'Your turnaround time will be 3 hours of conversation that needs to be filled before 12/28'). "
        "The output must not hint anything regarding deadlines, turnaround windows, or completion dates while keeping all other details covered exactly."
    )
    if client_name and client_name.strip().lower() in DOMAIN_PAGE_KEYS:
        system_instruction += (
            " CRITICAL NEGATIVE PROMPT FOR DOMAIN PAGES: Never ever mention Mercor, Cincinnatus, or any client/platform "
            "organization name even if present in the raw input JD. Keep the client confidential without stating or mentioning "
            "that it is confidential — sneakingly do not mention Mercor, Cincinnatus, or any client/platform organization name anywhere in the output."
        )

    _t0 = time.time()
    response = _get_openai_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )
    print(f"[LLM] Response time: {time.time() - _t0:.2f}s")

    return response.choices[0].message.content


# ── 2. Normalization and Cleaning Utilities ───────────────────────────────────

def normalize_client(client: str) -> str:
    if not client or "default" in client.lower():
        return "mercor"
    return client.strip().lower()

VALID_JOB_FUNCTIONS = [
    "Accounting & Auditing", "Administrative", "Advertising", "Analytics",
    "Customer Service", "Design", "Education", "Engineering", "Finance",
    "General Business", "Health care provider", "Human Resources", "IT",
    "Legal", "Manufacturing", "Marketing", "Product Management",
    "Project Management", "Public Relations", "Research", "Sales",
    "Strategy/Planning", "Training", "Consulting", "Writing/Editing",
    "Art/Creative"
]

VALID_INDUSTRIES = [
    "Accommodation and Food Services", "Administrative and Support Services",
    "Construction", "Consumer Services", "Education", "Entertainment Providers",
    "Farming, Ranching, Forestry", "Financial Services", "Government Administration",
    "Holding Companies", "Hospitals and Health Care", "Manufacturing",
    "Oil, Gas, and Mining", "Professional Services",
    "Real Estate and Equipment Rental Services", "Retail",
    "Technology, Information and Media",
    "Transportation, Logistics, Supply Chain and Storage", "Utilities",
    "Wholesale", "Research Services", "Investment Management",
    "Strategic Management Services", "Information Services", "Higher Education",
    "Primary and Secondary Education", "Medical Practices",
    "Translation and Localization"
]

def clean_category_list(items, valid_list):
    """Validate category values without inventing unrelated list entries."""
    if not isinstance(items, list): items = []
    cleaned = []
    for i in items:
        i_str = str(i).strip().lower()
        for v in valid_list:
            if v.lower() == i_str:
                if v not in cleaned:
                    cleaned.append(v)
                break

    # Failsafe 1: fill remaining slots via keyword-overlap scoring
    if len(cleaned) < 3:
        scored = []
        items_combined = " ".join(str(i).lower() for i in items)
        for v in valid_list:
            if v in cleaned:
                continue
            keywords = re.split(r'[\s,/&]+', v.lower())
            score = sum(1 for k in keywords if k and k in items_combined)
            if score > 0:
                scored.append((score, v))
        scored.sort(key=lambda x: -x[0])
        for _, v in scored:
            if v not in cleaned:
                cleaned.append(v)
            if len(cleaned) >= 3:
                break

    return cleaned[:3]

_SKILL_VERB_PREFIXES = (
    "using ", "leveraging ", "applying ", "developing ", "building ",
    "creating ", "managing ", "driving ", "analyzing ", "designing "
)

def clean_skills(skills: list, role: str = "") -> list:
    """Post-filter LLM skills: remove niche, verbose, or role-repeating entries."""
    if not isinstance(skills, list):
        skills = []
    role_lower = role.lower()
    cleaned = []
    seen = set()
    for s in skills:
        if not isinstance(s, str):
            continue
        s = s.strip()
        if not s:
            continue
        if len(s.split()) > 3:
            continue
        s_lower = s.lower()
        if any(s_lower.startswith(p) for p in _SKILL_VERB_PREFIXES):
            continue
        if s_lower == role_lower:
            continue
        if s_lower in seen:
            continue
        seen.add(s_lower)
        cleaned.append(s)
    return cleaned[:5]

def normalize_commitment(commitment: str) -> str:
    if not commitment:
        return ""
    return "10-40 hrs/week"

def clean_experience_phrases(text: str) -> str:
    if not text:
        return text

    original_text = str(text)
    original_started_upper = original_text.lstrip()[:1].isupper()
    number = (
        r"(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|"
        r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|"
        r"nineteen|twenty(?:[-\s](?:one|two|three|four|five|six|seven|eight|nine))?)"
    )
    duration = rf"""
        (?:(?:at\s+least|(?:a\s+)?minimum(?:\s+of)?|more\s+than|over|up\s+to|(?:not|no)\s+less\s+than)\s+|between\s+)?
        {number}
        (?:\s*(?:[-–—]|to|and)\s*{number})?
        (?:\s*\+|\s+or\s+more)?
        \s*(?:years?|yrs?\.?)['’]?
    """
    original_started_with_duration = bool(
        re.match(
            rf"(?ix)^\s*(?:an?\s+)?(?:(?:at\s+least|minimum(?:\s+of)?|between)\s+)?{number}",
            original_text,
        )
    )

    adjectival_pattern = re.compile(
        rf'''(?ix)
        \b(?:an?\s+)?{number}(?:\s*[-–—]\s*{number})?\s*[-–—]\s*year\s+
        (?:(?:relevant|professional|industry|domain|technical|practical|hands-on)\s+)?
        (?:experience|background)\b
        ''',
    )
    text, replacements = adjectival_pattern.subn("strong relevant experience", text)

    # Duration followed by an experience phrase, including descriptors such as
    # "hands-on machine learning". Education, age, training, and residency
    # durations are explicitly excluded.
    experience_duration_pattern = re.compile(
        rf'''
        \b{duration}
        (?:\s+of)?\s+
        (?:
            (?!
                (?:age|old|college|education|study|studies|degree|degrees|
                   training|residency|and|or|but|nor|with|without|before|after|
                   during|plus|including|followed|have|has|having|had|who|that|which)\b
            )
            (?!experience\b)[\w/&,+’'–—-]+[ \t]+
        ){{0,4}}
        experience\b
        ''',
        flags=re.IGNORECASE | re.VERBOSE,
    )
    text, count = experience_duration_pattern.subn("strong relevant experience", text)
    replacements += count

    # Experience-first variants: "minimum experience of 2 years" and
    # "professional experience: two years".
    experience_first_pattern = re.compile(
        rf'''(?ix)
        \b(?:minimum\s+|required\s+|relevant\s+|professional\s+)?experience
        (?:\s+(?:requirement|required))?\s*(?::|of|is)?\s*{duration}\b
        ''',
    )
    text, count = experience_first_pattern.subn("strong relevant experience", text)
    replacements += count

    # Postfix work-history variants. Require candidate/requirement grammar (or
    # a duration-led standalone bullet) so company/project timelines are not
    # mistaken for candidate experience.
    postfix_work_pattern = re.compile(
        rf'''(?ix)
        (?P<leading>
            \b(?:(?:must|should)\s+have\s+|(?:required|need(?:s)?)\s+to\s+have\s+)
            |
            \b(?:candidates?|applicants?|you)\s+(?:have|has|had)\s+
            |
            ^\s*
        )
        (?:been\s+)?
        (?:worked|working|employed|served|practiced|practised)
        (?P<context>(?:[ \t]+(?!for\b)[^.!?;:\r\n]+?)?)
        [ \t]+for[ \t]+{duration}\b
        ''',
    )

    def replace_postfix_work(match: re.Match) -> str:
        leading = match.group("leading")
        context = " ".join((match.group("context") or "").split())
        context_suffix = f" {context}" if context else ""
        return f"{leading}strong relevant experience{context_suffix}"

    text, count = postfix_work_pattern.subn(replace_postfix_work, text)
    replacements += count

    role_tenure_pattern = re.compile(
        rf'''(?ix)
        (?P<leading>
            \b(?:(?:must|should)\s+have\s+|(?:required|need(?:s)?)\s+to\s+have\s+)
            |
            \b(?:candidates?|applicants?|you)\s+(?:have|has|had)\s+
        )
        been\s+(?:an?\s+)?(?:senior\s+|lead\s+)?
        (?:analysts?|engineers?|developers?|managers?|researchers?|designers?|consultants?|
           specialists?|professionals?|practitioners?|scientists?|accountants?|attorneys?|
           lawyers?|teachers?|writers?|editors?)
        [ \t]+for[ \t]+{duration}\b
        ''',
    )
    text, count = role_tenure_pattern.subn(
        lambda match: f"{match.group('leading')}strong relevant experience",
        text,
    )
    replacements += count

    synonym_duration_pattern = re.compile(
        rf'''(?ix)
        (?P<leading>
            ^\s*
            |
            \b(?:(?:must|should)\s+(?:have\s+)?|(?:require(?:s|d)?|need(?:s)?(?:\s+to)?)\s+(?:have\s+)?)
            |
            \b(?:candidates?|applicants?|you)\s+(?:have|bring)\s+
        )
        {duration}(?:\s+of)?\s+
        (?:(?:relevant|professional|industry|domain|technical|practical|hands-on|full-time)\s+){{0,3}}
        (?:background|expertise|work)\b
        ''',
    )
    text, count = synonym_duration_pattern.subn(
        lambda match: f"{match.group('leading')}strong relevant experience",
        text,
    )
    replacements += count

    # Work-context variants without the word "experience":
    # "3 years working with Python", "two years as an analyst".
    work_context_pattern = re.compile(
        rf'''(?ix)
        (?P<leading>
            ^\s*
            |
            \b(?:(?:must|should)\s+(?:have\s+)?|(?:require(?:s|d)?|need(?:s)?(?:\s+to)?)\s+(?:have\s+)?)
            |
            \b(?:candidates?|applicants?|you)\s+(?:have|bring)\s+
        )
        {duration}\b
        (?=\s+(?:working|using|developing|building|practicing|practising|performing|
                     managing|leading|serving|employed|as|with|in)\b
            (?!\s+(?:college|education|study|studies|degree|training|residency)\b))
        ''',
    )
    text, count = work_context_pattern.subn(
        lambda match: f"{match.group('leading')}strong relevant experience",
        text,
    )
    replacements += count

    # A requirement expressed solely as a duration or followed by
    # "required/preferred" still represents experience in this field.
    standalone_pattern = re.compile(
        rf'''(?ix)^\s*(?:experience\s*:\s*)?{duration}\s*(?:required|preferred|desired)?\s*([.!?]?)\s*$'''
    )
    if standalone_pattern.match(text):
        punctuation = standalone_pattern.match(text).group(1) or ""
        text = f"strong relevant experience{punctuation}"
        replacements += 1

    if replacements:
        # In the reported Masters-studies construction, experience remains an
        # additional requirement. Keep genuine alternative qualifications as-is.
        text = re.sub(
            r'''(?ix)
            (
                currently[ \t]+pursuing[ \t]+or[ \t]+recently[ \t]+completed
                [ \t]+(?:a[ \t]+)?master(?:['’]?s)?[ \t]+(?:degree|studies),[ \t]*
            )
            or(?=[ \t]+have[ \t]+strong[ \t]+relevant[ \t]+experience\b)
            ''',
            r'\1and',
            text,
        )

    text = " ".join(text.split())
    if (original_started_upper or original_started_with_duration) and text[:1].islower():
        text = text[0].upper() + text[1:]
    return text.strip()

def normalize_role(role: str) -> str:
    if not role:
        return ""
    # Remove any ID patterns (e.g. "ID: 12345", "ID-12345", "ID 12345") case-insensitively
    role = re.sub(r'(?i)\bID\s*[:-]?\s*\d+\b', '', role)
    # Remove bracketed and parenthesized expressions (like [Task-based], (Remote), etc.)
    role = re.sub(r'\[[^\]]*\]', '', role)
    role = re.sub(r'\([^)]*\)', '', role)
    places = (
        r"united\s+states|u\.?s\.?(?:a\.?)?|canada|united\s+kingdom|u\.?k\.?|"
        r"india|australia|germany|france|brazil|singapore|europe|asia|apac|emea|"
        r"new\s+york|london|berlin|bangalore|bengaluru|mumbai|delhi|toronto|"
        r"vancouver|sydney|melbourne|paris|tokyo|dubai"
    )
    role = re.sub(
        r"^\s*(?!(?:Evidence|Research|Skill|Competency|Performance|Project|Team|Web|Cloud)\b)"
        r"[A-Z][a-z]{2,}\s*[- ]based\s*[-–—|:]?\s*",
        "",
        role,
    )
    role = re.sub(
        rf"(?i)^\s*(?:{places})\s*[-–— ]\s*(?:based|only)\s*[-–—|:]?\s*",
        "",
        role,
    )
    role = re.sub(
        rf"(?i)^\s*(?:remote|hybrid|on-?site)\s*[-–—|:]\s*",
        "",
        role,
    )
    role = re.sub(
        rf"(?i)\s*[-–—|,]\s*(?:{places}|remote|hybrid|on-?site)\s*$",
        "",
        role,
    )
    # Remove trailing/leading symbol clutter (pipes, dashes, colons, spaces)
    role = re.sub(r'\s*[|\-:\s]+$', '', role)
    role = re.sub(r'^[|\-:\s]+', '', role)
    return " ".join(role.split())

def normalize_requirements(requirements: List[str]) -> List[str]:
    cleaned = []
    for r in requirements:
        if not r or not r.strip():
            continue
        r = clean_experience_phrases(r)
        if not r:
            continue
        cleaned.append(r[0].upper() + r[1:])
    return list(dict.fromkeys(cleaned))

def strip_deadlines_and_dates(text: str) -> str:
    if not text:
        return text
    sentences = re.split(r'(?<=[.!?])\s+', text)
    cleaned = []
    deadline_pattern = re.compile(
        r'(?i)\b(before \d{1,2}/\d{1,2}|turnaround time|to be filled before|filled before|deadline|complete before|submit by|apply by|\d{1,2}(?:st|nd|rd|th)?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december))\b'
    )
    for sentence in sentences:
        if deadline_pattern.search(sentence):
            continue
        cleaned.append(sentence.strip())
    return " ".join([s for s in cleaned if s]).strip()

def filter_requirements(requirements: List[str]) -> List[str]:
    filtered = []
    deadline_pattern = re.compile(
        r'(?i)\b(before \d{1,2}/\d{1,2}|turnaround time|to be filled before|filled before|deadline|complete before|submit by|apply by|\d{1,2}(?:st|nd|rd|th)?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december))\b'
    )

    for r in requirements:
        if is_prohibited_eligibility(r) or deadline_pattern.search(r):
            continue
        filtered.append(r)

    return filtered


def filter_optional_requirements(requirements: List[str]) -> List[str]:
    """Apply requirement policies without adding mandatory fallback bullets."""
    deadline_pattern = re.compile(
        r'(?i)\b(before \d{1,2}/\d{1,2}|turnaround time|to be filled before|filled before|deadline|complete before|submit by|apply by|\d{1,2}(?:st|nd|rd|th)?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december))\b'
    )
    return [
        item for item in requirements
        if item and not is_prohibited_eligibility(item) and not deadline_pattern.search(item)
    ]

def filter_responsibilities(responsibilities: List[str]) -> List[str]:
    filtered = []
    deadline_pattern = re.compile(
        r'(?i)\b(before \d{1,2}/\d{1,2}|turnaround time|to be filled before|filled before|deadline|complete before|submit by|apply by|\d{1,2}(?:st|nd|rd|th)?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december))\b'
    )
    for r in responsibilities:
        if is_prohibited_eligibility(r) or deadline_pattern.search(r):
            continue
        filtered.append(r)
    return filtered

def normalize_text_block(text: str) -> str:
    if not text: return text
    text = text.strip()
    text = text.replace("///", "/")
    text = text.replace("//", "/")
    text = " ".join(text.split())
    if text:
        text = text[0].upper() + text[1:]
    return text

def format_bullet(text: str) -> str:
    if not text: return text
    text = text.strip()
    return text[0].upper() + text[1:] if len(text) > 0 else text

def normalize_compensation(pay: str) -> str:
    if not pay:
        return pay

    pay = pay.strip()
    match = re.match(
        r'^\$0(?:\.0+)?\s*[-–—]\s*\$?\s*(\d[\d,]*(?:\.\d+)?)\s*(.*)$',
        pay,
        flags=re.IGNORECASE,
    )

    if match:
        max_val = match.group(1)
        suffix = match.group(2).strip()
        separator = " " if suffix and not suffix.startswith("/") else ""
        return f"Up to ${max_val}{separator}{suffix}".strip()

    return pay

def normalize_data(data: dict, client_id: str) -> dict:
    config = get_client_config(client_id)

    # Always normalise client to the registry display name
    data["client"] = config["displayName"]
    data["client_desc"] = config["description"]

    data["pay"] = normalize_compensation(data.get("pay", ""))
    data["commitment"] = normalize_commitment(data.get("commitment", ""))
    data["role"] = normalize_role(
        sanitize_scalar_eligibility(data.get("role", ""))
    )
    for scalar_field in ("role", "type", "pay", "commitment"):
        data[scalar_field] = sanitize_scalar_eligibility(data.get(scalar_field, ""))
    data["location"] = "Remote"
    data["link"] = sanitize_http_url(data.get("link", ""))

    reqs = normalize_requirements(data.get("requirements", []))
    data["requirements"] = filter_requirements(reqs)

    preferred = normalize_requirements(data.get("preferred_qualifications", []))
    data["preferred_qualifications"] = filter_optional_requirements(preferred)

    who_for = clean_experience_phrases(data.get("who_this_is_for", ""))
    who_for = remove_prohibited_sentences(who_for)
    data["who_this_is_for"] = normalize_text_block(who_for)

    where_will = clean_experience_phrases(data.get("where_you_will", ""))
    where_will = remove_prohibited_sentences(where_will).strip()
    if where_will:
        where_will = " ".join(where_will.split())
        if len(where_will) > 0:
            where_will = where_will[0].lower() + where_will[1:]
    data["where_you_will"] = where_will
    
    data["justifications"] = data.get("justifications", {})
    if not isinstance(data["justifications"], dict):
        data["justifications"] = {}

    if "role_overview" in data and isinstance(data["role_overview"], str):
        data["role_overview"] = clean_experience_phrases(data["role_overview"])
        data["role_overview"] = strip_deadlines_and_dates(data["role_overview"])
        data["role_overview"] = remove_prohibited_sentences(data["role_overview"])
    if "commitment" in data and isinstance(data["commitment"], str):
        data["commitment"] = strip_deadlines_and_dates(data["commitment"])
    if "who_this_is_for" in data and isinstance(data["who_this_is_for"], str):
        data["who_this_is_for"] = strip_deadlines_and_dates(data["who_this_is_for"])

    data["role_overview"] = normalize_text_block(data.get("role_overview", ""))

    unique_resps = []
    for resp in data.get("role_responsibilities", []):
        resp = clean_experience_phrases(resp)
        r_fmt = format_bullet(resp)
        if r_fmt and r_fmt not in unique_resps:
            unique_resps.append(r_fmt)
    data["role_responsibilities"] = filter_responsibilities(unique_resps)

    data["requirements"] = [clean_requirement_text(clean_text_artifacts(r)) for r in data["requirements"]]
    data["role_responsibilities"] = [clean_text_artifacts(r) for r in data["role_responsibilities"]]

    data["role_responsibilities"] = [r for r in data["role_responsibilities"] if r and r.strip()]
    data["requirements"] = [r for r in data["requirements"] if r and r.strip()]

    # Client-specific post-normalisation (type coercions, commitment overrides)
    if client_id == "micro1":
        if data.get("type", "").strip().lower() == "contractor":
            data["type"] = "Contract"
        type_lower = data.get("type", "").lower()
        is_fulltime = "full-time" in type_lower or "full time" in type_lower or "fulltime" in type_lower
        if not is_fulltime:
            data["commitment"] = "10-40 hrs/week"

    return data


# ── 3. Text Utilities ─────────────────────────────────────────────────────────

def is_remote_role(data: dict) -> bool:
    text_blob = " ".join([
        data.get("location", ""),
        data.get("role_overview", ""),
        data.get("who_this_is_for", "")
    ]).lower()
    return "remote" in text_blob

def is_geography_sentence(sentence: str) -> bool:
    return is_geography_constraint(sentence)

def clean_text_artifacts(text: str) -> str:
    if not text: return text
    text = re.sub(r',\s*,', ',', text)
    text = re.sub(r'\s+,', ',', text)
    text = re.sub(r',\s+', ', ', text)
    return text.strip()

def clean_requirement_text(text: str) -> str:
    if not text:
        return ""
    prefixes = [
        "candidates should ",
        "candidates must ",
        "the candidate should ",
        "the candidate must ",
        "you should ",
        "you must "
    ]
    t = str(text).strip()
    lower = t.lower()
    for p in prefixes:
        if lower.startswith(p):
            t = t[len(p):].strip()
            break

    if t:
        t = t[0].upper() + t[1:]
    return t

def remove_inline_geography(text: str) -> str:
    return remove_prohibited_sentences(text)

def remove_geography_sentences(text: str) -> str:
    if not text:
        return text

    sentences = re.split(r'(?<=[.!?])\s+', text)
    cleaned = []

    for sentence in sentences:
        if is_prohibited_eligibility(sentence):
            continue
        cleaned.append(sentence.strip())

    result = " ".join(cleaned).strip()
    result = re.sub(r'\s+,', ',', result)
    result = re.sub(r',\s*,', ',', result)
    result = re.sub(r'\s+', ' ', result)

    return result

def get_fallback_titles(role: str) -> List[str]:
    role = normalize_role(role) or "Role"
    return [role]

def clean_titles(titles: List[str], role: str) -> List[str]:
    cleaned = []
    role_lower = role.lower()
    role_mentions_ai = bool(re.search(r"\bai\b", role_lower))
    seen = set()

    if not isinstance(titles, list):
        titles = []
    for t in titles:
        if not isinstance(t, str):
            continue
        t = normalize_role(t.strip())
        if not t:
            continue
        t_lower = t.lower()

        if len(t.split()) > 8:
            continue

        if any(bad in t_lower for bad in ["expert", "generalist"]):
            continue

        if re.search(r"\bai\b", t_lower) and not role_mentions_ai:
            continue

        title_key = t.casefold()
        if title_key not in seen:
            seen.add(title_key)
            cleaned.append(t)

    if not cleaned:
        cleaned = get_fallback_titles(role)

    return cleaned[:5]


_RAW_ROLE_LABEL = re.compile(
    r"(?i)^(?P<label>job\s+title|position\s+title|title|position|role)(?:"
    r"[ \t]*(?P<separator>:|：|=|\||[-–—])[ \t]*(?P<title>.*)"
    r"|[ \t]+(?P<spaced_title>.+)"
    r")?$"
)

_RAW_ROLE_BOILERPLATE = re.compile(
    r"(?ix)^(?:"
    r"job\s+description|description|about(?:\s+the\s+(?:job|role|position))?|"
    r"role\s+(?:description|overview|summary)|overview|summary|who\s+we\s+are|"
    r"key\s+responsibilities|responsibilities|duties|requirements|qualifications|"
    r"preferred\s+qualifications|what\s+you(?:'|’)?ll\s+do|what\s+you\s+will\s+do|"
    r"location|compensation|salary|pay|commitment|schedule|start\s+date|"
    r"application(?:\s+process)?|apply(?:\s+now)?|company(?:\s+overview)?|"
    r"about\s+us|terms\s+and\s+conditions|privacy\s+policy|benefits(?:\s+and\s+perks)?|"
    r"equal\s+opportunity(?:\s+employer)?|what\s+we\s+offer|"
    r"remote|hybrid|on-?site|full[ -]?time|part[ -]?time|contract"
    r")(?:\s*:\s*.*|\s*[\s.!?]*)$"
)

_RAW_ROLE_ORGANIZATION = re.compile(
    r"(?ix)(?:"
    r"\b(?:incorporated|inc|llc|ltd|limited|corporation|corp|company|group|holdings|"
    r"enterprises|foundation|university|institute|agency|studio|labs|technologies|"
    r"solutions|services)\.?$|^(?:university|institute|foundation)\s+of\b"
    r")"
)

_RAW_ROLE_NOUNLESS_HEADING = re.compile(
    r"(?ix)^(?:"
    r"ai\s+training(?:\s*[-–—:]\s*[A-Za-z][A-Za-z0-9 +#./'-]*)?|"
    r"machine\s+learning|data\s+science|customer\s+(?:success|support)|"
    r"quality\s+assurance|business\s+development|human\s+resources|"
    r"product\s+management|project\s+management|account\s+management|"
    r"sales\s+development|content\s+moderation|risk\s+management"
    r")$"
)

_RAW_ROLE_ACTION_AFTER_NOUN = re.compile(
    r"(?i)^(?:build|create|develop|evaluate|transform|review|analy[sz]e|manage|"
    r"support|work|write|test|provide|help|ensure|deliver|collaborate|conduct|"
    r"perform|use|train|assess|solve|research)(?:s|es|ed|ing)?\b"
)

_RAW_ROLE_PROSE_CONTINUATION = re.compile(
    r"(?ix)^(?:"
    r"will|would|can|could|should|must|shall|is|are|was|were|be|being|"
    r"who|that|responsible(?:\s+for)?|"
    r"(?:routinely|regularly|typically|often|primarily|usually|actively)"
    r")\b"
)

_RAW_ROLE_NOUN = re.compile(
    r"(?ix)\b(?:"
    r"accountants?|administrators?|advisers?|advisors?|agents?|analysts?|animators?|"
    r"annotators?|apprentices?|architects?|artists?|assistants?|associates?|"
    r"attorneys?|auditors?|brokers?|buyers?|chiefs?|consultants?|contributors?|"
    r"controllers?|coordinators?|copywriters?|counsel|designers?|developers?|"
    r"directors?|editors?|engineers?|evaluators?|executives?|experts?|fellows?|"
    r"founders?|heads?|illustrators?|instructors?|interpreters?|interns?|"
    r"investigators?|labelers?|labellers?|leads?|librarians?|linguists?|managers?|"
    r"marketers?|mechanics?|nurses?|officers?|operators?|owners?|paralegals?|"
    r"partners?|pharmacists?|photographers?|physicians?|planners?|practitioners?|"
    r"presidents?|principals?|producers?|professors?|recruiters?|representatives?|"
    r"researchers?|reviewers?|scientists?|specialists?|strategists?|supervisors?|"
    r"surgeons?|teachers?|technicians?|therapists?|traders?|trainers?|trainees?|"
    r"translators?|videographers?|vice\s+presidents?|vps?|writers?|"
    r"ceo|cfo|cio|cmo|coo|cpo|cto|svp|evp|avp"
    r")\b"
)


def _unwrap_raw_role_markdown(value: str) -> str:
    """Remove only simple Markdown heading/bold presentation around a title line."""
    line = str(value or "").strip()
    heading = re.fullmatch(r"#{1,6}[ \t]+(.+)", line)
    if heading:
        line = heading.group(1).strip()
    line = re.sub(r"\*\*([^*\r\n]+)\*\*", r"\1", line)
    return line.strip()


def _safe_raw_role_candidate(value: str) -> str:
    """Return a compact plain-text title candidate, or an empty string if unsafe."""
    candidate = " ".join(str(value or "").split()).strip()
    if not candidate or len(candidate) > 120 or len(candidate.split()) > 16:
        return ""
    if not any(char.isalpha() for char in candidate):
        return ""
    if any(ord(char) < 32 for char in candidate):
        return ""
    if any(token in candidate for token in ("<", ">", "{", "}", "`")):
        return ""
    if candidate.startswith(("#", "*", ">")) or "**" in candidate:
        return ""
    if re.search(r"(?i)(?:https?://|www\.|javascript\s*:|data\s*:|vbscript\s*:)", candidate):
        return ""
    if candidate.rstrip().endswith((".", "!", "?", ";")):
        return ""
    if _RAW_ROLE_LABEL.fullmatch(candidate) or _RAW_ROLE_BOILERPLATE.fullmatch(candidate):
        return ""
    return candidate


def _is_high_confidence_raw_role_heading(value: str) -> bool:
    """Recognize a title-like first heading without treating arbitrary prose as a role."""
    candidate = _safe_raw_role_candidate(value)
    if not candidate:
        return False

    # Apply the same compact eligibility cleanup used by the final role before
    # assessing its shape. The original candidate is still returned so the
    # normal normalization pipeline remains the single source of policy output.
    title_shape = normalize_role(sanitize_scalar_eligibility(candidate))
    if not title_shape or len(title_shape.split()) > 12:
        return False
    if _RAW_ROLE_BOILERPLATE.fullmatch(title_shape):
        return False
    if _RAW_ROLE_ORGANIZATION.search(title_shape):
        return False
    if title_shape.rstrip().endswith((".", "!", "?", ";")):
        return False
    if re.search(r"(?i)\b(?:we|you|our|this)\b", title_shape):
        return False
    if re.search(r"(?i)\b(?:per\s+hour|hrs?/week|hours?/week)\b|[$€£]", title_shape):
        return False

    noun_match = _RAW_ROLE_NOUN.search(title_shape)
    if noun_match:
        following_text = title_shape[noun_match.end():].lstrip(" ,:;-–—")
        if following_text and (
            _RAW_ROLE_ACTION_AFTER_NOUN.match(following_text)
            or _RAW_ROLE_PROSE_CONTINUATION.match(following_text)
        ):
            return False
        return True

    return bool(_RAW_ROLE_NOUNLESS_HEADING.fullmatch(title_shape))


def extract_raw_role(raw_jd: str) -> str:
    """Extract the source title while rejecting markup, URLs, metadata, and prose."""
    lines = [
        _unwrap_raw_role_markdown(line)
        for line in str(raw_jd or "").splitlines()[:20]
    ]

    # Explicit labels are authoritative. Support both inline values and the
    # common two-line layout where the label is followed by the title.
    # Search authoritative title labels before the more ambiguous Role/Position
    # headings so nearby prose cannot win over a later explicit Job Title.
    for authoritative_pass in (True, False):
        for index, line in enumerate(lines):
            if not line:
                continue
            match = _RAW_ROLE_LABEL.fullmatch(line)
            if not match:
                continue
            label = " ".join(match.group("label").casefold().split())
            authoritative_label = label in {"job title", "position title", "title"}
            if authoritative_label != authoritative_pass:
                continue
            inline_title = _safe_raw_role_candidate(
                match.group("title") or match.group("spaced_title") or ""
            )
            if inline_title and (
                authoritative_label or _is_high_confidence_raw_role_heading(inline_title)
            ):
                return inline_title
            for following_line in lines[index + 1:]:
                if not following_line:
                    continue
                next_title = _safe_raw_role_candidate(following_line)
                if next_title and (
                    authoritative_label or _is_high_confidence_raw_role_heading(next_title)
                ):
                    return next_title
                break

    # Many source JDs, including Mercor exports, use the role as the first
    # unlabelled heading. Accept it only when it has a strong title shape.
    first_line = next((line for line in lines if line), "")
    first_title = _safe_raw_role_candidate(first_line)
    if first_title and _is_high_confidence_raw_role_heading(first_title):
        return first_title
    return ""

def extract_pay_info(pay_str: str):
    if not pay_str:
        return 0.0, "", ""

    pay_str_lower = str(pay_str).lower()
    unit = ""
    if "hour" in pay_str_lower or "/hr" in pay_str_lower:
        unit = "/hr"
    elif "month" in pay_str_lower or "/mo" in pay_str_lower:
        unit = "/month"
    elif "year" in pay_str_lower or "annu" in pay_str_lower or "/yr" in pay_str_lower:
        unit = "/year"
    elif "week" in pay_str_lower or "/wk" in pay_str_lower:
        unit = "/week"

    matches = re.findall(r'\d+(?:\.\d+)?(?:[kKmM])?', str(pay_str).replace(',', ''))
    max_numeric = 0.0
    formatted_max = ""
    for m in matches:
        num_str = m.upper().replace('K', '').replace('M', '')
        try:
            val = float(num_str)
            numeric_val = val
            if 'K' in m.upper(): numeric_val *= 1000
            if 'M' in m.upper(): numeric_val *= 1000000

            if numeric_val > max_numeric:
                max_numeric = numeric_val
                if 'K' in m.upper():
                    formatted_max = str(int(val)) + "K" if val.is_integer() else str(val) + "K"
                elif 'M' in m.upper():
                    formatted_max = str(int(val)) + "M" if val.is_integer() else str(val) + "M"
                else:
                    formatted_max = str(int(val)) if val.is_integer() else str(val)
        except Exception:
            pass

    return max_numeric, formatted_max, unit

def generate_subject(role: str, formatted_max: str, unit: str, is_remote: bool, client_id: str) -> str:
    config = get_client_config(client_id)
    suffix = config["subjectSuffix"]
    middle_parts = []
    if formatted_max:
        middle_parts.append(f"${formatted_max}{unit}")
    if is_remote:
        middle_parts.append("Remote")
    middle = " ".join(middle_parts)
    if middle:
        return f"{role} | {middle} | {suffix}"
    return f"{role} | {suffix}"

def generate_linkedin_title(role: str, numeric_max: float, formatted_max: str, unit: str, is_remote: bool) -> str:
    middle_parts = []
    if numeric_max > 0 and numeric_max <= 99:
        middle_parts.append(f"${formatted_max}{unit}")
    if is_remote:
        middle_parts.append("Remote")
    middle = " ".join(middle_parts)
    if middle:
        return f"{role} | {middle}"
    return role


# ── 4. Schema Validation ──────────────────────────────────────────────────────

def validate_raw_schema(data: Any) -> Tuple[bool, str]:
    """Validate model-produced types before any normalizer can coerce them."""
    if not isinstance(data, dict):
        return False, "LLM output must be a JSON object"

    string_fields = {
        "role", "type", "pay", "location", "commitment", "role_overview",
        "who_this_is_for", "where_you_will", "client", "client_desc", "link",
        "subject", "linkedin_title", "start_date",
    }
    list_fields = {
        "role_responsibilities", "requirements", "preferred_qualifications",
        "suggested_titles", "skills", "job_functions", "industries",
    }

    for key in string_fields:
        if key in data and not isinstance(data[key], str):
            return False, f"{key} must be a string"
    for key in list_fields:
        if key not in data:
            continue
        if not isinstance(data[key], list):
            return False, f"{key} must be a list"
        if not all(isinstance(item, str) for item in data[key]):
            return False, f"{key} must contain only strings"
    if "justifications" in data and not isinstance(data["justifications"], dict):
        return False, "justifications must be an object"
    return True, ""


def validate_schema(data: dict) -> Tuple[bool, Any]:
    required_keys = [
        "role", "type", "pay", "location", "commitment",
        "role_responsibilities", "requirements", "role_overview",
        "who_this_is_for", "client", "client_desc", "link", "suggested_titles"
    ]
    for k in required_keys:
        if k not in data:
            return False, f"Missing key: {k}"

    if not isinstance(data["role_responsibilities"], list): return False, "role_responsibilities must be a list"
    if not isinstance(data["requirements"], list): return False, "requirements must be a list"
    if not all(isinstance(item, str) for item in data["role_responsibilities"]):
        return False, "role_responsibilities must contain only strings"
    if not all(isinstance(item, str) for item in data["requirements"]):
        return False, "requirements must contain only strings"

    string_keys = ["role", "type", "pay", "location", "commitment", "role_overview", "who_this_is_for", "client", "client_desc", "link"]
    for k in string_keys:
        if not isinstance(data[k], str):
            return False, f"{k} must be a string"

    if not isinstance(data.get("suggested_titles"), list):
        return False, "suggested_titles must be a list"
    if not all(isinstance(item, str) for item in data["suggested_titles"]):
        return False, "suggested_titles must contain only strings"
    if not isinstance(data.get("justifications", {}), dict):
        return False, "justifications must be an object"

    return True, data


# ── 5. Classification Refinement with Higher Model ────────────────────────────

def refine_classifications_with_higher_model(raw_jd: str, client_id: str) -> dict:
    """Uses a higher reasoning model (o3-mini) to generate high-quality suggested titles,
    skills, job functions, industries, and specific, helpful justifications."""
    config = get_client_config(client_id)
    
    prompt = f"""
You are an expert recruitment classifier and taxonomist.
Your task is to analyze the job description below and extract/generate the following structured fields:

1. "suggested_titles": Exactly 5 market-standard job titles ranked from best to worst.
   Rules for suggested titles:
   - Must be market-standard job titles that candidates use on LinkedIn.
   - Do NOT include ID numbers, bracketed annotations, or task-based descriptors (e.g. do NOT include "ID: 12345", "(Task based)", or any brackets/parenthesis contents).
   - 3-6 words preferred, max 8 words.
   - Do NOT use inflated titles (avoid "Expert" unless required).
   
2. "skills": Exactly 4-5 target skills.
   Rules for skills:
   - Must be broad, searchable, industry-standard technical skills or frameworks.
   - Each skill must be 1-3 words.
   - NO soft skills (e.g., communication, teamwork, problem solving).
   - NO verbs or verb phrases.
   - Do NOT repeat the role title.
   
3. "job_functions": Exactly 3 job functions selected VERBATIM from this list:
   {", ".join(VALID_JOB_FUNCTIONS)}
   
4. "industries": Exactly 3 industries selected VERBATIM from this list:
   {", ".join(VALID_INDUSTRIES)}
   
5. "justifications": A JSON dictionary mapping EACH item in suggested_titles, skills, job_functions, and industries to a highly specific, professional, and helpful 1-line justification (max 20 words).
   - The justification MUST refer to specific requirements, tools, tasks, or background from the job description.
   - DO NOT use generic filler like "matches the title", "relevant industry", "required for the role", "needed for responsibilities", or "fits the category".
   - Example of a GOOD justification: "Python": "Needed to develop training pipelines and integrate ML tools as described in key duties."

CRITICAL DEADLINE EXCLUSION: Do NOT include any deadlines, dates, or turnaround time limits anywhere in suggested_titles, skills, job_functions, industries, or justifications.

Output strictly in JSON format matching this schema:
{{
  "suggested_titles": [],
  "skills": [],
  "job_functions": [],
  "industries": [],
  "justifications": {{}}
}}

Job Description:
{raw_jd}
"""

    try:
        # o3-mini supports JSON mode via response_format={"type": "json_object"}
        response = _get_openai_client().chat.completions.create(
            model="o3-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"[ERROR] Failed calling o3-mini for classifications: {e}")
        return None


# ── 6. Main wrapper ───────────────────────────────────────────────────────────

def get_valid_llm_output(raw_jd: str, url: str = None, client: str = "mercor") -> dict:
    # Normalise to lowercase registry key
    client_id = client.strip().lower()

    # Validate client is supported — fail fast with a clear message
    if client_id not in SUPPORTED_CLIENTS:
        raise ValueError(
            f"Unsupported client '{client}'. Supported clients: {SUPPORTED_CLIENTS}"
        )

    config = get_client_config(client_id)
    formatter = get_formatter(client_id)

    for attempt in range(3):
        start_time = time.time()
        raw_resp = generate_llm_output(raw_jd, client_name=client_id)
        print(f"[LLM TIME] {time.time() - start_time:.2f}s")

        try:
            clean_text = raw_resp.strip()
            if clean_text.startswith("```json"): clean_text = clean_text[7:]
            if clean_text.startswith("```"): clean_text = clean_text[3:]
            if clean_text.endswith("```"): clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            data = json.loads(clean_text)
        except json.JSONDecodeError:
            print(f"[!] Invalid JSON on attempt {attempt+1}")
            continue

        raw_is_valid, raw_error = validate_raw_schema(data)
        if not raw_is_valid:
            print(f"[!] Invalid schema on attempt {attempt+1}: {raw_error}")
            continue

        # NORMALIZE ONLY AFTER RAW TYPES ARE VALIDATED
        raw_role = extract_raw_role(raw_jd)
        if raw_role:
            data["role"] = raw_role

        data = normalize_data(data, client_id)

        # Call higher model to refine classifications and justifications
        refinement = refine_classifications_with_higher_model(raw_jd, client_id)
        if isinstance(refinement, dict):
            print("[LLM] Successfully refined classifications and justifications using higher model (o3-mini)")
            for field in ("suggested_titles", "skills", "job_functions", "industries"):
                value = refinement.get(field)
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    data[field] = value
            if isinstance(refinement.get("justifications"), dict):
                data["justifications"] = refinement["justifications"]
        else:
            print("[LLM] Fallback: using initial classifications and justifications")

        # VALIDATE STRICTLY ON STRUCTURE ONLY
        is_valid, msg_or_data = validate_schema(data)
        if is_valid:
            result = msg_or_data

            # Output location is intentionally standardized for every client.
            is_remote = True
            result["location"] = "Remote"
            result["role_overview"] = remove_geography_sentences(result.get("role_overview", ""))
            result["who_this_is_for"] = remove_geography_sentences(result.get("who_this_is_for", ""))
            result["role_overview"] = remove_inline_geography(result.get("role_overview", ""))
            result["who_this_is_for"] = remove_inline_geography(result.get("who_this_is_for", ""))

            result["suggested_titles"] = clean_titles(result.get("suggested_titles", []), result.get("role", ""))

            # Ensure client_desc is always populated from config
            if not result.get("client_desc"):
                result["client_desc"] = config["description"]

            assert isinstance(result["role_responsibilities"], list)
            assert isinstance(result["requirements"], list)

            # Guard: ensure client is in the registry (replaces old hardcoded assert)
            assert client_id in SUPPORTED_CLIENTS, f"Unexpected client: {client_id}"

            if url:
                result["link"] = sanitize_http_url(url)

            # Use the registry formatter — no more if/else branching
            jd_output = formatter.format_jd(result)
            email_output = formatter.format_email(result)

            if client_id in DOMAIN_PAGE_KEYS:
                jd_output = scrub_all_client_orgs_from_jd(jd_output)

            skills = result.get("skills", [])
            if not isinstance(skills, list):
                skills = []
            skills = clean_skills([s.strip() for s in skills if isinstance(s, str) and s.strip()], result.get("role", ""))

            max_numeric, formatted_max, unit = extract_pay_info(result.get("pay", ""))
            subject = generate_subject(result["role"], formatted_max, unit, is_remote, client_id)
            linkedin_title = generate_linkedin_title(result["role"], max_numeric, formatted_max, unit, is_remote)

            job_functions = clean_category_list(result.get("job_functions", []), VALID_JOB_FUNCTIONS)
            industries = clean_category_list(result.get("industries", []), VALID_INDUSTRIES)

            # Build final justifications dictionary mapping post-processed keys case-insensitively
            final_justifications = {}
            raw_justifications = result.get("justifications", {})

            def get_justification(item_str: str) -> str:
                item_lower = item_str.lower().strip()
                if item_str in raw_justifications:
                    return raw_justifications[item_str]
                for k, v in raw_justifications.items():
                    if isinstance(k, str) and k.lower().strip() == item_lower:
                        return v
                return ""

            for t in result["suggested_titles"]:
                j = get_justification(t)
                if j:
                    final_justifications[t] = j
            for s in skills:
                j = get_justification(s)
                if j:
                    final_justifications[s] = j
            for jf in job_functions:
                j = get_justification(jf)
                if j:
                    final_justifications[jf] = j
            for ind in industries:
                j = get_justification(ind)
                if j:
                    final_justifications[ind] = j

            print("Final role:", result["role"])
            print("Subject:", subject)
            print("LinkedIn:", linkedin_title)

            is_dp = client_id in DOMAIN_PAGE_KEYS
            return {
                "jd": jd_output,
                "email": email_output if not is_dp else "",
                "inmail_draft": email_output if is_dp else None,
                "email_draft": None if is_dp else email_output,
                "subject": subject,
                "linkedin_title": linkedin_title,
                "skills": skills,
                "job_functions": job_functions,
                "industries": industries,
                "version": OUTPUT_VERSION,
                "titles": result["suggested_titles"],
                "structured_data": result,
                "justifications": final_justifications,
                "is_domain_page": is_dp
            }

        else:
            print(f"[!] Validation failed on attempt {attempt+1}: {msg_or_data}")

    raise ValueError("Failed to get valid structured output from LLM after 3 attempts.")



# ── 6. Test block ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample_jd = """
Audio and Video Technicians
Part-time position
Remote
Recent hire 1Recent hire 2Recent hire 3
41 hired this month

$500-$1K
one-time
Mercor logo
Posted by Mercor
mercor.com

About the Role
Mercor is seeking experienced audio and video technicians to support a leading AI lab in advancing research and infrastructure for next-generation machine learning systems. This engagement focuses on diagnosing and solving real issues in your domain. It's an opportunity to contribute your expertise to cutting-edge AI research while working independently and remotely on your own schedule.

Key Responsibilities
You'll be asked to create deliverables regarding common requests regarding your professional domain

You'll be asked to review peer developed deliverables to improve AI research

Ideal Qualifications
4+ years professional experience in your respective domain

Excellent written communication with strong grammar and spelling skills

More About the Opportunity
Start Date: Immediate

Duration: ~2 weeks (with the potential for project expansion)

Commitment: ~15 hours/week required

Compensation & Contract
Task Completion Pay: Payment is based on a task completion and task quality (~$500 - $1000 per completed task, subject to change as the project evolves)

Performance Bonus: Top performers receive a weekly bonus incentive on top of their per task rate!

We consider all qualified applicants without regard to legally protected characteristics and provide reasonable accommodations upon request.
link - https://work.mercor.com/explore?listingId=list_AAABnSLJvfVX3RBDlENFN7tC
    """

    for test_client in ["mercor", "micro1", "turing"]:
        print(f"\n\n{'='*60}")
        print(f"--- Running Test: client={test_client} ---")
        print('='*60)
        try:
            res = get_valid_llm_output(sample_jd, client=test_client)

            print("\n=== RENDERED JD ===")
            print(res["jd"])

            print("\n=== SUBJECT ===")
            print(res["subject"])

            print("\n=== SUGGESTED TITLES ===")
            print(json.dumps(res["titles"], indent=2))

            print("\n=== JUSTIFICATIONS ===")
            print(json.dumps(res["justifications"], indent=2))

        except Exception as e:
            print(f"Error during test [{test_client}]: {e}")
