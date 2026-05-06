from __future__ import annotations

import asyncio
import logging

from playwright.async_api import Browser, Page

from src.config import PRODUCT_CATALOG, SHOP_BASE_URL

logger = logging.getLogger(__name__)


class CartManager:
    """Manages the add-to-cart flow on shop.amul.com using a shared browser."""

    def __init__(self, browser: Browser) -> None:
        self._browser = browser

    async def _new_page(self) -> Page:
        context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        return await context.new_page()

    async def add_to_cart_and_get_checkout_url(
        self,
        items: dict[str, int],
    ) -> tuple[str, list[str]]:
        """Add products to cart and return (checkout_url, list_of_errors).

        Args:
            items: mapping of product_id -> quantity

        Returns:
            (checkout_url, errors) where checkout_url may be a direct link
            to the shop if automation fails.
        """
        page = await self._new_page()
        errors: list[str] = []
        added_count = 0

        try:
            for product_id, qty in items.items():
                product = PRODUCT_CATALOG.get(product_id)
                if not product:
                    errors.append(f"Unknown product: {product_id}")
                    continue

                try:
                    success = await self._add_single_product(page, product.url, qty)
                    if success:
                        added_count += 1
                        logger.info("Added %s x%d to cart", product.name, qty)
                    else:
                        errors.append(f"Could not add {product.short_name} to cart")
                except Exception as exc:
                    logger.error("Error adding %s: %s", product.name, exc)
                    errors.append(f"Error adding {product.short_name}: {str(exc)[:80]}")

                await asyncio.sleep(1)

            if added_count > 0:
                checkout_url = await self._navigate_to_checkout(page)
            else:
                checkout_url = SHOP_BASE_URL + "/en"

            return checkout_url, errors

        except Exception as exc:
            logger.error("Cart flow failed: %s", exc)
            errors.append(f"Cart flow failed: {str(exc)[:100]}")
            return SHOP_BASE_URL + "/en", errors

        finally:
            ctx = page.context
            await page.close()
            await ctx.close()

    async def _add_single_product(
        self, page: Page, product_url: str, qty: int
    ) -> bool:
        await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        add_btn = None
        for selector in [
            "button:has-text('Add to Cart')",
            "button:has-text('Add to Bag')",
            "button:has-text('ADD TO CART')",
            "button:has-text('Add')",
            "[class*='add-to-cart'] button",
            "[class*='AddToCart']",
            "[data-testid*='add-to-cart']",
        ]:
            try:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    add_btn = btn
                    break
            except Exception:
                continue

        if not add_btn:
            return False

        # Click add-to-cart for the required quantity
        for i in range(qty):
            await add_btn.click()
            await page.wait_for_timeout(1000)

            # After first click, might need to click "+" for subsequent items
            if i == 0 and qty > 1:
                plus_btn = None
                for sel in [
                    "button:has-text('+')",
                    "[class*='increment']",
                    "[class*='plus']",
                    "[aria-label='Increase quantity']",
                ]:
                    try:
                        btn = await page.query_selector(sel)
                        if btn and await btn.is_visible():
                            plus_btn = btn
                            break
                    except Exception:
                        continue

                if plus_btn:
                    for _ in range(qty - 1):
                        await plus_btn.click()
                        await page.wait_for_timeout(500)
                    break

        return True

    async def _navigate_to_checkout(self, page: Page) -> str:
        # Try navigating to cart/checkout page
        for cart_sel in [
            "[class*='cart'] a",
            "a[href*='cart']",
            "[class*='Cart']",
            "button:has-text('Cart')",
            "[class*='bag-icon']",
            "a[href*='bag']",
        ]:
            try:
                el = await page.query_selector(cart_sel)
                if el and await el.is_visible():
                    await el.click()
                    await page.wait_for_timeout(2000)
                    break
            except Exception:
                continue

        current_url = page.url

        # Try clicking checkout/proceed button
        for checkout_sel in [
            "button:has-text('Checkout')",
            "button:has-text('Proceed')",
            "a:has-text('Checkout')",
            "a:has-text('Proceed')",
            "[class*='checkout']",
        ]:
            try:
                el = await page.query_selector(checkout_sel)
                if el and await el.is_visible():
                    await el.click()
                    await page.wait_for_timeout(2000)
                    current_url = page.url
                    break
            except Exception:
                continue

        return current_url

    async def get_direct_cart_links(
        self, items: dict[str, int]
    ) -> list[tuple[str, str, int]]:
        """Fallback: return direct product links for manual ordering.

        Returns list of (product_name, url, quantity).
        """
        links = []
        for product_id, qty in items.items():
            product = PRODUCT_CATALOG.get(product_id)
            if product:
                links.append((product.short_name, product.url, qty))
        return links
