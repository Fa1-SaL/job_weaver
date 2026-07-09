"""
History and caching utility for Job Weaver.
Stores generated JD/InMail results in memory and persists them to JSON on disk.
When identical raw_jd + client + url are requested, returns the cached result instantly.
Also provides history endpoints for the UI drawer/modal.
"""

import json
import hashlib
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

CACHE_DIR = Path(__file__).resolve().parent / "cache_data"
CACHE_FILE = CACHE_DIR / "history.json"

_HISTORY: List[Dict[str, Any]] = []


def _load_history():
    global _HISTORY
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _HISTORY = json.load(f)
        else:
            _HISTORY = []
    except Exception as e:
        print("Error loading history file:", e)
        _HISTORY = []


def _save_history():
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        # Save up to latest 100 entries
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_HISTORY[:100], f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Error saving history file:", e)


# Load initially
_load_history()


def _compute_key(raw_jd: str, client: str, url: Optional[str]) -> str:
    raw_norm = clean_text_for_hash(raw_jd)
    client_norm = (client or "mercor").strip().lower()
    url_norm = (url or "").strip().lower()
    payload = f"{raw_norm}|{client_norm}|{url_norm}"
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def clean_text_for_hash(text: str) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join([l for l in lines if l]).lower()


def _ensure_classifications(data: Optional[Dict[str, Any]], role_hint: str = "") -> Optional[Dict[str, Any]]:
    if not isinstance(data, dict):
        return data
    role = role_hint
    if not role:
        if isinstance(data.get("structured_data"), dict):
            role = data["structured_data"].get("role", "")
        if not role and data.get("subject"):
            role = str(data["subject"]).split("|")[0].strip()
    if not role:
        role = "Role"

    if not data.get("titles") or not isinstance(data.get("titles"), list) or len(data.get("titles", [])) == 0:
        data["titles"] = [
            f"{role} (Research & Reporting)",
            "Content Analyst (Media & Insights)",
            "Reporting Specialist (Analysis & Review)",
            "Media Reviewer (Content & Accuracy)",
            "Editorial Analyst (Research & Quality)"
        ]
    if not data.get("job_functions") or not isinstance(data.get("job_functions"), list) or len(data.get("job_functions", [])) == 0:
        data["job_functions"] = ["Writing/Editing", "Analytics", "Project Management"]
    if not data.get("industries") or not isinstance(data.get("industries"), list) or len(data.get("industries", [])) == 0:
        data["industries"] = ["Technology, Information and Media", "Professional Services", "Education"]
    if not data.get("skills") or not isinstance(data.get("skills"), list) or len(data.get("skills", [])) == 0:
        data["skills"] = ["Data Evaluation", "Quality Assurance", "Content Analysis"]
    return data


def get_cached_item(raw_jd: str, client: str, url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Check if we already generated a result for this input string and client."""
    key = _compute_key(raw_jd, client, url)
    for item in _HISTORY:
        if item.get("cache_key") == key:
            data = item.get("data")
            return _ensure_classifications(data, item.get("role", ""))
    return None


def add_item(raw_jd: str, client: str, url: Optional[str], data: Dict[str, Any]) -> Dict[str, Any]:
    """Add a newly generated result to history and save to disk."""
    key = _compute_key(raw_jd, client, url)
    
    # Extract a friendly role title
    role = "Untitled Job"
    if isinstance(data, dict):
        if data.get("structured_data") and isinstance(data["structured_data"], dict):
            role = data["structured_data"].get("role", role)
        elif data.get("subject"):
            role = data["subject"].split("|")[0].strip()
            
    snippet = raw_jd.strip()[:150] + ("..." if len(raw_jd.strip()) > 150 else "")
    data = _ensure_classifications(data, role)
    
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "client": client,
        "url": url or "",
        "raw_jd": raw_jd,
        "role": role,
        "raw_jd_snippet": snippet,
        "cache_key": key,
        "data": data
    }
    
    # Remove any existing duplicate cache_key entry so the latest pops to top
    global _HISTORY
    _HISTORY = [item for item in _HISTORY if item.get("cache_key") != key]
    _HISTORY.insert(0, entry)
    _save_history()
    return entry


def get_history_list() -> List[Dict[str, Any]]:
    """Return lightweight summary list for the frontend modal/sidebar."""
    return [
        {
            "id": item["id"],
            "timestamp": item["timestamp"],
            "client": item["client"],
            "url": item.get("url", ""),
            "role": item.get("role", "Untitled Job"),
            "raw_jd_snippet": item.get("raw_jd_snippet", ""),
        }
        for item in _HISTORY
    ]


def get_history_detail(item_id: str) -> Optional[Dict[str, Any]]:
    """Return full data payload for a specific history item ID including input metadata."""
    for item in _HISTORY:
        if item["id"] == item_id:
            data = dict(item["data"]) if isinstance(item["data"], dict) else {}
            data = _ensure_classifications(data, item.get("role", ""))
            data["_id"] = item["id"]
            data["_timestamp"] = item["timestamp"]
            data["_client"] = item["client"]
            data["_url"] = item.get("url", "")
            data["_raw_jd_snippet"] = item.get("raw_jd_snippet", "")
            if "raw_jd" in item:
                data["_raw_jd"] = item["raw_jd"]
            return data
    return None


def delete_history_item(item_id: str) -> bool:
    global _HISTORY
    initial_len = len(_HISTORY)
    _HISTORY = [item for item in _HISTORY if item["id"] != item_id]
    if len(_HISTORY) != initial_len:
        _save_history()
        return True
    return False


def clear_history() -> None:
    global _HISTORY
    _HISTORY = []
    _save_history()
