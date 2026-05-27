import logging
from datetime import datetime, timezone

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.url import URL
from app.models.click import Click
from app.services.cache import CacheService
from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)


async def cleanup_expired_urls() -> None:
    """
    Runs on a schedule:
    1. Finds all expired active URLs
    2. Marks them inactive
    3. Clears them from Redis cache
    """
    logger.info("Running expired URL cleanup job...")

    async with AsyncSessionLocal() as db:
        try:
            # Find expired URLs that are still active
            stmt = select(URL).where(
                URL.is_active == True,
                URL.expires_at.isnot(None),
                URL.expires_at <= datetime.now(timezone.utc),
            )
            result = await db.execute(stmt)
            expired_urls = result.scalars().all()

            if not expired_urls:
                logger.info("No expired URLs found.")
                return

            redis = get_redis_client()
            cache = CacheService(redis=redis)

            for url_obj in expired_urls:
                # Deactivate in DB
                url_obj.is_active = False
                # Remove from cache
                await cache.delete_url(url_obj.short_code)
                logger.info(f"Expired URL deactivated: {url_obj.short_code}")

            await db.commit()
            logger.info(f"Cleanup complete — {len(expired_urls)} URLs deactivated.")

        except Exception as e:
            await db.rollback()
            logger.error(f"Cleanup job failed: {e}")


async def cleanup_old_clicks(days: int = 90) -> None:
    """
    Optional: delete click events older than X days to keep DB lean.
    Runs weekly.
    """
    logger.info(f"Running old click cleanup (older than {days} days)...")

    async with AsyncSessionLocal() as db:
        try:
            from datetime import timedelta
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            stmt = delete(Click).where(Click.clicked_at < cutoff)
            result = await db.execute(stmt)
            await db.commit()

            logger.info(f"Deleted {result.rowcount} old click records.")

        except Exception as e:
            await db.rollback()
            logger.error(f"Click cleanup job failed: {e}")