from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from playwright.async_api import async_playwright, Browser, Page, Playwright

from src.config import PRODUCT_CATALOG, Product, SCRAPE_CACHE_TTL_MINUTES

logger = logging.getLogger(__name__)


@dataclass
class ScrapedProduct:
    product_id: str
    name: str
    price: float
    in_stock: bool
    pack_info: str
    url: str


_cache: dict[str, tuple[float, ScrapedProduct]] = {}


def _cache_valid(product_id: str) -> ScrapedProduct | None:
    if product_id in _cache:
        ts, data = _cache[product_id]
        if time.time() - ts < SCRAPE_CACHE_TTL_MINUTES * 60:
            return data
    return None


class AmulScraper:
    def __init__(self) -> None:
        self._pw: Playwright | None = None
        self._browser: Browser | None = None

    async def start(self) -> None:
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=True)
        logger.info("Playwright browser started")

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
        logger.info("Playwright browser stopped")

    async def _new_page(self) -> Page:
        assert self._browser is not None
        context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        return await context.new_page()

    async def scrape_product(self, product: Product) -> ScrapedProduct:
        cached = _cache_valid(product.id)
        if cached:
            logger.debug("Cache hit for %s", product.id)
            return cached

        page = await self._new_page()
        try:
            logger.info("Scraping %s from %s", product.name, product.url)
            await page.goto(product.url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            price = 0.0
            in_stock = False

            # Try multiple selector strategies for price extraction
            for selector in [
                "[class*='price'] [class*='sale']",
                "[class*='price'] span",
                "[class*='Price']",
                "[class*='product-price']",
                "[data-testid*='price']",
                ".price",
            ]:
                try:
                    el = await page.query_selector(selector)
                    if el:
                        text = (await el.inner_text()).strip()
                        cleaned = "".join(
                            c for c in text if c.isdigit() or c == "."
                        )
                        if cleaned:
                            price = float(cleaned)
                            break
                except Exception:
                    continue

            # Fallback: scan full page text for price pattern
            if price == 0.0:
                try:
                    body_text = await page.inner_text("body")
                    import re

                    prices = re.findall(r"₹\s*([\d,]+(?:\.\d{2})?)", body_text)
                    if not prices:
                        prices = re.findall(r"Rs\.?\s*([\d,]+(?:\.\d{2})?)", body_text)
                    if prices:
                        price = float(prices[0].replace(",", ""))
                except Exception:
                    pass

            # Check stock status
            for stock_sel in [
                "[class*='add-to-cart']",
                "[class*='AddToCart']",
                "button:has-text('Add')",
                "button:has-text('add to')",
                "[class*='add-to-bag']",
            ]:
                try:
                    btn = await page.query_selector(stock_sel)
                    if btn and await btn.is_visible():
                        in_stock = True
                        break
                except Exception:
                    continue

            # If no add-to-cart button found, check for out-of-stock indicators
            if not in_stock:
                try:
                    body_text = await page.inner_text("body")
                    lower_text = body_text.lower()
                    if "out of stock" in lower_text or "sold out" in lower_text:
                        in_stock = False
                    elif "add" in lower_text and "cart" in lower_text:
                        in_stock = True
                except Exception:
                    pass

            result = ScrapedProduct(
                product_id=product.id,
                name=product.name,
                price=price,
                in_stock=in_stock,
                pack_info=product.pack_info,
                url=product.url,
            )

            _cache[product.id] = (time.time(), result)
            logger.info(
                "Scraped %s: price=%.2f, in_stock=%s",
                product.name,
                price,
                in_stock,
            )
            return result

        except Exception as exc:
            logger.error("Failed to scrape %s: %s", product.name, exc)
            return ScrapedProduct(
                product_id=product.id,
                name=product.name,
                price=0.0,
                in_stock=False,
                pack_info=product.pack_info,
                url=product.url,
            )
        finally:
            ctx = page.context
            await page.close()
            await ctx.close()

    async def scrape_all(self) -> list[ScrapedProduct]:
        results: list[ScrapedProduct] = []
        for product in PRODUCT_CATALOG.values():
            result = await self.scrape_product(product)
            results.append(result)
            await asyncio.sleep(1)  # polite delay between requests
        return results

    def clear_cache(self) -> None:
        _cache.clear()
