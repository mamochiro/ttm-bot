#!/usr/bin/env python3
import argparse
import asyncio
import logging
import sys
from typing import Optional
from playwright.async_api import async_playwright, BrowserContext, Page
from config.settings import Settings
from modules.auth import AuthModule
from modules.booking import BookingModule
from modules.seat_selector import SeatSelectorModule
from modules.payment import PaymentModule
from utils.captcha import CaptchaHandler
from utils.proxy import ProxyManager
from utils.logger import get_logger, setup_logging

log = get_logger("main")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TTM Concert Ticket Bot")
    parser.add_argument("-c", "--config", help="Path to config.yaml", default=None)
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--workers", type=int, default=None, help="Number of parallel workers")
    parser.add_argument("--url", help="Concert URL override")
    parser.add_argument("--tickets", type=int, help="Number of tickets override")
    parser.add_argument("--zones", help="Comma-separated zone list override")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args()


async def run_worker(
    worker_id: int,
    settings: Settings,
    proxy_manager: Optional[ProxyManager],
) -> bool:
    proxy = proxy_manager.get_next() if proxy_manager and proxy_manager.has_proxies else None

    async with async_playwright() as pw:
        browser_opts = {
            "headless": settings.bot.headless,
            "args": ["--no-sandbox", "--disable-dev-shm-usage"],
        }
        if proxy:
            browser_opts["proxy"] = proxy
            log.info(f"[Worker {worker_id}] Using proxy: {proxy['server']}")

        browser = await pw.chromium.launch(**browser_opts)
        context: BrowserContext = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="th-TH",
        )
        context.set_default_timeout(settings.bot.timeout)
        page: Page = await context.new_page()

        # Log console errors for debugging
        page.on("console", lambda msg: log.debug(f"[Browser] {msg.type}: {msg.text}") if msg.type == "error" else None)

        auth = AuthModule(settings, worker_id=worker_id)
        seat_selector = SeatSelectorModule(settings)
        payment = PaymentModule(settings)
        captcha = CaptchaHandler(
            mode=settings.captcha.mode,
            api_key=settings.captcha.api_key,
            timeout=settings.captcha.timeout,
        )

        booking = BookingModule(
            settings=settings,
            auth=auth,
            seat_selector=seat_selector,
            payment=payment,
            captcha=captcha,
            worker_id=worker_id,
        )

        try:
            result = await booking.run(page, context)
            return result
        finally:
            await browser.close()


async def main() -> int:
    args = parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO

    settings = Settings(config_path=args.config)

    setup_logging(log_dir=settings.log_dir, level=log_level)

    # Apply CLI overrides
    if args.headless:
        settings.bot.headless = True
    if args.workers is not None:
        if args.workers < 1:
            log.error("--workers must be >= 1")
            return 1
        settings.workers = args.workers
    if args.url:
        settings.concert.url = args.url
    if args.tickets:
        settings.ticket.num_tickets = args.tickets
    if args.zones:
        settings.ticket.preferred_zones = [z.strip() for z in args.zones.split(",")]

    try:
        settings.validate()
    except ValueError as e:
        log.error(str(e))
        return 1

    log.info("=" * 60)
    log.info("TTM Concert Ticket Bot")
    log.info(f"  Concert : {settings.concert.url or settings.concert.name}")
    log.info(f"  Tickets : {settings.ticket.num_tickets}")
    log.info(f"  Zones   : {', '.join(settings.ticket.preferred_zones) or 'any'}")
    log.info(f"  Workers : {settings.workers}")
    log.info(f"  Headless: {settings.bot.headless}")
    log.info("=" * 60)

    proxy_manager = None
    if settings.proxy.enabled:
        proxy_manager = ProxyManager(proxy_file=settings.proxy.file)

    if settings.workers == 1:
        success = await run_worker(0, settings, proxy_manager)
        return 0 if success else 1

    # Multi-worker mode
    tasks = [
        asyncio.create_task(run_worker(i, settings, proxy_manager))
        for i in range(settings.workers)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    any_success = any(r is True for r in results)

    if any_success:
        log.info("At least one worker succeeded!")
        return 0
    else:
        log.error("All workers failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
