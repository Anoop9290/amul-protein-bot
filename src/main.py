from __future__ import annotations

import logging
import sys

from telegram.ext import Application

from src.config import TELEGRAM_BOT_TOKEN
from src.bot.handlers import get_all_handlers
from src.db.database import Database
from src.scheduler.jobs import register_jobs
from src.scraper.amul_scraper import AmulScraper

logging.basicConfig(
    format="%(asctime)s | %(name)-28s | %(levelname)-7s | %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("playwright").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def post_init(app: Application) -> None:
    """Initialize shared resources after the Application is built."""
    db = Database()
    await db.init()

    scraper = AmulScraper()
    await scraper.start()

    app.bot_data["db"] = db
    app.bot_data["scraper"] = scraper

    logger.info("Bot resources initialized")


async def post_shutdown(app: Application) -> None:
    """Clean up shared resources on shutdown."""
    scraper: AmulScraper | None = app.bot_data.get("scraper")
    if scraper:
        await scraper.stop()
    logger.info("Bot resources cleaned up")


def main() -> None:
    token_preview = TELEGRAM_BOT_TOKEN[:10] + "..." if TELEGRAM_BOT_TOKEN else "(empty)"
    logger.info("Token check: %s", token_preview)

    if not TELEGRAM_BOT_TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN not set. "
            "Set it as an environment variable or in a .env file."
        )
        sys.exit(1)

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    for handler in get_all_handlers():
        app.add_handler(handler)

    register_jobs(app)

    logger.info("Starting Amul Protein Tracker...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
