thonfrom __future__ import annotations

import random
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import logging
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

class ActionSimulator:
    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or logging.getLogger("action-simulator")

    async def simulate(self, page: Page, url: str, max_interactions: int = 10) -> Dict[str, Any]:
        interactions = 0
        status_code: Optional[int] = None
        start = time.monotonic()
        try:
            response = await page.goto(url, wait_until="networkidle", timeout=30000)
            if response is not None:
                status_code = response.status
            interactions += 1
            await page.wait_for_timeout(1000)

            scroll_steps = max(1, max_interactions // 2)
            for _ in range(scroll_steps):
                delta_y = random.randint(200, 800)
                await page.mouse.wheel(0, delta_y)
                interactions += 1
                await page.wait_for_timeout(random.randint(300, 700))

            try:
                elements = await page.query_selector_all("a, button")
                random.shuffle(elements)
                for element in elements:
                    if interactions >= max_interactions:
                        break
                    try:
                        await element.scroll_into_view_if_needed(timeout=2000)
                        await element.click(timeout=3000)
                        interactions += 1
                        await page.wait_for_timeout(random.randint(300, 800))
                    except PlaywrightTimeoutError:
                        continue
                    except Exception:
                        continue
            except Exception as exc:  # pragma: no cover - non-critical
                self.logger.debug("Error during click interactions on %s: %s", url, exc)

        except PlaywrightTimeoutError as exc:
            self.logger.warning("Timeout while loading %s: %s", url, exc)
        except Exception as exc:
            self.logger.error("Unexpected error while simulating actions for %s: %s", url, exc)
        finally:
            response_time = round(time.monotonic() - start, 3)

        record: Dict[str, Any] = {
            "url": url,
            "status_code": status_code if status_code is not None else -1,
            "response_time": response_time,
            "interactions": interactions,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return record