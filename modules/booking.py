import asyncio
import subprocess
import time
from datetime import datetime
from typing import Optional
from playwright.async_api import Page, BrowserContext
from config.settings import Settings
from modules.auth import AuthModule
from modules.seat_selector import SeatSelectorModule
from modules.payment import PaymentModule
from utils.captcha import CaptchaHandler
from utils.logger import get_logger

log = get_logger(__name__)

TTM_BASE_URL = "https://www.thaiticketmajor.com"


class BookingModule:
    def __init__(
        self,
        settings: Settings,
        auth: AuthModule,
        seat_selector: SeatSelectorModule,
        payment: PaymentModule,
        captcha: CaptchaHandler,
        worker_id: int = 0,
    ):
        self.settings = settings
        self.auth = auth
        self.seat_selector = seat_selector
        self.payment = payment
        self.captcha = captcha
        self.worker_id = worker_id

    async def run(self, page: Page, context: BrowserContext) -> bool:
        cfg = self.settings
        retries = 0
        max_retries = cfg.bot.max_retries

        if not await self.auth.ensure_logged_in(page, context):
            log.error("Authentication failed")
            return False

        while retries <= max_retries:
            try:
                concert_url = await self._navigate_to_concert(page)
                if not concert_url:
                    log.error("Could not navigate to concert page")
                    return False

                await self._handle_captcha(page)

                if not await self._handle_queue(page):
                    log.warning("Queue handling failed or timed out")

                await self._handle_captcha(page)

                if not await self._select_show(page):
                    log.error("Show/date selection failed")
                    await self._screenshot(page, "select_show_failed")
                    raise RuntimeError("Show selection failed")

                if not await self.seat_selector.select_zone(page):
                    log.error("Zone selection failed")
                    await self._screenshot(page, "zone_failed")
                    raise RuntimeError("Zone selection failed")

                await self.seat_selector.set_ticket_count(page)

                if not await self.seat_selector.select_specific_seats(page):
                    log.error("Seat selection failed")
                    await self._screenshot(page, "seat_failed")
                    raise RuntimeError("Seat selection failed")

                await self._screenshot(page, f"seats_selected_{self.worker_id}")

                if not await self._proceed_to_checkout(page):
                    log.error("Could not proceed to checkout")
                    raise RuntimeError("Checkout navigation failed")

                await self._handle_captcha(page)
                await self.payment.fill_buyer_info(page)
                await self.payment.select_payment_method(page)

                await self._screenshot(page, f"pre_confirm_{self.worker_id}", is_error=False)

                if not await self.payment.confirm_order(page):
                    log.error("Order confirmation failed")
                    raise RuntimeError("Order confirmation failed")

                success = await self.payment.wait_for_payment_complete(page)

                if success:
                    await self._screenshot(page, f"success_{self.worker_id}", is_error=False)
                    await self._notify_success(page)
                    log.info(f"[Worker {self.worker_id}] BOOKING SUCCESSFUL!")
                    return True
                else:
                    log.error("Payment did not complete successfully")
                    await self._screenshot(page, f"payment_incomplete_{self.worker_id}")
                    raise RuntimeError("Payment incomplete")

            except RuntimeError as e:
                retries += 1
                if retries > max_retries:
                    log.error(f"Max retries reached: {e}")
                    await self._screenshot(page, f"max_retries_reached_{self.worker_id}")
                    return False

                delay = cfg.bot.retry_delay * (2 ** (retries - 1))
                log.warning(f"Retry {retries}/{max_retries} in {delay}s: {e}")
                await asyncio.sleep(delay)

            except Exception as e:
                log.error(f"Unexpected error: {e}", exc_info=True)
                await self._screenshot(page, f"unexpected_error_{self.worker_id}")
                retries += 1
                if retries > max_retries:
                    return False
                await asyncio.sleep(cfg.bot.retry_delay)

        return False

    async def _navigate_to_concert(self, page: Page) -> Optional[str]:
        url = self.settings.concert.url
        if url:
            log.info(f"Navigating to concert URL: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=self.settings.bot.timeout)
            return url

        name = self.settings.concert.name
        if name:
            log.info(f"Searching for concert: {name}")
            search_url = f"{TTM_BASE_URL}/search/?keyword={name}"
            await page.goto(search_url, wait_until="domcontentloaded")
            try:
                result = await page.wait_for_selector(
                    f".concert-item:has-text('{name}') a, "
                    f".event-list a:has-text('{name}')",
                    timeout=10000,
                )
                href = await result.get_attribute("href")
                if href:
                    concert_url = href if href.startswith("http") else f"{TTM_BASE_URL}{href}"
                    await page.goto(concert_url, wait_until="domcontentloaded")
                    log.info(f"Found concert: {concert_url}")
                    return concert_url
            except Exception:
                log.error(f"Concert '{name}' not found in search results")
                return None

        log.error("No concert URL or name configured")
        return None

    async def _handle_queue(self, page: Page) -> bool:
        queue_selectors = [
            ".queue-page, #queue-container, .waiting-room",
            "h1:has-text('คิว'), h1:has-text('Queue'), h1:has-text('Waiting')",
            ".queue-position, #queue-number",
        ]
        is_in_queue = False
        for sel in queue_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    is_in_queue = True
                    break
            except Exception:
                pass

        if not is_in_queue:
            return True

        log.info("In queue — waiting for access...")
        check_interval = self.settings.bot.check_interval
        start_time = time.time()
        max_wait = 3600  # 1 hour

        while time.time() - start_time < max_wait:
            queue_still_visible = False
            for sel in queue_selectors:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        queue_still_visible = True
                        break
                except Exception:
                    pass

            if not queue_still_visible:
                log.info("Left queue! Proceeding with booking...")
                return True

            try:
                pos_el = await page.query_selector(".queue-position, #your-position, .position-number")
                if pos_el:
                    pos_text = await pos_el.inner_text()
                    elapsed = int(time.time() - start_time)
                    log.info(f"Queue position: {pos_text.strip()} | Waited: {elapsed}s")
            except Exception:
                pass

            await asyncio.sleep(check_interval)
            try:
                await page.reload(wait_until="domcontentloaded")
            except Exception:
                pass

        log.warning("Queue wait timeout after 1 hour")
        return False

    async def _select_show(self, page: Page) -> bool:
        return await self.seat_selector.select_date(page)

    async def _proceed_to_checkout(self, page: Page) -> bool:
        log.info("Proceeding to checkout...")
        selectors = [
            "button:has-text('ดำเนินการต่อ'), button:has-text('Continue'), button:has-text('ถัดไป')",
            "a:has-text('ดำเนินการต่อ'), a:has-text('Checkout'), a:has-text('ซื้อบัตร')",
            ".btn-next, .btn-continue, .btn-checkout, #btn-next",
            "input[type='submit'][value*='ต่อ']",
        ]
        for sel in selectors:
            try:
                btn = await page.wait_for_selector(sel, timeout=5000)
                await btn.click()
                await page.wait_for_load_state("networkidle", timeout=15000)
                log.info("Navigated to checkout")
                return True
            except Exception:
                continue

        log.warning("No checkout button found, may already be on checkout page")
        return True

    async def _screenshot(self, page: Page, name: str, is_error: bool = True) -> None:
        cfg = self.settings.bot
        if is_error and not cfg.screenshot_on_error:
            return
        if not is_error and not cfg.screenshot_on_success:
            return
        try:
            ts = datetime.now().strftime("%H%M%S")
            path = self.settings.screenshot_dir / f"{name}_{ts}.png"
            await page.screenshot(path=str(path), full_page=True)
            log.debug(f"Screenshot: {path}")
        except Exception:
            pass

    async def _handle_captcha(self, page: Page) -> None:
        try:
            visible = await page.is_visible(
                "iframe[src*='recaptcha'], .g-recaptcha, #captcha",
                timeout=1000,
            )
        except Exception:
            visible = False

        if not visible:
            return

        log.warning("Captcha detected")
        site_key = ""
        try:
            el = await page.query_selector(".g-recaptcha[data-sitekey]")
            if el:
                site_key = await el.get_attribute("data-sitekey") or ""
        except Exception:
            pass

        token = await self.captcha.solve(page, site_key=site_key, page_url=page.url)
        if token and token != "manual_solved" and site_key:
            await self.captcha.inject_recaptcha_token(page, token)

    async def _notify_success(self, page: Page) -> None:
        url = page.url
        webhook = self.settings.notifications.webhook_url

        if webhook:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        webhook,
                        json={
                            "text": f"Booking SUCCESS! Worker {self.worker_id}",
                            "url": url,
                        },
                        timeout=aiohttp.ClientTimeout(total=10),
                    )
                log.info("Webhook notification sent")
            except Exception as e:
                log.warning(f"Webhook failed: {e}")

        if self.settings.notifications.sound:
            self._play_sound()

    @staticmethod
    def _play_sound() -> None:
        try:
            subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], timeout=3)
        except Exception:
            try:
                subprocess.run(["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"], timeout=3)
            except Exception:
                log.debug("Could not play sound alert")
