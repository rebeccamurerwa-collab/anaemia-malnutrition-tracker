"""
APScheduler — runs weekly PIB scrape + Gmail fetch
every Monday at 06:00 UTC.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

logger = logging.getLogger(__name__)


def weekly_job():
    logger.info("[scheduler] Starting weekly scrape job …")
    try:
        from scraper import run_full_scrape
        n = run_full_scrape(pages_per_ministry=3)
        logger.info(f"[scheduler] Scrape done: {n} records")
    except Exception as e:
        logger.error(f"[scheduler] Scrape failed: {e}")

    try:
        from gmail_reader import fetch_gmail_alerts
        m = fetch_gmail_alerts()
        logger.info(f"[scheduler] Gmail done: {m} records")
    except Exception as e:
        logger.error(f"[scheduler] Gmail fetch failed: {e}")


def start_scheduler():
    scheduler = BackgroundScheduler()
    # Every Monday at 06:00 UTC
    scheduler.add_job(
        weekly_job,
        CronTrigger(day_of_week="mon", hour=3, minute=0),
        id="weekly_scrape",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[scheduler] Weekly scrape scheduled (Mon 06:00 UTC)")