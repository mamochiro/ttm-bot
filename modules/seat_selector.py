import asyncio
from typing import Optional, List
from playwright.async_api import Page
from config.settings import Settings
from utils.logger import get_logger

log = get_logger(__name__)


class SeatSelectorModule:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def select_date(self, page: Page) -> bool:
        if not self.settings.ticket.preferred_dates:
            log.info("No preferred dates set, selecting first available")
            return await self._click_first_available_date(page)

        for date_str in self.settings.ticket.preferred_dates:
            log.info(f"Trying date: {date_str}")
            selector = f"[data-date='{date_str}'], .show-date:has-text('{date_str}'), td[data-date='{date_str}']"
            try:
                el = await page.wait_for_selector(selector, timeout=5000)
                is_available = await el.get_attribute("class") or ""
                if "disabled" in is_available or "sold-out" in is_available:
                    log.warning(f"Date {date_str} is not available")
                    continue
                await el.click()
                log.info(f"Selected date: {date_str}")
                await page.wait_for_load_state("networkidle", timeout=10000)
                return True
            except Exception:
                log.warning(f"Date element not found for: {date_str}")

        return await self._click_first_available_date(page)

    async def _click_first_available_date(self, page: Page) -> bool:
        try:
            selectors = [
                ".show-date:not(.disabled):not(.sold-out)",
                "td.available[data-date]",
                ".calendar-day:not(.disabled)",
            ]
            for sel in selectors:
                el = await page.query_selector(sel)
                if el:
                    await el.click()
                    log.info("Selected first available date")
                    await page.wait_for_load_state("networkidle", timeout=10000)
                    return True
        except Exception as e:
            log.error(f"Could not select any date: {e}")
        return False

    async def select_zone(self, page: Page) -> bool:
        zones = self.settings.ticket.preferred_zones
        if not zones:
            log.info("No preferred zones set, selecting first available")
            return await self._click_first_available_zone(page)

        for zone in zones:
            log.info(f"Trying zone: {zone}")
            selectors = [
                f".zone-{zone.lower()}:not(.disabled):not(.sold-out)",
                f"[data-zone='{zone}']:not(.disabled)",
                f".seat-zone:has-text('{zone}'):not(.disabled)",
                f"area[title*='{zone}']",
                f"a:has-text('{zone}'):not([class*='disabled'])",
            ]
            for sel in selectors:
                try:
                    el = await page.wait_for_selector(sel, timeout=3000)
                    if el:
                        await el.click()
                        log.info(f"Selected zone: {zone}")
                        await page.wait_for_load_state("networkidle", timeout=10000)
                        return True
                except Exception:
                    continue
            log.warning(f"Zone {zone} not found or unavailable")

        return await self._click_first_available_zone(page)

    async def _click_first_available_zone(self, page: Page) -> bool:
        selectors = [
            ".zone:not(.disabled):not(.sold-out)",
            "area:not([class*='disabled'])",
            ".seat-area.available",
        ]
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.click()
                    log.info("Selected first available zone")
                    await page.wait_for_load_state("networkidle", timeout=10000)
                    return True
            except Exception:
                continue
        log.error("No available zones found")
        return False

    async def set_ticket_count(self, page: Page) -> bool:
        count = self.settings.ticket.num_tickets
        log.info(f"Setting ticket count to {count}")

        # Try dropdown/select first
        try:
            sel_el = await page.query_selector("select[name*='qty'], select#quantity, select.ticket-qty")
            if sel_el:
                await sel_el.select_option(str(count))
                log.info(f"Set quantity via dropdown: {count}")
                return True
        except Exception:
            pass

        # Try +/- buttons
        try:
            minus = await page.query_selector(".qty-minus, .btn-minus, [data-action='decrease']")
            plus = await page.query_selector(".qty-plus, .btn-plus, [data-action='increase']")
            qty_input = await page.query_selector("input[name*='qty'], input.quantity, input#qty")
            if qty_input and plus:
                current = int(await qty_input.get_attribute("value") or "1")
                diff = count - current
                for _ in range(abs(diff)):
                    if diff > 0:
                        await plus.click()
                    elif diff < 0 and minus:
                        await minus.click()
                    await asyncio.sleep(0.2)
                log.info(f"Set quantity via buttons: {count}")
                return True
        except Exception:
            pass

        log.warning("Could not set ticket count — proceeding with default")
        return False

    async def select_specific_seats(self, page: Page) -> bool:
        preferred = self.settings.ticket.preferred_seats
        if not preferred:
            return await self._select_best_available(page)

        selected = 0
        for seat in preferred:
            selectors = [
                f".seat[data-seat='{seat}']:not(.taken):not(.reserved)",
                f"[id='seat-{seat}']:not(.unavailable)",
                f".seat-{seat}:not(.sold)",
            ]
            for sel in selectors:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        await el.click()
                        log.info(f"Selected seat: {seat}")
                        selected += 1
                        await asyncio.sleep(0.3)
                        break
                except Exception:
                    continue

        if selected == 0:
            log.warning("Preferred seats unavailable, falling back to best available")
            return await self._select_best_available(page)

        return selected == self.settings.ticket.num_tickets

    async def _select_best_available(self, page: Page) -> bool:
        count = self.settings.ticket.num_tickets
        log.info(f"Selecting {count} best available seats")
        selected = 0

        available_seats = await page.query_selector_all(
            ".seat.available:not(.taken):not(.reserved), "
            ".seat-btn:not(.sold):not(.unavailable)"
        )

        if not available_seats:
            log.error("No available seats found on page")
            return False

        log.info(f"Found {len(available_seats)} available seats")
        for seat_el in available_seats[:count]:
            try:
                await seat_el.click()
                selected += 1
                await asyncio.sleep(0.3)
            except Exception as e:
                log.warning(f"Failed to click seat: {e}")

        log.info(f"Selected {selected}/{count} seats")
        return selected == count

    async def screenshot(self, page: Page, name: str) -> None:
        try:
            path = self.settings.screenshot_dir / f"{name}.png"
            await page.screenshot(path=str(path), full_page=True)
            log.debug(f"Screenshot: {path}")
        except Exception:
            pass
