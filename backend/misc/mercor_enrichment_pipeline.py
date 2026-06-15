import os
import sys
import time
import argparse
from typing import List

import httpx
from pydantic import BaseModel, Field

try:
    from openai import OpenAI
except ImportError:
    print("[X] 'openai' package not found. Please install via: pip install openai pydantic")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ixzcmfbbkvwfyfsesthl.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "sb_secret_9gTaYPsx87WK_DPdihthaA_IAYkA6dq")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "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")

if not SUPABASE_KEY:
    print("[X] SUPABASE_SERVICE_ROLE_KEY is required as an environment variable.")
    sys.exit(1)
if not OPENAI_API_KEY:
    print("[X] OPENAI_API_KEY is required as an environment variable.")
    sys.exit(1)

MAX_RETRIES = 3
RETRY_DELAY = 2

# ---------------------------------------------------------------------------
# Structure Definitions
# ---------------------------------------------------------------------------
class JobEnrichment(BaseModel):
    cleaned_description: str = Field(description="Information-dense job description. Start directly with role responsibilities. DO NOT start with company name or 'Mercor is hiring'. Include specific tools, technologies, and tasks.")
    skills: List[str] = Field(description="List of specific technical skill names. Max 1-3 words. Lowercase. Exclude soft skills, broad categories, and languages (unless role-specific).")
    seniority_level: str = Field(description="Seniority level: junior/mid/senior/expert")
    role_category: str = Field(description="Broad category like software engineering, data, design, marketing")

# ---------------------------------------------------------------------------
# Supabase API Helpers
# ---------------------------------------------------------------------------
def _supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

def fetch_unprocessed_jobs(limit: int = 0) -> list[dict]:
    """Fetch rows from Supabase where cleaned_description is NULL."""
    url = f"{SUPABASE_URL}/rest/v1/mercor_jobs"
    params = {
        "cleaned_description": "is.null",
        "select": "job_id,job_title,job_description"
    }
    if limit > 0:
        params["limit"] = str(limit)

    print(f"[*] Fetching unprocessed jobs from Supabase... (limit={limit if limit > 0 else 'none'})")
    
    resp = httpx.get(url, params=params, headers=_supabase_headers(), timeout=30)
    resp.raise_for_status()
    jobs = resp.json()
    print(f"[+] Found {len(jobs)} jobs to process.")
    return jobs

def update_job_in_supabase(job_id: str, data: dict):
    """Update structured fields and embedding for a specific job in Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/mercor_jobs"
    params = {"job_id": f"eq.{job_id}"}
    
    resp = httpx.patch(url, params=params, json=data, headers=_supabase_headers(), timeout=30)
    resp.raise_for_status()

# ---------------------------------------------------------------------------
# Pipeline Execution
# ---------------------------------------------------------------------------
def process_job(job: dict, client: OpenAI) -> dict:
    """Process a single job description through the LLM and Embedding models."""
    job_desc = job.get("job_description")
    job_title = job.get("job_title", "Unknown Title")
    
    if not job_desc or len(job_desc) < 20:
        raise ValueError("Job description is too short or missing.")

    # 1. LLM Extraction
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert HR assistant. Extract fields. For cleaned_description: Start directly with role responsibilities; DO NOT start with company name or generic phrases like 'Mercor is hiring'. Include specific tools, technologies, and tasks. Make it information-dense, not generic. Preserve technical details/keywords and do not overly summarize. For skills: specific technical terms only (max 1-3 words, lowercase), similar granularity. Exclude soft skills, personality traits, and languages (unless role-specific)."},
            {"role": "user", "content": f"Title: {job_title}\n\nDescription: {job_desc}"}
        ],
        response_format=JobEnrichment,
    )
    
    parsed = completion.choices[0].message.parsed
    if not parsed:
        raise ValueError("Failed to parse LLM structured output.")
    
    # Post-process skills
    processed_skills = [s.lower().strip() for s in parsed.skills]
    
    # 2. Embedding Generation
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=parsed.cleaned_description,
        dimensions=1536
    )
    embedding = response.data[0].embedding
    
    return {
        "cleaned_description": parsed.cleaned_description,
        "skills": processed_skills,
        "seniority_level": parsed.seniority_level,
        "role_category": parsed.role_category,
        "embedding": embedding
    }

def run_pipeline(dry_run: bool, limit: int):
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        jobs = fetch_unprocessed_jobs(limit=limit)
    except Exception as e:
        print(f"[X] Failed to fetch jobs from Supabase: {e}")
        return

    processed_count = 0
    failure_count = 0

    for i, job in enumerate(jobs, 1):
        job_id = job.get("job_id")
        title = job.get("job_title", "Untitled")
        print(f"[{i}/{len(jobs)}] Processing: {title[:50]} ({job_id})")
        
        success = False
        for attempt in range(MAX_RETRIES):
            try:
                enriched_data = process_job(job, client)
                
                if not dry_run:
                    update_job_in_supabase(job_id, enriched_data)
                    
                success = True
                print(f"  [+] Success! Skills: {len(enriched_data['skills'])} | Role: {enriched_data['role_category']}")
                processed_count += 1
                break
            except Exception as e:
                print(f"  [!] Attempt {attempt+1}/{MAX_RETRIES} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    
        if not success:
            print(f"  [X] Skipped row {job_id} after {MAX_RETRIES} failures.")
            failure_count += 1

    print("\n" + "=" * 50)
    print("  ENRICHMENT PIPELINE SUMMARY")
    print("=" * 50)
    print(f"  Total records fetched:  {len(jobs)}")
    print(f"  Successfully processed: {processed_count}")
    print(f"  Failures skipped:       {failure_count}")
    
    if dry_run:
        print("\n  ** DRY RUN COMPLETED - NO DATA UPDATED IN SUPABASE **")
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrich Supabase mercor_jobs with embeddings and structured data.")
    parser.add_argument("--dry-run", action="store_true", help="Process without updating Supabase.")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of rows to process.")
    args = parser.parse_args()
    
    run_pipeline(dry_run=args.dry_run, limit=args.limit)
