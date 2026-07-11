import os
import json
import re
import time
from pathlib import Path
from typing import Tuple, Any, Dict, List
from openai import OpenAI
from dotenv import load_dotenv

# ── Registry imports ─────────────────────────────────────────────────────────
from clients import get_client_config, CLIENT_REGISTRY, SUPPORTED_CLIENTS, DOMAIN_PAGE_KEYS
from formatters import get_formatter
from prompts import get_prompt

# Explicitly load .env from the project root (one level above this file's backend/ folder)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in environment variables.")

_openai_client = OpenAI(api_key=api_key)

# ── Output schema ─────────────────────────────────────────────────────────────
OUTPUT_SCHEMA = {
    "role": "",
    "type": "",
    "pay": "",
    "location": "",
    "commitment": "",
    "role_responsibilities": [],
    "requirements": [],
    "role_overview": "",
    "who_this_is_for": "",
    "where_you_will": "",
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

    _t0 = time.time()
    response = _openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You output strict JSON only. Do not wrap in formatting blocks. CRITICAL INSTRUCTION: Remove any sort of date, turnaround deadline, or completion time limit if mentioned in the JD (for example, 'Your turnaround time will be 3 hours of conversation that needs to be filled before 12/28'). The output must not hint anything regarding deadlines, turnaround windows, or completion dates while keeping all other details covered exactly."},
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
    """Validates items against valid_list (exact match). Falls back to keyword overlap if < 3 match, and defaults if still < 3."""
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

    # Failsafe 2: if still < 3 (e.g. empty input or no keyword match), fill from valid_list
    if len(cleaned) < 3:
        for v in valid_list:
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
    for s in skills:
        s = str(s).strip()
        if not s:
            continue
        if len(s.split()) > 3:
            continue
        s_lower = s.lower()
        if any(s_lower.startswith(p) for p in _SKILL_VERB_PREFIXES):
            continue
        if s_lower == role_lower:
            continue
        cleaned.append(s)
    if not cleaned:
        cleaned = ["Data Evaluation", "Quality Assurance", "Content Analysis"]
    return cleaned[:5]

def normalize_commitment(commitment: str) -> str:
    if not commitment:
        return ""
    return "10-40 hrs/week"

def clean_experience_phrases(text: str) -> str:
    if not text:
        return text
    text = re.sub(r'\b\d+\+?\s*(years?|yrs?)\b', '', text, flags=re.IGNORECASE)
    text = " ".join(text.split())
    return text.strip()

def normalize_role(role: str) -> str:
    if not role:
        return ""
    # Remove any ID patterns (e.g. "ID: 12345", "ID-12345", "ID 12345") case-insensitively
    role = re.sub(r'(?i)\bID\s*[:-]?\s*\d+\b', '', role)
    # Remove bracketed and parenthesized expressions (like [Task-based], (Remote), etc.)
    role = re.sub(r'\[[^\]]*\]', '', role)
    role = re.sub(r'\([^)]*\)', '', role)
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
    blocked_pattern = re.compile(r'\b(us|uk|canada|europe|western|h1-b|h1b|visa|opt|citizenship)\b', re.IGNORECASE)
    deadline_pattern = re.compile(
        r'(?i)\b(before \d{1,2}/\d{1,2}|turnaround time|to be filled before|filled before|deadline|complete before|submit by|apply by|\d{1,2}(?:st|nd|rd|th)?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december))\b'
    )

    for r in requirements:
        if blocked_pattern.search(r) or deadline_pattern.search(r):
            continue
        filtered.append(r)

    if len(filtered) < 2:
        fallback = "Candidates should have strong relevant experience in the domain."
        if fallback not in filtered:
            filtered.append(fallback)

    return filtered

def filter_responsibilities(responsibilities: List[str]) -> List[str]:
    filtered = []
    blocked_patterns = ["based in", "located in", "native to"]
    deadline_pattern = re.compile(
        r'(?i)\b(before \d{1,2}/\d{1,2}|turnaround time|to be filled before|filled before|deadline|complete before|submit by|apply by|\d{1,2}(?:st|nd|rd|th)?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december))\b'
    )
    for r in responsibilities:
        r_lower = r.lower()
        if any(p in r_lower for p in blocked_patterns) or deadline_pattern.search(r):
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
    match = re.match(r'\$0\s*-\s*\$?(\d+)', pay)

    if match:
        max_val = match.group(1)
        if "hour" in pay.lower():
            return f"Upto ${max_val} per hour"
        elif "month" in pay.lower():
            return f"Upto ${max_val} per month"
        else:
            return f"Upto ${max_val}"

    return pay

def normalize_data(data: dict, client_id: str) -> dict:
    config = get_client_config(client_id)

    # Always normalise client to the registry display name
    data["client"] = config["displayName"]
    data["client_desc"] = config["description"]

    data["pay"] = normalize_compensation(data.get("pay", ""))
    data["commitment"] = normalize_commitment(data.get("commitment", ""))
    data["role"] = normalize_role(data.get("role", ""))

    reqs = normalize_requirements(data.get("requirements", []))
    data["requirements"] = filter_requirements(reqs)

    who_for = clean_experience_phrases(data.get("who_this_is_for", ""))
    data["who_this_is_for"] = normalize_text_block(who_for)

    if len(data["who_this_is_for"].split()) < 10:
        data["who_this_is_for"] = (
            "Professionals with strong experience in content editing, proofreading, or "
            "language-focused roles who are comfortable working with structured evaluation "
            "tasks and maintaining high-quality standards."
        )

    where_will = data.get("where_you_will", "").strip()
    if where_will:
        where_will = " ".join(where_will.split())
        if len(where_will) > 0:
            where_will = where_will[0].lower() + where_will[1:]
    else:
        where_will = "contribute to training advanced AI models and ensuring high-quality system integration"
    data["where_you_will"] = where_will
    
    data["justifications"] = data.get("justifications", {})
    if not isinstance(data["justifications"], dict):
        data["justifications"] = {}

    if "role_overview" in data and isinstance(data["role_overview"], str):
        data["role_overview"] = strip_deadlines_and_dates(data["role_overview"])
    if "commitment" in data and isinstance(data["commitment"], str):
        data["commitment"] = strip_deadlines_and_dates(data["commitment"])
    if "who_this_is_for" in data and isinstance(data["who_this_is_for"], str):
        data["who_this_is_for"] = strip_deadlines_and_dates(data["who_this_is_for"])

    data["role_overview"] = normalize_text_block(data.get("role_overview", ""))

    unique_resps = []
    for resp in data.get("role_responsibilities", []):
        r_fmt = format_bullet(resp)
        if r_fmt and r_fmt not in unique_resps:
            unique_resps.append(r_fmt)
    data["role_responsibilities"] = filter_responsibilities(unique_resps)

    data["requirements"] = [clean_requirement_text(clean_text_artifacts(r)) for r in data["requirements"]]
    data["role_responsibilities"] = [clean_text_artifacts(r) for r in data["role_responsibilities"]]

    if len(data["role_responsibilities"]) < 2:
        data["role_responsibilities"] = [
            "Perform tasks relevant to the role with high accuracy",
            "Follow guidelines to ensure consistent output quality"
        ]

    if len(data["requirements"]) < 2:
        data["requirements"] = [
            "Candidates should have strong relevant experience in the domain.",
            "Strong communication and analytical skills"
        ]

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
    patterns = [
        r'(?i)\bbased in\b',
        r'(?i)\blocated in\b',
        r'(?i)\bnative to\b',
        r'(?i)\bmust be in\b',
        r'(?i)\bonly candidates from\b'
    ]
    return any(re.search(p, sentence) for p in patterns)

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
    if not text:
        return text

    geo_terms = [
        "us", "uk", "canada", "spain", "mexico", "chile",
        "europe", "western", "germany", "france"
    ]

    words = text.split()
    cleaned_words = []

    for w in words:
        word_clean = w.lower().strip(",.")
        if word_clean in geo_terms:
            continue
        cleaned_words.append(w)

    return " ".join(cleaned_words)

def remove_geography_sentences(text: str) -> str:
    if not text:
        return text

    sentences = re.split(r'(?<=[.!?])\s+', text)
    cleaned = []

    for sentence in sentences:
        if is_geography_sentence(sentence):
            continue
        cleaned.append(sentence.strip())

    result = " ".join(cleaned).strip()
    result = re.sub(r'\s+,', ',', result)
    result = re.sub(r',\s*,', ',', result)
    result = re.sub(r'\s+', ' ', result)

    return result

def get_fallback_titles(role: str) -> List[str]:
    return [
        f"{role} (Research & Reporting)",
        "Content Analyst (Media & Insights)",
        "Reporting Specialist (Analysis & Review)",
        "Media Reviewer (Content & Accuracy)",
        "Editorial Analyst (Research & Quality)"
    ]

def clean_titles(titles: List[str], role: str) -> List[str]:
    cleaned = []
    role_lower = role.lower()

    for t in titles:
        t_lower = t.lower()

        if len(t.split()) > 10:
            continue

        if any(bad in t_lower for bad in ["expert", "generalist"]):
            continue

        if "ai" in t_lower and "ai" not in role_lower:
            continue

        if t not in cleaned:
            cleaned.append(t)

    if len(cleaned) < 3:
        cleaned = get_fallback_titles(role)

    return cleaned[:5]


def extract_raw_role(raw_jd: str) -> str:
    for line in raw_jd.split('\n'):
        line = line.strip()
        if line:
            return line
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

    string_keys = ["role", "type", "pay", "location", "commitment", "role_overview", "who_this_is_for", "client", "client_desc", "link"]
    for k in string_keys:
        if not isinstance(data[k], str):
            return False, f"{k} must be a string"

    if not isinstance(data.get("suggested_titles"), list):
        return False, "suggested_titles must be a list"

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
        response = _openai_client.chat.completions.create(
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

            if attempt == 2:
                fallback_titles = get_fallback_titles("Role")
                fallback_data = {
                    "role": "Role not parsed",
                    "type": "",
                    "pay": "",
                    "location": "Remote",
                    "commitment": "",
                    "role_responsibilities": [
                        "Unable to extract responsibilities from input",
                        "Please review the original job description"
                    ],
                    "requirements": [
                        "Candidates should have strong relevant experience in the domain.",
                        "Strong communication and analytical skills"
                    ],
                    "role_overview": "Unable to generate overview due to parsing failure.",
                    "who_this_is_for": "Unable to determine target candidate profile.",
                    "where_you_will": "",
                    "client": config["displayName"],
                    "client_desc": config["description"],
                    "link": url if url else "",
                    "suggested_titles": fallback_titles,
                    "subject": "",
                    "linkedin_title": "",
                    "skills": ["Data Evaluation", "Quality Assurance", "Content Analysis"],
                    "job_functions": ["Writing/Editing", "Analytics", "Project Management"],
                    "industries": ["Technology, Information and Media", "Professional Services", "Education"],
                    "justifications": {}
                }

                jd_output = formatter.format_jd(fallback_data)
                email_output = formatter.format_email(fallback_data)

                print("Final role:", fallback_data["role"])
                print("Subject:", fallback_data["subject"])
                print("LinkedIn:", fallback_data["linkedin_title"])

                if client_id == "turing":
                    print("[TURING DEBUG] Formatter Output (email_output):", email_output)
                    print("[TURING DEBUG] AI Raw Output (raw_resp):", raw_resp)
                    print("[TURING DEBUG] Final Response Payload (email):", email_output)

                is_dp = client_id in DOMAIN_PAGE_KEYS
                return {
                    "jd": jd_output,
                    "email": email_output if not is_dp else "",
                    "inmail_draft": email_output if is_dp else None,
                    "email_draft": None if is_dp else email_output,
                    "subject": fallback_data["subject"],
                    "linkedin_title": fallback_data["linkedin_title"],
                    "skills": fallback_data["skills"],
                    "job_functions": fallback_data["job_functions"],
                    "industries": fallback_data["industries"],
                    "version": "v2",
                    "titles": fallback_titles,
                    "structured_data": fallback_data,
                    "justifications": {},
                    "is_domain_page": is_dp
                }

            continue

        # NORMALIZE BEFORE VALIDATION
        raw_role = extract_raw_role(raw_jd)
        if raw_role:
            data["role"] = raw_role

        data = normalize_data(data, client_id)

        # Call higher model to refine classifications and justifications
        refinement = refine_classifications_with_higher_model(raw_jd, client_id)
        if refinement:
            print("[LLM] Successfully refined classifications and justifications using higher model (o3-mini)")
            if refinement.get("suggested_titles"):
                data["suggested_titles"] = refinement["suggested_titles"]
            if refinement.get("skills"):
                data["skills"] = refinement["skills"]
            if refinement.get("job_functions"):
                data["job_functions"] = refinement["job_functions"]
            if refinement.get("industries"):
                data["industries"] = refinement["industries"]
            if refinement.get("justifications"):
                data["justifications"] = refinement["justifications"]
        else:
            print("[LLM] Fallback: using initial classifications and justifications")

        # VALIDATE STRICTLY ON STRUCTURE ONLY
        is_valid, msg_or_data = validate_schema(data)
        if is_valid:
            result = msg_or_data

            # Policy Enforcement
            is_remote = is_remote_role(result)
            
            # Detect location from first 10 non-empty lines of the input JD
            first_lines = [line.strip().lower() for line in raw_jd.split('\n') if line.strip()][:10]
            detected_loc = None
            for line in first_lines:
                if "remote" in line:
                    detected_loc = "Remote"
                    break
                elif "hybrid" in line:
                    detected_loc = "Hybrid"
                    break
                elif "on-site" in line or "onsite" in line:
                    detected_loc = "Onsite"
                    break
            
            if detected_loc:
                if detected_loc == "Remote":
                    is_remote = True
                    result["location"] = "Remote"
                else:
                    is_remote = False
                    result["location"] = detected_loc
            elif client_id == "turing":
                loc_lower = result.get("location", "").lower()
                if "onsite" in loc_lower or "on-site" in loc_lower or "hybrid" in loc_lower:
                    is_remote = False
                else:
                    is_remote = True
                    result["location"] = "Remote"
            elif is_remote:
                result["location"] = "Remote"

            if is_remote:
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
            assert len(result["role_responsibilities"]) >= 2
            assert len(result["requirements"]) >= 2

            # Guard: ensure client is in the registry (replaces old hardcoded assert)
            assert client_id in SUPPORTED_CLIENTS, f"Unexpected client: {client_id}"

            if url:
                result["link"] = url

            # Use the registry formatter — no more if/else branching
            jd_output = formatter.format_jd(result)
            email_output = formatter.format_email(result)

            skills = result.get("skills", [])
            if not isinstance(skills, list):
                skills = []
            skills = clean_skills([str(s).strip() for s in skills if str(s).strip()], result.get("role", ""))

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
                    if k.lower().strip() == item_lower:
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

            if client_id == "turing":
                print("[TURING DEBUG] Formatter Output (email_output):", email_output)
                print("[TURING DEBUG] AI Raw Output (raw_resp):", raw_resp)
                print("[TURING DEBUG] Final Response Payload (email):", email_output)

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
                "version": "v2",
                "titles": result["suggested_titles"],
                "structured_data": result,
                "justifications": final_justifications,
                "is_domain_page": is_dp
            }

        else:
            print(f"[!] Validation failed on attempt {attempt+1}: {msg_or_data}")

    raise ValueError("Failed to get valid JSON from LLM after 3 attempts.")



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

