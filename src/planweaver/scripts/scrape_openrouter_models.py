"""
Script to scrape free models from OpenRouter using Playwright.
Run manually: uv run python -m planweaver.scripts.scrape_openrouter_models
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page
from sqlalchemy.exc import IntegrityError

from ..db.database import get_session
from ..db.models import AvailableModel

logger = logging.getLogger(__name__)


class OpenRouterScraper:
    """Scraper for OpenRouter free models page."""

    FREE_MODELS_URL = "https://openrouter.ai/collections/free-models"
    MODELS_URL = "https://openrouter.ai/models"

    def __init__(self, timeout_ms: int = 30000):
        self.timeout_ms = timeout_ms

    async def scrape_free_models(self) -> List[Dict[str, Any]]:
        """Scrape free models from OpenRouter.

        Returns:
            List of model dictionaries with keys: model_id, name, provider, is_free
        """
        models = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                logger.info(f"Navigating to {self.FREE_MODELS_URL}")
                await page.goto(self.FREE_MODELS_URL, wait_until="networkidle", timeout=self.timeout_ms)
                await asyncio.sleep(2)  # Wait for dynamic content

                # Extract model data using JavaScript
                models_data = await page.evaluate("""
                    () => {
                        const models = [];
                        const modelLinks = document.querySelectorAll('a[href$=":free"]');

                        modelLinks.forEach(link => {
                            const href = link.getAttribute('href');
                            const modelText = link.querySelector('h3')?.textContent || link.textContent.trim();

                            // Extract provider from href (e.g., "arcee-ai" from "/arcee-ai/trinity-large-preview:free")
                            const hrefParts = href.split('/');
                            const provider = hrefParts[1] || 'unknown';

                            // Extract model_id (remove leading slash)
                            const modelId = href.startsWith('/') ? href.substring(1) : href;

                            models.push({
                                model_id: modelId,
                                name: modelText,
                                provider: provider,
                                is_free: true
                            });
                        });

                        return models;
                    }
                """)

                models = models_data
                logger.info(f"Found {len(models)} free models")

            except Exception as e:
                logger.error(f"Error during scraping: {e}")
                raise
            finally:
                await browser.close()

        return models

    def save_models(self, models: List[Dict[str, Any]]) -> Dict[str, int]:
        """Save scraped models to database.

        Args:
            models: List of model dictionaries

        Returns:
            Dictionary with counts: created, updated, failed
        """
        session = get_session()
        stats = {"created": 0, "updated": 0, "failed": 0}

        for model_data in models:
            try:
                # Default type to 'both' for all models (can be manually updated later)
                model_data.setdefault("type", "both")
                model_data["pricing_info"] = None
                model_data["context_length"] = None
                model_data["is_active"] = True

                existing = session.query(AvailableModel).filter_by(
                    model_id=model_data["model_id"]
                ).first()

                if existing:
                    # Update existing model
                    for key, value in model_data.items():
                        setattr(existing, key, value)
                    existing.last_updated = datetime.now(timezone.utc)
                    stats["updated"] += 1
                    logger.debug(f"Updated model: {model_data['model_id']}")
                else:
                    # Create new model
                    db_model = AvailableModel(**model_data)
                    session.add(db_model)
                    stats["created"] += 1
                    logger.debug(f"Created model: {model_data['model_id']}")

                session.commit()

            except IntegrityError as e:
                logger.warning(f"Integrity error for model {model_data.get('model_id')}: {e}")
                session.rollback()
                stats["failed"] += 1
            except Exception as e:
                logger.error(f"Failed to save model {model_data.get('model_id')}: {e}")
                session.rollback()
                stats["failed"] += 1

        session.close()
        return stats


async def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    scraper = OpenRouterScraper()

    logger.info("Starting OpenRouter free models scrape...")
    try:
        models = await scraper.scrape_free_models()
        logger.info(f"Scraped {len(models)} free models")

        stats = scraper.save_models(models)
        logger.info(f"Save results: {stats}")

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
