"""
Mercor Job Scraper → Supabase
==============================
Scrapes all job listings from work.mercor.com/explore via API interception,
cleans/normalizes the data, and upserts into a Supabase `mercor_jobs` table.

Uses httpx for Supabase REST API calls (no supabase-py dependency needed).

Usage:
    set SUPABASE_URL=https://ixzcmfbbkvwfyfsesthl.supabase.co
    set SUPABASE_SERVICE_ROLE_KEY=sb_secret_9gTaYPsx87WK_DPdihthaA_IAYkA6dq
    python mercor_scraper_supabase.py [--visible] [--dry-run]
"""

import io
import os
import re
import sys
import time
import hashlib
from datetime import datetime, timezone
from html import unescape

# Fix Windows console encoding
try:
    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True
        )
except Exception:
    pass

import httpx
from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://ixzcmfbbkvwfyfsesthl.supabase.co"
)
SUPABASE_KEY = os.environ.get(
    "SUPABASE_SERVICE_ROLE_KEY", "sb_secret_9gTaYPsx87WK_DPdihthaA_IAYkA6dq"
)

MAX_RETRIES = 3
RETRY_DELAY = 2          # seconds between retries
SCROLL_PAUSE = 2          # seconds between scrolls
MAX_SCROLL_ATTEMPTS = 30   # max scroll iterations


# ---------------------------------------------------------------------------
# Supabase REST API helpers
# ---------------------------------------------------------------------------

def _supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

def _rest_url(table: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{table}"

def fetch_existing_job(job_id: str) -> dict | None:
    """Fetch an existing job using job_id."""
    try:
        resp = httpx.get(
            _rest_url("mercor_jobs"),
            params={"job_id": f"eq.{job_id}"},
            headers=_supabase_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        rows = resp.json()
        return rows[0] if rows else None
    except Exception as e:
        print(f"      [!] Error fetching existing job: {e}")
        return None

def upsert_job(record: dict):
    """Upsert a single job into Supabase with on_conflict behavior."""
    headers = _supabase_headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    resp = httpx.post(
        f"{_rest_url('mercor_jobs')}?on_conflict=job_id",
        json=[record],
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# Data Cleaning Helpers
# ---------------------------------------------------------------------------

def has_changed(existing, new):
    fields_to_check = [
        "job_title",
        "compensation_min",
        "compensation_max",
        "compensation_type",
        "compensation_range",
        "hires_this_month",
        "job_description",
        "referral_bonus",
        "job_url"
    ]
    for field in fields_to_check:
        if existing.get(field) != new.get(field):
            return True
    return False

def is_incomplete(record: dict) -> bool:
    """A record is INCOMPLETE if any of the required fields are missing."""
    jd = record.get("job_description")
    if not jd or len(jd) < 200:
        return True
    if record.get("compensation_min") is None:
        return True
    if record.get("hires_this_month") is None:
        return True
    if record.get("referral_bonus") is None:
        return True
    return False

def strip_html(text: str | None) -> str | None:
    if not text:
        return None
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text if text else None

def slugify(title: str) -> str:
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    return slug.strip("-")

def build_job_url(title: str, listing_id: str) -> str:
    return f"https://work.mercor.com/jobs/{slugify(title)}-{listing_id}"

def derive_job_id(listing: dict) -> str:
    lid = listing.get("listingId")
    if lid:
        return lid
    url = listing.get("_url", "")
    title = listing.get("title", "")
    return hashlib.sha256(f"{url}:{title}".encode()).hexdigest()[:32]

def parse_compensation(listing: dict) -> dict:
    rate_min = listing.get("rateMin")
    rate_max = listing.get("rateMax")
    
    if rate_min is None and rate_max is not None:
        rate_min = rate_max
    if rate_max is None and rate_min is not None:
        rate_max = rate_min

    frequency = listing.get("payRateFrequency", "")
    commitment = listing.get("commitment", "")
    comp_type = frequency.lower() if frequency else None
    freq_labels = {"hourly": "/hr", "weekly": "/week", "monthly": "/month", "yearly": "/year", "one-time": " (one-time)"}
    if commitment == "FULL_TIME" and rate_max and rate_max < 1000:
        freq_suffix = "/hr"
        comp_type = "hourly"
    else:
        freq_suffix = freq_labels.get(frequency, f" ({frequency})" if frequency else "")
    if rate_min and rate_max and rate_min != rate_max:
        comp_range = f"${rate_min:,.0f} - ${rate_max:,.0f}{freq_suffix}"
    elif rate_max:
        comp_range = f"${rate_max:,.0f}{freq_suffix}"
    elif rate_min:
        comp_range = f"${rate_min:,.0f}{freq_suffix}"
    else:
        comp_range = None
    return {
        "compensation_min": float(rate_min) if rate_min else None,
        "compensation_max": float(rate_max) if rate_max else None,
        "compensation_type": comp_type,
        "compensation_range": comp_range,
    }

def parse_hires(listing: dict) -> int | None:
    rc = listing.get("recentCandidatesCount")
    if rc is not None:
        try:
            return int(rc)
        except (ValueError, TypeError):
            return None
    return None

def parse_referral(listing: dict) -> float | None:
    raw = listing.get("referralAmount")
    if raw:
        try:
            val = float(raw)
            return val if val > 0 else None
        except (ValueError, TypeError):
            return None
    return None

def clean_listing(listing: dict, description: str | None = None) -> dict:
    title = listing.get("title") or "Untitled"
    listing_id = derive_job_id(listing)
    comp = parse_compensation(listing)
    url = build_job_url(title, listing_id)
    return {
        "job_id": listing_id,
        "job_title": title,
        "compensation_min": comp["compensation_min"],
        "compensation_max": comp["compensation_max"],
        "compensation_type": comp["compensation_type"],
        "compensation_range": comp["compensation_range"],
        "hires_this_month": parse_hires(listing),
        "job_description": strip_html(description),
        "referral_bonus": parse_referral(listing),
        "job_url": url,
    }


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------

def scrape_mercor_jobs(headless: bool = True, dry_run: bool = False) -> dict:
    all_listings: dict[str, dict] = {}
    api_captured = False

    print("[*] Starting Mercor Job Scraper → Supabase pipeline...")
    if not SUPABASE_KEY:
        print("[X] SUPABASE_SERVICE_ROLE_KEY not set! Exiting.")
        sys.exit(1)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()

        def handle_response(response):
            nonlocal api_captured
            url = response.url
            if "listings-explore-page" in url or "listings-public" in url:
                try:
                    body = response.json()
                    items = []
                    if isinstance(body, dict) and "listings" in body:
                        items = body["listings"]
                    elif isinstance(body, list):
                        items = body
                    if items:
                        for item in items:
                            lid = item.get("listingId")
                            if lid and lid not in all_listings:
                                all_listings[lid] = item
                        api_captured = True
                        print(f"[+] API batch captured — total unique listings: {len(all_listings)}")
                except Exception as e:
                    print(f"[!] Error parsing API response: {e}")

        page.on("response", handle_response)

        print("[*] Loading https://work.mercor.com/explore ...")
        try:
            page.goto("https://work.mercor.com/explore", wait_until="networkidle", timeout=30_000)
        except PwTimeout:
            print("[!] Page load timed out, continuing...")

        page.wait_for_timeout(3000)

        print("[*] Scrolling to load all listings...")
        prev_count = 0
        stale_count = 0
        for _ in range(MAX_SCROLL_ATTEMPTS):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(int(SCROLL_PAUSE * 1000))
            current = len(all_listings)
            if current == prev_count:
                stale_count += 1
                if stale_count >= 3:
                    print(f"[+] No new listings after {stale_count} scrolls — done loading.")
                    break
            else:
                stale_count = 0
                prev_count = current

        print(f"[+] Total unique listings captured: {len(all_listings)}")

        listings_list = list(all_listings.values())
        total = len(listings_list)
        
        stats = {"inserted": 0, "updated": 0, "skipped": 0, "errors": 0}
        print(f"\n[*] Processing and verifying completeness for {total} listings...\n")

        detail_page = context.new_page()
        base_explore = "https://work.mercor.com/explore?listingId="

        EXTRACT_DESC_JS = """() => {
            const paragraphs = document.querySelectorAll('p.mb-2.mt-2.text-base.text-gray-600');
            const parts = [];
            for (const p of paragraphs) {
                const text = p.innerText.trim();
                if (text.length > 30) parts.push(text);
            }
            if (parts.length > 0) return parts.join('\\n\\n');

            const sections = document.querySelectorAll('section.mt-8, div.min-w-0.overflow-x-hidden.break-words');
            for (const sec of sections) {
                const text = sec.innerText.trim();
                if (text.length > 100) return text;
            }
            return '';
        }"""

        for i, listing in enumerate(listings_list, 1):
            title = listing.get("title") or "Untitled"
            listing_id = derive_job_id(listing)

            # Need to scrape JD
            description = ""
            for attempt in range(MAX_RETRIES):
                try:
                    detail_url = f"{base_explore}{listing_id}"
                    try:
                        detail_page.goto(detail_url, wait_until="networkidle", timeout=20_000)
                    except PwTimeout:
                        pass
                    detail_page.wait_for_timeout(1500)
                    description = detail_page.evaluate(EXTRACT_DESC_JS) or ""
                    break
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                        try:
                            detail_page.close()
                        except Exception:
                            pass
                        detail_page = context.new_page()
                    else:
                        print(f"    [X] Gave up on JD for: {title[:60]}")

            # Error handling: Do not upsert if JD is missing
            if not description:
                print(f"  [{i}/{total}] SKIP (No JD Scraped) {title[:48]:50s}")
                stats["errors"] += 1
                continue

            record = clean_listing(listing, description)

            existing_record = fetch_existing_job(listing_id)

            if existing_record:
                if not has_changed(existing_record, record):
                    print(f"  [{i}/{total}] SKIP (No Change) {title[:50]:52s}")
                    stats["skipped"] += 1
                    continue
                else:
                    action = "updated"
            else:
                action = "inserted"
                
            record["updated_at"] = datetime.now(timezone.utc).isoformat()

            if dry_run:
                if action == "updated":
                    stats["updated"] += 1
                else:
                    stats["inserted"] += 1
                print(f"  [{i}/{total}] DRY-RUN (Would Upsert) {title[:45]:47s}")
                continue

            # Upsert into Supabase
            try:
                upsert_job(record)
                if action == "updated":
                    stats["updated"] += 1
                    print(f"  [{i}/{total}] UPDATED {title[:55]:57s}")
                else:
                    stats["inserted"] += 1
                    print(f"  [{i}/{total}] INSERTED {title[:54]:56s}")
            except Exception as e:
                print(f"  [{i}/{total}] ERROR (Upsert Failed) {e}")
                stats["errors"] += 1

        try:
            detail_page.close()
        except Exception:
            pass
        browser.close()

    return stats


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape Mercor jobs → Supabase")
    parser.add_argument("--visible", "-v", action="store_true", help="Show browser window")
    parser.add_argument("--dry-run", action="store_true", help="Scrape only, skip Supabase upload")
    args = parser.parse_args()

    stats = scrape_mercor_jobs(headless=not.
    args.visible, dry_run=args.dry_run)

    print("\n" + "=" * 50)
    print("  SCRAPE COMPLETED STATUS")
    print("=" * 50)
    print(f"  Records Inserted: {stats['inserted']}")
    print(f"  Records Updated:  {stats['updated']}")
    print(f"  Records Skipped:  {stats['skipped']}")
    print(f"  Errors / Missing JD: {stats['errors']}")
    print("=" * 50)
