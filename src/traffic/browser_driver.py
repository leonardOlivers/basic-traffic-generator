thonfrom __future__ import annotations

from typing import Optional, Tuple

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright
import logging

class BrowserDriver:
    def __init__(self, headless: bool = True, logger: Optional[logging.Logger] = None) -> None:
        self.headless = headless
        self.logger = logger or logging.getLogger("browser-driver")
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    async def __aenter__(self) -> "BrowserDriver":
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self.logger.info("Launched Chromium browser (headless=%s).", self.headless)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._browser:
            await self._browser.close()
            self.logger.info("Browser closed.")
        if self._playwright:
            await self._playwright.stop()
            self.logger.info("Playwright stopped.")

    async def new_page(self) -> Tuple[BrowserContext, Page]:
        if not self._browser:
            raise RuntimeError("Browser not initialized. Use 'async with BrowserDriver(...)'.")
        context = await self._browser.new_context()
        page = await context.new_page()
        return context, page