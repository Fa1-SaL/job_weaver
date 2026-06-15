import httpx
import json

def test_jbo():
    # Try fetching public API for the job details if it exists
    url = "https://prod-api.micro1.ai/api/v1/job/18d2124d-9cc1-472c-968f-5db976f09029"
    try:
        r = httpx.get(url, timeout=10)
        print("API Status:", r.status_code)
        if r.status_code == 200:
            print("API Returns JSON:", list(r.json().keys()))
            with open("temp_job.json", "w") as f:
                json.dump(r.json(), f, indent=2)
            return
    except Exception as e:
        print("API Error:", e)

    # If API fails, fetch HTML
    url2 = "https://jobs.micro1.ai/post/18d2124d-9cc1-472c-968f-5db976f09029"
    r = httpx.get(url2, timeout=10)
    print("HTML Status:", r.status_code)
    html = r.text
    with open("temp_job.html", "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    test_jbo()
