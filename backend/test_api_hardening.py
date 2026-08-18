"""Focused regression tests for API, cache, and history hardening."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

from fastapi.testclient import TestClient


os.environ.setdefault("OPENAI_API_KEY", "test-key")

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import api  # noqa: E402
import history_cache  # noqa: E402
from html_safety import sanitize_rich_html  # noqa: E402


def _fake_result() -> dict:
    return {
        "jd": '<b>Safe JD</b><img src="x" onerror="alert(1)">',
        "email": "<b>Safe email</b>",
        "email_draft": "<b>Safe email</b>",
        "inmail_draft": "<b>Safe InMail</b>",
        "subject": "Role | Remote",
        "linkedin_title": "Role | Remote",
        "titles": [],
        "skills": [],
        "job_functions": [],
        "industries": [],
        "structured_data": {"role": "Role"},
    }


class ApiHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        history_cache.configure_history_database(
            Path(self.temp_dir.name) / "history.sqlite3"
        )
        self.client = TestClient(api.app)
        self.rate_patch = mock.patch.object(api, "GENERATION_RATE_LIMIT", 1_000)
        self.rate_patch.start()

    def tearDown(self) -> None:
        self.rate_patch.stop()
        self.client.close()
        self.temp_dir.cleanup()

    def test_strict_origins_and_local_or_token_access(self) -> None:
        denied = self.client.get(
            "/history", headers={"Origin": "https://attacker.example"}
        )
        self.assertEqual(denied.status_code, 403)

        preflight = self.client.options(
            "/history",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "DELETE",
            },
        )
        self.assertEqual(preflight.status_code, 200)
        self.assertEqual(
            preflight.headers.get("access-control-allow-origin"),
            "http://localhost:3000",
        )
        self.assertNotEqual(
            preflight.headers.get("access-control-allow-credentials"), "true"
        )

        preview_preflight = self.client.options(
            "/history",
            headers={
                "Origin": "http://127.0.0.1:4173",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(preview_preflight.status_code, 200)
        self.assertEqual(
            preview_preflight.headers.get("access-control-allow-origin"),
            "http://127.0.0.1:4173",
        )

        remote_client = TestClient(api.app, client=("198.51.100.10", 50000))
        try:
            self.assertEqual(remote_client.get("/history").status_code, 403)
            with mock.patch.object(api, "_API_TOKENS", {"alice": "test-token"}):
                self.assertEqual(self.client.get("/history").status_code, 401)
                authorized = remote_client.get(
                    "/history", headers={"Authorization": "Bearer test-token"}
                )
                self.assertEqual(authorized.status_code, 200)
        finally:
            remote_client.close()

    def test_validation_http_errors_and_size_limit(self) -> None:
        empty = self.client.post(
            "/parse-jd", json={"raw_jd": "\t\r\n", "client": "mercor"}
        )
        self.assertEqual(empty.status_code, 422)

        invalid_url = self.client.post(
            "/parse-jd",
            json={
                "raw_jd": "Valid input",
                "client": "mercor",
                "url": "javascript:alert(1)",
            },
        )
        self.assertEqual(invalid_url.status_code, 422)

        invalid_client = self.client.post(
            "/parse-jd", json={"raw_jd": "Valid input", "client": "unknown"}
        )
        self.assertEqual(invalid_client.status_code, 422)

        oversized = self.client.post(
            "/parse-jd",
            content="x" * (api.MAX_REQUEST_BYTES + 1),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(oversized.status_code, 413)

        with mock.patch.object(
            api, "get_valid_llm_output", side_effect=RuntimeError("private detail")
        ):
            upstream = self.client.post(
                "/parse-jd", json={"raw_jd": "Valid input", "client": "mercor"}
            )
        self.assertEqual(upstream.status_code, 502)
        self.assertNotIn("private detail", upstream.text)

    def test_output_selection_isolated_cache_ids_and_sanitization(self) -> None:
        calls = 0

        def generate(*args, **kwargs):
            nonlocal calls
            calls += 1
            return _fake_result()

        base = {
            "raw_jd": "A\tqualified candidate",
            "url": "https://EXAMPLE.test/Jobs/RoleA",
            "client": "stemsyncai",
        }
        with mock.patch.object(api, "get_valid_llm_output", side_effect=generate):
            jd_only = self.client.post(
                "/parse-jd",
                json={
                    **base,
                    "output_selection": {"inmail": False, "jd": True},
                },
            )
            self.assertEqual(jd_only.status_code, 200)
            body = jd_only.json()
            self.assertTrue(body["id"])
            self.assertEqual(body["id"], body["_id"])
            self.assertEqual(body["email"], "")
            self.assertIsNone(body["inmail_draft"])
            self.assertNotIn("onerror", body["jd"])
            self.assertEqual(body["titles"], [])

            cached = self.client.post(
                "/parse-jd",
                json={
                    **base,
                    "output_selection": {"inmail": False, "jd": True},
                },
            )
            self.assertTrue(cached.json()["cached"])
            self.assertEqual(cached.json()["id"], body["id"])

            inmail_only = self.client.post(
                "/parse-jd",
                json={
                    **base,
                    "output_selection": {"inmail": True, "jd": False},
                },
            )
            self.assertEqual(inmail_only.status_code, 200)
            self.assertEqual(inmail_only.json()["jd"], "")
            self.assertNotEqual(inmail_only.json()["id"], body["id"])

        self.assertEqual(calls, 2)
        detail = self.client.get(f"/history/{body['id']}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(
            detail.json()["data"]["_output_selection"],
            {"inmail": False, "jd": True},
        )

    def test_identical_concurrent_requests_use_one_generation(self) -> None:
        calls = 0
        calls_lock = threading.Lock()

        def slow_generation(*args, **kwargs):
            nonlocal calls
            with calls_lock:
                calls += 1
            time.sleep(0.2)
            return _fake_result()

        payload = {"raw_jd": "Concurrent JD", "client": "mercor"}

        def send_request() -> tuple[int, dict]:
            with TestClient(api.app) as client:
                response = client.post("/parse-jd", json=payload)
                return response.status_code, response.json()

        with mock.patch.object(
            api, "get_valid_llm_output", side_effect=slow_generation
        ):
            with ThreadPoolExecutor(max_workers=2) as executor:
                responses = list(executor.map(lambda _: send_request(), range(2)))

        self.assertEqual([code for code, _ in responses], [200, 200])
        self.assertEqual(calls, 1)
        self.assertEqual(responses[0][1]["id"], responses[1][1]["id"])
        self.assertEqual(sorted(body["cached"] for _, body in responses), [False, True])

    def test_cache_key_version_selection_and_url_path_case(self) -> None:
        common = ("Raw\tJD", "mercor")
        upper_path = history_cache.compute_cache_key(
            *common, "https://EXAMPLE.com/Jobs/A", "owner", {"inmail": True, "jd": False}
        )
        same_host_case = history_cache.compute_cache_key(
            *common, "https://example.COM/Jobs/A", "owner", {"inmail": True, "jd": False}
        )
        lower_path = history_cache.compute_cache_key(
            *common, "https://example.com/jobs/a", "owner", {"inmail": True, "jd": False}
        )
        other_selection = history_cache.compute_cache_key(
            *common, "https://example.com/Jobs/A", "owner", {"inmail": False, "jd": True}
        )
        self.assertEqual(upper_path, same_host_case)
        self.assertNotEqual(upper_path, lower_path)
        self.assertNotEqual(upper_path, other_selection)

        with mock.patch.object(history_cache, "CACHE_SCHEMA_VERSION", "next"):
            next_version = history_cache.compute_cache_key(
                *common,
                "https://example.com/Jobs/A",
                "owner",
                {"inmail": True, "jd": False},
            )
        self.assertNotEqual(upper_path, next_version)
        self.assertEqual(api.clean_input("two\tyears"), "two years")

    def test_history_is_scoped_bounded_and_has_real_404s(self) -> None:
        with mock.patch.object(history_cache, "HISTORY_LIMIT", 3):
            history_cache.add_item(
                "Bob JD",
                "mercor",
                None,
                {"titles": [], "structured_data": {"role": "Bob Role"}},
                owner_id="bob",
            )
            for index in range(4):
                history_cache.add_item(
                    f"JD {index}",
                    "mercor",
                    None,
                    {"titles": [], "structured_data": {"role": f"Role {index}"}},
                    owner_id="alice",
                )
        self.assertEqual(len(history_cache.get_history_list("alice")), 3)
        self.assertEqual(len(history_cache.get_history_list("bob")), 1)
        self.assertEqual(self.client.get("/history/missing").status_code, 404)
        self.assertEqual(self.client.delete("/history/missing").status_code, 404)

    def test_history_accepts_concurrent_process_writers(self) -> None:
        database = Path(self.temp_dir.name) / "multi-process.sqlite3"
        script = (
            "import sys; import backend.history_cache as h; "
            "h.configure_history_database(sys.argv[1]); "
            "h.add_item(sys.argv[2], 'mercor', None, {'titles': []}, owner_id='owner')"
        )
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        processes = [
            subprocess.Popen(
                [sys.executable, "-B", "-c", script, str(database), f"JD {index}"],
                cwd=PROJECT_ROOT,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for index in range(4)
        ]
        failures = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=30)
            if process.returncode:
                failures.append((process.returncode, stdout, stderr))
        self.assertEqual(failures, [])
        history_cache.configure_history_database(database)
        self.assertEqual(len(history_cache.get_history_list("owner")), 4)

    def test_rate_limit_is_shared_through_storage(self) -> None:
        with mock.patch.object(api, "GENERATION_RATE_LIMIT", 1), mock.patch.object(
            api, "get_valid_llm_output", return_value=_fake_result()
        ):
            first = self.client.post(
                "/parse-jd", json={"raw_jd": "First JD", "client": "mercor"}
            )
            second = self.client.post(
                "/parse-jd", json={"raw_jd": "Second JD", "client": "mercor"}
            )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertIn("retry-after", second.headers)

    def test_rich_html_allowlist(self) -> None:
        dirty = (
            '<a href="javascript:alert(1)" onclick="alert(2)" '
            'style="color:#0066cc;position:fixed">link</a>'
            '<script>alert(3)</script><b>safe</b>'
        )
        cleaned = sanitize_rich_html(dirty)
        self.assertNotIn("javascript:", cleaned)
        self.assertNotIn("onclick", cleaned)
        self.assertNotIn("position", cleaned)
        self.assertNotIn("alert(3)", cleaned)
        self.assertIn("<b>safe</b>", cleaned)

    def test_package_and_script_import_smoke(self) -> None:
        environment = dict(os.environ)
        environment["OPENAI_API_KEY"] = "test-key"
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        package_import = subprocess.run(
            [sys.executable, "-B", "-c", "import backend.api"],
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(package_import.returncode, 0, package_import.stderr)
        script_import = subprocess.run(
            [sys.executable, "-B", "-c", "import api"],
            cwd=BACKEND_DIR,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(script_import.returncode, 0, script_import.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
