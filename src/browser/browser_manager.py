from contextlib import contextmanager
from collections.abc import Iterator

from playwright.sync_api import Browser, Page, Playwright, sync_playwright


@contextmanager
def open_page(browser_name: str, headless: bool) -> Iterator[Page]:
    with sync_playwright() as playwright:
        browser_type = getattr(playwright, browser_name)
        browser: Browser = browser_type.launch(headless=headless)
        try:
            yield browser.new_page()
        finally:
            browser.close()
