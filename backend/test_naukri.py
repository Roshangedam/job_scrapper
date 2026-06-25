import asyncio
from playwright.async_api import async_playwright

async def test_naukri():
    print("Testing Naukri with different Playwright settings...")
    async with async_playwright() as p:
        
        # Test 1: Real Chrome (Headless)
        print("\n--- Test 1: Real Chrome (Headless) ---")
        try:
            browser = await p.chromium.launch(
                channel="chrome",  # Uses the machine's strict Chrome installation
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            )
            await page.goto('https://www.naukri.com/java-developer-jobs-in-pune', wait_until='networkidle')
            title = await page.title()
            links = await page.evaluate("() => document.querySelectorAll('a[href*=\"job-listings\"]').length")
            print(f"Title: {title}, Links found: {links}")
            await browser.close()
        except Exception as e:
            print(f"Test 1 Failed: {e}")

        # Test 2: Real Chrome (Non-Headless)
        print("\n--- Test 2: Real Chrome (Non-Headless) ---")
        try:
            browser = await p.chromium.launch(
                channel="chrome",
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            )
            await page.goto('https://www.naukri.com/java-developer-jobs-in-pune', wait_until='networkidle')
            title = await page.title()
            links = await page.evaluate("() => document.querySelectorAll('a[href*=\"job-listings\"]').length")
            print(f"Title: {title}, Links found: {links}")
            await browser.close()
        except Exception as e:
            print(f"Test 2 Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_naukri())
