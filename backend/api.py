"""FastAPI entry point for Job Weaver."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import ipaddress
import json
import logging
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any, Dict, Optional
from urllib.parse import urlsplit

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware


# The parser/registry modules historically use backend-directory absolute
# imports. Keep script execution working while allowing ``import backend.api``
# from the repository root without requiring callers to mutate sys.path.
_BACKEND_DIR = Path(__file__).resolve().parent
if __package__ and str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

load_dotenv(dotenv_path=_BACKEND_DIR.parent / ".env")

if __package__:
    from .clients import SUPPORTED_CLIENTS
    from .history_cache import (
        CACHE_SCHEMA_VERSION,
        GenerationLockTimeout,
        _ensure_classifications,
        add_item,
        check_rate_limit,
        clear_history,
        compute_cache_key,
        delete_history_item,
        generation_lock,
        get_cached_item,
        get_history_detail,
        get_history_list,
        normalize_input_text,
        normalize_output_selection,
    )
    from .html_safety import sanitize_result_html
    from .llm_jd_parser import get_valid_llm_output
else:
    from clients import SUPPORTED_CLIENTS
    from history_cache import (
        CACHE_SCHEMA_VERSION,
        GenerationLockTimeout,
        _ensure_classifications,
        add_item,
        check_rate_limit,
        clear_history,
        compute_cache_key,
        delete_history_item,
        generation_lock,
        get_cached_item,
        get_history_detail,
        get_history_list,
        normalize_input_text,
        normalize_output_selection,
    )
    from html_safety import sanitize_result_html
    from llm_jd_parser import get_valid_llm_output


logger = logging.getLogger("job_weaver.api")


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return max(minimum, min(value, maximum))


def _csv_setting(name: str, defaults: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    values = defaults if not raw else tuple(part.strip() for part in raw.split(","))
    normalized = tuple(dict.fromkeys(value.rstrip("/") for value in values if value))
    if "*" in normalized:
        raise RuntimeError(f"{name} must not contain a wildcard")
    return normalized


def _allowed_hosts() -> tuple[str, ...]:
    configured = _csv_setting(
        "JOB_WEAVER_ALLOWED_HOSTS",
        ("localhost", "127.0.0.1", "[::1]", "testserver"),
    )
    # Render supplies its public hostname at runtime. Trusting that exact host
    # keeps host-header protection enabled without requiring a duplicated
    # dashboard setting that can drift when a service is renamed.
    render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip().rstrip("/")
    if render_hostname:
        configured = (*configured, render_hostname)
    return tuple(dict.fromkeys(configured))


MAX_RAW_JD_CHARS = _bounded_int("JOB_WEAVER_MAX_RAW_JD_CHARS", 100_000, 1_000, 1_000_000)
MAX_REQUEST_BYTES = _bounded_int("JOB_WEAVER_MAX_REQUEST_BYTES", 262_144, 4_096, 2_000_000)
GENERATION_RATE_LIMIT = _bounded_int(
    "JOB_WEAVER_GENERATION_RATE_LIMIT_PER_MINUTE", 12, 1, 1_000
)
RATE_LIMIT_WINDOW_SECONDS = 60

ALLOWED_ORIGINS = _csv_setting(
    "JOB_WEAVER_ALLOWED_ORIGINS",
    (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ),
)
ALLOWED_HOSTS = _allowed_hosts()


def _load_api_tokens() -> Dict[str, str]:
    tokens: Dict[str, str] = {}
    raw_mapping = os.getenv("JOB_WEAVER_API_TOKENS", "").strip()
    if raw_mapping:
        try:
            decoded = json.loads(raw_mapping)
        except json.JSONDecodeError as exc:
            raise RuntimeError("JOB_WEAVER_API_TOKENS must be a JSON object") from exc
        if not isinstance(decoded, dict):
            raise RuntimeError("JOB_WEAVER_API_TOKENS must be a JSON object")
        for owner, token in decoded.items():
            if not isinstance(owner, str) or not isinstance(token, str):
                raise RuntimeError(
                    "JOB_WEAVER_API_TOKENS owners and tokens must be strings"
                )
            owner_value = owner.strip()
            token_value = token.strip()
            if not owner_value or not token_value:
                raise RuntimeError(
                    "JOB_WEAVER_API_TOKENS owners and tokens must be non-empty"
                )
            tokens[owner_value] = token_value

    single_token = os.getenv("JOB_WEAVER_API_TOKEN", "").strip()
    if single_token:
        owner = os.getenv("JOB_WEAVER_USER_ID", "default").strip() or "default"
        tokens[owner] = single_token
    return tokens


_API_TOKENS = _load_api_tokens()


class OutputSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inmail: bool = True
    jd: bool = True

    @model_validator(mode="after")
    def at_least_one_output(self) -> "OutputSelection":
        if not self.inmail and not self.jd:
            raise ValueError("At least one output must be selected")
        return self


class JDRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_jd: str = Field(max_length=MAX_RAW_JD_CHARS)
    url: Optional[str] = Field(default=None, max_length=2_048)
    client: str = Field(default="mercor", min_length=1, max_length=64)
    output_selection: Optional[OutputSelection] = None

    @field_validator("url", mode="before")
    @classmethod
    def validate_job_url(cls, value: Any) -> Optional[str]:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        if not isinstance(value, str):
            raise ValueError("Job URL must be a string")
        candidate = value.strip()
        parts = urlsplit(candidate)
        if parts.scheme.casefold() not in {"http", "https"} or not parts.hostname:
            raise ValueError("Job URL must be an absolute HTTP or HTTPS URL")
        if parts.username or parts.password:
            raise ValueError("Job URL must not include credentials")
        return candidate


@dataclass(frozen=True)
class RequestIdentity:
    owner_id: str
    authenticated: bool


def _request_token(request: Request) -> Optional[str]:
    authorization = request.headers.get("authorization", "").strip()
    if authorization.casefold().startswith("bearer "):
        return authorization[7:].strip()
    api_key = request.headers.get("x-api-key", "").strip()
    return api_key or None


def _is_loopback_client(request: Request) -> bool:
    if not request.client:
        return False
    host = request.client.host.split("%", 1)[0]
    if host == "testclient":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host.casefold() == "localhost"


def get_request_identity(request: Request) -> RequestIdentity:
    supplied_token = _request_token(request)
    if _API_TOKENS:
        if not supplied_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API authentication is required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        for owner_id, expected_token in _API_TOKENS.items():
            if hmac.compare_digest(supplied_token, expected_token):
                return RequestIdentity(owner_id=owner_id, authenticated=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not _is_loopback_client(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Non-local access requires JOB_WEAVER_API_TOKEN",
        )
    return RequestIdentity(owner_id="local", authenticated=False)


class RequestSizeLimitMiddleware:
    def __init__(self, app: Any, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope.get("type") != "http" or scope.get("method") not in {
            "POST",
            "PUT",
            "PATCH",
        }:
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > self.max_bytes:
                    await JSONResponse(
                        {"detail": "Request body is too large"}, status_code=413
                    )(scope, receive, send)
                    return
            except ValueError:
                await JSONResponse(
                    {"detail": "Invalid Content-Length header"}, status_code=400
                )(scope, receive, send)
                return

        chunks: list[bytes] = []
        received = 0
        while True:
            message = await receive()
            if message.get("type") != "http.request":
                await self.app(scope, receive, send)
                return
            chunk = message.get("body", b"")
            chunks.append(chunk)
            received += len(chunk)
            if received > self.max_bytes:
                await JSONResponse(
                    {"detail": "Request body is too large"}, status_code=413
                )(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        body = b"".join(chunks)
        replayed = False

        async def replay_receive() -> dict:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        await self.app(scope, replay_receive, send)


class OriginPolicyMiddleware:
    def __init__(self, app: Any, allowed_origins: tuple[str, ...]) -> None:
        self.app = app
        self.allowed_origins = frozenset(allowed_origins)

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope.get("type") == "http":
            headers = {key.lower(): value for key, value in scope.get("headers", [])}
            raw_origin = headers.get(b"origin")
            if raw_origin:
                origin = raw_origin.decode("latin-1").rstrip("/")
                if origin not in self.allowed_origins:
                    await JSONResponse(
                        {"detail": "Origin is not allowed"}, status_code=403
                    )(scope, receive, send)
                    return
        await self.app(scope, receive, send)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(ALLOWED_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(ALLOWED_HOSTS))
app.add_middleware(OriginPolicyMiddleware, allowed_origins=ALLOWED_ORIGINS)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=MAX_REQUEST_BYTES)


def clean_input(text: str) -> str:
    return normalize_input_text(text)


def _rate_limit_generation(request: Request, identity: RequestIdentity) -> None:
    client_host = request.client.host if request.client else "unknown"
    bucket_material = f"{identity.owner_id}|{client_host}"
    bucket = hashlib.sha256(bucket_material.encode("utf-8")).hexdigest()
    try:
        retry_after = check_rate_limit(
            bucket, GENERATION_RATE_LIMIT, RATE_LIMIT_WINDOW_SECONDS
        )
    except sqlite3.Error as exc:
        logger.error("Rate-limit storage failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Rate limiting is unavailable") from exc
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Generation rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )


def _apply_output_selection(data: Dict[str, Any], selection: Dict[str, bool]) -> Dict[str, Any]:
    selected = dict(data)
    if not selection["jd"]:
        selected["jd"] = ""
        selected["linkedin_title"] = ""
    if not selection["inmail"]:
        selected["email"] = ""
        selected["email_draft"] = None
        selected["inmail_draft"] = None
        selected["subject"] = ""
    return selected


def _cache_response(cached_result: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(cached_result)
    item_id = result.get("_id")
    result.pop("success", None)
    result.pop("cached", None)
    result.pop("_raw_jd", None)
    return {"success": True, **result, "id": item_id, "cached": True}


@app.post("/parse-jd")
def parse_jd(
    request: JDRequest,
    http_request: Request,
    identity: RequestIdentity = Depends(get_request_identity),
) -> Dict[str, Any]:
    raw = clean_input(request.raw_jd)
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A non-empty raw job description is required",
        )

    client_id = request.client.strip().casefold()
    if client_id not in SUPPORTED_CLIENTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported client",
        )

    selection = normalize_output_selection(request.output_selection)
    _rate_limit_generation(http_request, identity)
    cache_key = compute_cache_key(
        raw, client_id, request.url, identity.owner_id, selection
    )

    try:
        cached_result = get_cached_item(
            raw,
            client_id,
            request.url,
            identity.owner_id,
            selection,
        )
    except sqlite3.Error as exc:
        logger.error("History lookup failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="History storage is unavailable") from exc
    if cached_result:
        return _cache_response(cached_result)

    try:
        with generation_lock(cache_key):
            # A concurrent worker may have populated the cache while this
            # request waited for the single-flight lock.
            cached_result = get_cached_item(
                raw,
                client_id,
                request.url,
                identity.owner_id,
                selection,
            )
            if cached_result:
                return _cache_response(cached_result)

            try:
                parsed_result = get_valid_llm_output(
                    raw, url=request.url, client=client_id
                )
            except Exception as exc:
                logger.error("JD generation failed (%s)", type(exc).__name__)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="The generation service could not produce an output",
                ) from exc

            if not isinstance(parsed_result, dict):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="The generation service returned an invalid output",
                )

            classified = _ensure_classifications(dict(parsed_result), "") or {}
            safe_result = sanitize_result_html(classified)
            selected_result = _apply_output_selection(safe_result, selection)
            entry = add_item(
                raw,
                client_id,
                request.url,
                selected_result,
                identity.owner_id,
                selection,
            )
    except GenerationLockTimeout as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="An identical generation is still in progress",
            headers={"Retry-After": "5"},
        ) from exc
    except sqlite3.Error as exc:
        logger.error("History update failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="History storage is unavailable") from exc

    return {
        "success": True,
        **selected_result,
        "id": entry["id"],
        "_id": entry["id"],
        "_timestamp": entry["timestamp"],
        "_client": client_id,
        "_url": request.url or "",
        "_output_selection": selection,
        "cached": False,
    }


@app.get("/history")
def get_history(
    identity: RequestIdentity = Depends(get_request_identity),
) -> Dict[str, Any]:
    try:
        history = get_history_list(identity.owner_id)
    except sqlite3.Error as exc:
        logger.error("History listing failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="History storage is unavailable") from exc
    return {"success": True, "history": history}


@app.get("/history/{item_id}")
def get_history_item(
    item_id: str,
    identity: RequestIdentity = Depends(get_request_identity),
) -> Dict[str, Any]:
    try:
        data = get_history_detail(item_id, identity.owner_id)
    except sqlite3.Error as exc:
        logger.error("History detail lookup failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="History storage is unavailable") from exc
    if not data:
        raise HTTPException(status_code=404, detail="History item not found")
    return {"success": True, "data": data}


@app.delete("/history/{item_id}")
def remove_history_item(
    item_id: str,
    identity: RequestIdentity = Depends(get_request_identity),
) -> Dict[str, bool]:
    try:
        deleted = delete_history_item(item_id, identity.owner_id)
    except sqlite3.Error as exc:
        logger.error("History deletion failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="History storage is unavailable") from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="History item not found")
    return {"success": True}


@app.delete("/history")
def purge_history(
    identity: RequestIdentity = Depends(get_request_identity),
) -> Dict[str, bool]:
    try:
        clear_history(identity.owner_id)
    except sqlite3.Error as exc:
        logger.error("History purge failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="History storage is unavailable") from exc
    return {"success": True}


@app.get("/")
def health_check() -> Dict[str, str]:
    return {
        "status": "running",
        "cache_version": CACHE_SCHEMA_VERSION,
        "access_mode": "token" if _API_TOKENS else "local-only",
    }
