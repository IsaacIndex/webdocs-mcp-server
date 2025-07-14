"""
playwright_scrape.py
Scrapes a single page: prints title, grabs some text,
and saves the final HTML to disk.
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

TARGET_URL = "https://www.cnbc.com/world/?region=worldm"   # <-- change me!

async def scrape(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, timeout=30_000)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")  # wait for JS & XHR
        title = await page.title()
        body_text = await page.locator("body").inner_text()   # selector demo
        print(f"Title: {title}\nH1  : {body_text}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape(TARGET_URL))