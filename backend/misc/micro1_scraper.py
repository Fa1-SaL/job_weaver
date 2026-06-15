import asyncio
import json
import httpx
from bs4 import BeautifulSoup
import re
import csv

AUTH_FILE = "micro1_auth.json"

def extract_token():
    try:
        with open(AUTH_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        for origin in state.get("origins", []):
            if origin.get("origin") == "https://refer.micro1.ai":
                for item in origin.get("localStorage", []):
                    if item["name"] == "auth_session":
                        auth_data = json.loads(item["value"])
                        return auth_data["token"]
    except Exception as e:
        print(f"Error extracting token from {AUTH_FILE}: {e}")
    return None

def strip_html(html_str):
    if not html_str:
        return ""
    soup = BeautifulSoup(html_str, "html.parser")
    # Add newlines for paragraphs and breaks to keep formatting clean
    for tag in soup.find_all(['p', 'div', 'br', 'li']):
        if tag.name == 'br':
            tag.replace_with('\n')
        elif tag.name == 'li':
            tag.insert(0, '- ')
            tag.append('\n')
        else:
            tag.append('\n\n')
    
    text = soup.get_text()
    # Clean up excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

async def fetch_job_description(client, job_id):
    url = f"https://jobs.micro1.ai/post/{job_id}"
    for attempt in range(3):
        try:
            resp = await client.get(url, timeout=15.0)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                job_html_div = soup.find('div', class_='job-html')
                if job_html_div:
                    return strip_html(str(job_html_div))
                
                # Fallback: JSON-LD Schema
                scripts = soup.find_all('script', type='application/ld+json')
                for script in scripts:
                    try:
                        data = json.loads(script.string)
                        if data.get('@type') == 'JobPosting' and 'description' in data:
                            return strip_html(data['description'])
                    except Exception:
                        pass
            return ""
        except Exception:
            await asyncio.sleep(2)
    return ""

async def main():
    token = extract_token()
    if not token:
        print(f"[X] Could not find auth token. Make sure {AUTH_FILE} is populated by running original interactive script.")
        return

    print("[*] Authentication token successfully loaded.")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Referer": "https://refer.micro1.ai/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    jobs_data = []
    
    async with httpx.AsyncClient(headers=headers) as client:
        page = 1
        limit = 50
        while True:
            url = f"https://prod-api.micro1.ai/api/v1/referral/portal/eligible-jobs?page={page}&limit={limit}"
            print(f"[*] Fetching page {page} of micro1 jobs API...")
            resp = await client.get(url, timeout=20.0)
            if resp.status_code != 200:
                print(f"[!] API returned status {resp.status_code}. Stopping pagination.")
                break
                
            data = resp.json()
            items = data.get("data", [])
            if not items:
                break
                
            jobs_data.extend(items)
            
            total = data.get("total", 0)
            if len(jobs_data) >= total:
                break
                
            page += 1
            await asyncio.sleep(1)

    print(f"[+] Total jobs found via API: {len(jobs_data)}")
    if not jobs_data:
        return
        
    print("[*] Extracting full job descriptions from public job pages...")
    results = []
    
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
    async with httpx.AsyncClient(limits=limits) as client:
        # We can run these concurrently for speed, but let's do batches
        batch_size = 10
        for i in range(0, len(jobs_data), batch_size):
            batch = jobs_data[i:i+batch_size]
            
            tasks = []
            for job in batch:
                tasks.append(fetch_job_description(client, job.get("job_id")))
                
            descriptions = await asyncio.gather(*tasks)
            
            for j, job in enumerate(batch):
                title = job.get("job_name", "Unknown Title")
                
                comp_min = None
                comp_max = None
                
                # Derive compensation
                if job.get("ideal_yearly_compensation") and isinstance(job["ideal_yearly_compensation"], dict):
                    comp_min = job["ideal_yearly_compensation"].get("min")
                    comp_max = job["ideal_yearly_compensation"].get("max")
                elif job.get("ideal_monthly_salary_min") or job.get("ideal_monthly_salary_max"):
                    try: comp_min = float(job.get("ideal_monthly_salary_min")) if job.get("ideal_monthly_salary_min") else None
                    except Exception: pass
                    try: comp_max = float(job.get("ideal_monthly_salary_max")) if job.get("ideal_monthly_salary_max") else None
                    except Exception: pass
                elif job.get("ideal_hourly_rate") and isinstance(job["ideal_hourly_rate"], dict):
                    comp_min = job["ideal_hourly_rate"].get("min")
                    comp_max = job["ideal_hourly_rate"].get("max")

                record = {
                    "Title": title.strip(),
                    "Min Compensation": comp_min,
                    "Max Compensation": comp_max,
                    "Referral Bonus": job.get("referral_reward_amount"),
                    "Referral Link": job.get("apply_url"),
                    "Number of Openings": job.get("no_of_openings"),
                    "Full Job Description": descriptions[j]
                }
                results.append(record)
                
            print(f"  [Processed {min(i+batch_size, len(jobs_data))}/{len(jobs_data)}] jobs...")
            
    output_file = "micro1_jobs.csv"
    keys = ["Title", "Min Compensation", "Max Compensation", "Referral Bonus", "Referral Link", "Number of Openings", "Full Job Description"]
    
    try:
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(results)
    except Exception as e:
        print(f"[!] Failed to save CSV: {e}")
        
    output_json = "micro1_jobs.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"\n[+] Successfully saved {len(results)} jobs to {output_file} and {output_json}!")

if __name__ == "__main__":
    asyncio.run(main())
