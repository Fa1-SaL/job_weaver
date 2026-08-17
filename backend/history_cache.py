"""Process-safe history and cache storage for Job Weaver.

History is stored in SQLite rather than a process-local list plus JSON file. A
short-lived connection is used for every operation so multiple Uvicorn workers
see the same state. SQLite transactions provide atomic updates, while a
per-cache-key filesystem lock prevents duplicate LLM calls across workers.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, Iterator, List, Mapping, Optional
from urllib.parse import urlsplit, urlunsplit
import uuid


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return max(minimum, min(value, maximum))


_DEFAULT_CACHE_DIR = Path(__file__).resolve().parent / "cache_data"
CACHE_DIR = Path(os.getenv("JOB_WEAVER_CACHE_DIR", str(_DEFAULT_CACHE_DIR))).resolve()
HISTORY_DB = Path(
    os.getenv("JOB_WEAVER_HISTORY_DB", str(CACHE_DIR / "history.sqlite3"))
).resolve()
GENERATION_LOCK_DIR = HISTORY_DB.parent / ".generation_locks"

# Bump this value whenever prompts, policy cleaning, or formatter behavior
# changes. It is included in every cache key, so stale rendered output is not
# returned after a deployment.
CACHE_SCHEMA_VERSION = os.getenv("JOB_WEAVER_CACHE_VERSION", "3").strip() or "3"
HISTORY_LIMIT = _bounded_int("JOB_WEAVER_HISTORY_LIMIT", 100, 1, 10_000)
SQLITE_TIMEOUT_SECONDS = _bounded_int("JOB_WEAVER_SQLITE_TIMEOUT_SECONDS", 30, 1, 300)
GENERATION_LOCK_TIMEOUT_SECONDS = _bounded_int(
    "JOB_WEAVER_GENERATION_LOCK_TIMEOUT_SECONDS", 300, 1, 1_800
)
GENERATION_LOCK_STALE_SECONDS = _bounded_int(
    "JOB_WEAVER_GENERATION_LOCK_STALE_SECONDS", 900, 60, 7_200
)


def normalize_input_text(text: str) -> str:
    """Normalize input without joining words that were separated by tabs."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    text = "".join(ch for ch in text if ch.isprintable() or ch == "\n")
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def clean_text_for_hash(text: str) -> str:
    return normalize_input_text(text).casefold()


def normalize_url_for_hash(url: Optional[str]) -> str:
    """Lowercase only URL components that are case-insensitive.

    URL paths, queries, and fragments remain case-sensitive. In particular,
    ``/Job/A`` and ``/job/a`` must not collide in the cache.
    """
    value = (url or "").strip()
    if not value:
        return ""
    parts = urlsplit(value)
    if not parts.scheme or not parts.netloc:
        return value
    return urlunsplit(
        (
            parts.scheme.casefold(),
            parts.netloc.casefold(),
            parts.path,
            parts.query,
            parts.fragment,
        )
    )


def normalize_output_selection(selection: Any = None) -> Dict[str, bool]:
    if selection is None:
        return {"inmail": True, "jd": True}
    if hasattr(selection, "model_dump"):
        selection = selection.model_dump()
    if not isinstance(selection, Mapping):
        return {"inmail": True, "jd": True}
    return {
        "inmail": bool(selection.get("inmail", True)),
        "jd": bool(selection.get("jd", True)),
    }


def _selection_json(selection: Any = None) -> str:
    return json.dumps(
        normalize_output_selection(selection), sort_keys=True, separators=(",", ":")
    )


def _compute_key(
    raw_jd: str,
    client: str,
    url: Optional[str],
    owner_id: str = "local",
    output_selection: Any = None,
) -> str:
    payload = {
        "cache_version": CACHE_SCHEMA_VERSION,
        "client": (client or "mercor").strip().casefold(),
        "output_selection": normalize_output_selection(output_selection),
        "owner_id": (owner_id or "local").strip(),
        "raw_jd": clean_text_for_hash(raw_jd),
        "url": normalize_url_for_hash(url),
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


compute_cache_key = _compute_key


def _connect() -> sqlite3.Connection:
    HISTORY_DB.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(
        str(HISTORY_DB),
        timeout=SQLITE_TIMEOUT_SECONDS,
        isolation_level=None,
    )
    connection.row_factory = sqlite3.Row
    connection.execute(f"PRAGMA busy_timeout = {SQLITE_TIMEOUT_SECONDS * 1000}")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = FULL")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            created_at REAL NOT NULL,
            owner_id TEXT NOT NULL,
            client TEXT NOT NULL,
            url TEXT NOT NULL,
            raw_jd TEXT NOT NULL,
            role TEXT NOT NULL,
            raw_jd_snippet TEXT NOT NULL,
            cache_key TEXT NOT NULL,
            cache_version TEXT NOT NULL,
            output_selection TEXT NOT NULL,
            data_json TEXT NOT NULL,
            UNIQUE(owner_id, cache_key)
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_history_owner_time "
        "ON history(owner_id, created_at DESC)"
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS rate_events (
            bucket TEXT NOT NULL,
            occurred_at REAL NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_rate_bucket_time "
        "ON rate_events(bucket, occurred_at)"
    )
    return connection


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    connection = _connect()
    try:
        yield connection
    finally:
        connection.close()


def configure_history_database(path: Path | str) -> None:
    """Point storage at an isolated database (primarily for tests/tools)."""
    global HISTORY_DB, CACHE_DIR, GENERATION_LOCK_DIR
    HISTORY_DB = Path(path).resolve()
    CACHE_DIR = HISTORY_DB.parent
    GENERATION_LOCK_DIR = HISTORY_DB.parent / f".{HISTORY_DB.stem}_generation_locks"
    with _connection() as connection:
        connection.execute("SELECT 1")


def _ensure_classifications(
    data: Optional[Dict[str, Any]], role_hint: str = ""
) -> Optional[Dict[str, Any]]:
    """Coerce malformed classification fields without inventing content."""
    if not isinstance(data, dict):
        return data
    del role_hint  # Kept in the signature for compatibility with older callers.
    for field in ("titles", "job_functions", "industries", "skills"):
        if not isinstance(data.get(field), list):
            data[field] = []
    return data


def _decode_data(row: sqlite3.Row, *, include_raw_jd: bool) -> Dict[str, Any]:
    try:
        decoded = json.loads(row["data_json"])
    except (TypeError, json.JSONDecodeError):
        decoded = {}
    data = decoded if isinstance(decoded, dict) else {}
    data = _ensure_classifications(data, row["role"]) or {}
    data["_id"] = row["id"]
    data["_timestamp"] = row["timestamp"]
    data["_client"] = row["client"]
    data["_url"] = row["url"]
    data["_raw_jd_snippet"] = row["raw_jd_snippet"]
    data["_output_selection"] = json.loads(row["output_selection"])
    if include_raw_jd:
        data["_raw_jd"] = row["raw_jd"]
    return data


def get_cached_item(
    raw_jd: str,
    client: str,
    url: Optional[str] = None,
    owner_id: str = "local",
    output_selection: Any = None,
) -> Optional[Dict[str, Any]]:
    key = _compute_key(raw_jd, client, url, owner_id, output_selection)
    with _connection() as connection:
        row = connection.execute(
            "SELECT * FROM history WHERE owner_id = ? AND cache_key = ? LIMIT 1",
            (owner_id, key),
        ).fetchone()
    return _decode_data(row, include_raw_jd=True) if row else None


def add_item(
    raw_jd: str,
    client: str,
    url: Optional[str],
    data: Dict[str, Any],
    owner_id: str = "local",
    output_selection: Any = None,
) -> Dict[str, Any]:
    key = _compute_key(raw_jd, client, url, owner_id, output_selection)
    role = "Untitled Job"
    if isinstance(data, dict):
        if isinstance(data.get("structured_data"), dict):
            role = data["structured_data"].get("role", role) or role
        elif data.get("subject"):
            role = str(data["subject"]).split("|")[0].strip() or role

    normalized_data = _ensure_classifications(dict(data), role) or {}
    raw_text = raw_jd.strip()
    snippet = raw_text[:150] + ("..." if len(raw_text) > 150 else "")
    entry_id = str(uuid.uuid4())
    created_at = time.time()
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    selection = normalize_output_selection(output_selection)

    with _connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute(
                "DELETE FROM history WHERE owner_id = ? AND cache_key = ?",
                (owner_id, key),
            )
            connection.execute(
                """
                INSERT INTO history (
                    id, timestamp, created_at, owner_id, client, url, raw_jd,
                    role, raw_jd_snippet, cache_key, cache_version,
                    output_selection, data_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    timestamp,
                    created_at,
                    owner_id,
                    client,
                    url or "",
                    raw_jd,
                    role,
                    snippet,
                    key,
                    CACHE_SCHEMA_VERSION,
                    _selection_json(selection),
                    json.dumps(normalized_data, ensure_ascii=False),
                ),
            )
            connection.execute(
                """
                DELETE FROM history
                WHERE id IN (
                    SELECT id FROM history
                    WHERE owner_id = ?
                    ORDER BY created_at DESC, rowid DESC
                    LIMIT -1 OFFSET ?
                )
                """,
                (owner_id, HISTORY_LIMIT),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    return {
        "id": entry_id,
        "timestamp": timestamp,
        "client": client,
        "url": url or "",
        "raw_jd": raw_jd,
        "role": role,
        "raw_jd_snippet": snippet,
        "cache_key": key,
        "cache_version": CACHE_SCHEMA_VERSION,
        "output_selection": selection,
        "data": normalized_data,
    }


def get_history_list(owner_id: str = "local") -> List[Dict[str, Any]]:
    with _connection() as connection:
        rows = connection.execute(
            """
            SELECT id, timestamp, client, url, role, raw_jd_snippet,
                   output_selection
            FROM history
            WHERE owner_id = ?
            ORDER BY created_at DESC, rowid DESC
            LIMIT ?
            """,
            (owner_id, HISTORY_LIMIT),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "client": row["client"],
            "url": row["url"],
            "role": row["role"],
            "raw_jd_snippet": row["raw_jd_snippet"],
            "output_selection": json.loads(row["output_selection"]),
        }
        for row in rows
    ]


def get_history_detail(item_id: str, owner_id: str = "local") -> Optional[Dict[str, Any]]:
    with _connection() as connection:
        row = connection.execute(
            "SELECT * FROM history WHERE id = ? AND owner_id = ? LIMIT 1",
            (item_id, owner_id),
        ).fetchone()
    return _decode_data(row, include_raw_jd=True) if row else None


def delete_history_item(item_id: str, owner_id: str = "local") -> bool:
    with _connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            cursor = connection.execute(
                "DELETE FROM history WHERE id = ? AND owner_id = ?",
                (item_id, owner_id),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return cursor.rowcount > 0


def clear_history(owner_id: str = "local") -> None:
    with _connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute("DELETE FROM history WHERE owner_id = ?", (owner_id,))
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def check_rate_limit(bucket: str, limit: int, window_seconds: int) -> Optional[int]:
    """Record a request, or return seconds until the bucket can be retried."""
    if limit <= 0:
        return None
    now = time.time()
    cutoff = now - window_seconds
    with _connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute("DELETE FROM rate_events WHERE occurred_at < ?", (cutoff,))
            row = connection.execute(
                "SELECT COUNT(*) AS count, MIN(occurred_at) AS oldest "
                "FROM rate_events WHERE bucket = ? AND occurred_at >= ?",
                (bucket, cutoff),
            ).fetchone()
            if row["count"] >= limit:
                retry_after = max(1, math.ceil(window_seconds - (now - row["oldest"])))
                connection.commit()
                return retry_after
            connection.execute(
                "INSERT INTO rate_events(bucket, occurred_at) VALUES (?, ?)",
                (bucket, now),
            )
            connection.commit()
            return None
        except Exception:
            connection.rollback()
            raise


class GenerationLockTimeout(TimeoutError):
    pass


@contextmanager
def generation_lock(
    cache_key: str, timeout_seconds: Optional[int] = None
) -> Iterator[None]:
    """Acquire a process-safe lock for one cache key."""
    timeout = timeout_seconds or GENERATION_LOCK_TIMEOUT_SECONDS
    GENERATION_LOCK_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = GENERATION_LOCK_DIR / f"{cache_key}.lock"
    token = uuid.uuid4().hex
    deadline = time.monotonic() + timeout

    while True:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            try:
                os.write(descriptor, token.encode("ascii"))
            finally:
                os.close(descriptor)
            break
        except FileExistsError:
            try:
                age = time.time() - lock_path.stat().st_mtime
                if age > GENERATION_LOCK_STALE_SECONDS:
                    lock_path.unlink(missing_ok=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise GenerationLockTimeout("Timed out waiting for identical generation")
            time.sleep(0.05)

    try:
        yield
    finally:
        try:
            if lock_path.read_text(encoding="ascii") == token:
                lock_path.unlink(missing_ok=True)
        except FileNotFoundError:
            pass
