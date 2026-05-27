import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def setup_scheduler() -> None:
    """Register all background jobs."""

    from app.services.cleanup import cleanup_expired_urls, cleanup_old_clicks

    # Run expired URL cleanup every hour
    scheduler.add_job(
        cleanup_expired_urls,
        trigger=IntervalTrigger(hours=1),
        id="cleanup_expired_urls",
        name="Cleanup Expired URLs",
        replace_existing=True,
        misfire_grace_time=60,
    )

    # Run old click cleanup every Sunday at 2am
    scheduler.add_job(
        cleanup_old_clicks,
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
        id="cleanup_old_clicks",
        name="Cleanup Old Click Records",
        replace_existing=True,
        misfire_grace_time=300,
    )

    logger.info("Scheduler jobs registered.")


def start_scheduler() -> None:
    setup_scheduler()
    scheduler.start()
    logger.info("Scheduler started.")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")