import asyncio
import json
from playwright.async_api import async_playwright

AUTH_FILE = "micro1_auth.json"

async def main():
    async with async_playwright() as p:
        print("[*] Launching browser...")
        browser = await p.chromium.launch(headless=False)
        try:
            context = await browser.new_context(storage_state=AUTH_FILE)
            print("[*] Loaded existing auth state.")
        except Exception:
            context = await browser.new_context()

        page = await context.new_page()
        
        api_responses = {}
        async def handle_response(response):
            if "api" in response.url and response.request.resource_type in ["fetch", "xhr"]:
                try:
                    data = await response.json()
                    api_responses[response.url] = data
                except Exception:
                    pass
        page.on("response", handle_response)

        print("[*] Navigating to https://refer.micro1.ai/opportunities")
        await page.goto("https://refer.micro1.ai/opportunities")

        if "login" in page.url:
            print("\n" + "="*50)
            print("  [!] PLEASE LOG IN MANUALLY IN THE BROWSER WINDOW")
            print("  The script will pause until you successfully log in.")
            print("="*50 + "\n")
            
            # Wait for user to login and redirect back to opportunities
            await page.wait_for_url("**/opportunities*", timeout=0)
            
            print("[+] Logged in! Saving authentication state...")
            await context.storage_state(path=AUTH_FILE)
        
        print("[*] On opportunities page. Waiting 5 seconds for jobs to load...")
        await page.wait_for_timeout(5000)

        # Scroll down to trigger any lazy loading
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(3000)

        print("[*] Capturing page HTML and API responses...")
        html = await page.content()
        with open("micro1_opportunities.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        with open("micro1_api_dump.json", "w", encoding="utf-8") as f:
            json.dump(api_responses, f, indent=2)

        print("[+] Finished capturing data! The AI assistant will now analyze it and build the scraper.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
