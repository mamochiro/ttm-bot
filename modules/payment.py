import asyncio
from playwright.async_api import Page
from config.settings import Settings
from utils.logger import get_logger

log = get_logger(__name__)


class PaymentModule:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def fill_buyer_info(self, page: Page) -> bool:
        b = self.settings.buyer
        log.info("Filling buyer information")

        field_map = {
            "first_name": [
                "input[name='fname'], input[name='first_name'], #fname, #firstName",
                b.first_name,
            ],
            "last_name": [
                "input[name='lname'], input[name='last_name'], #lname, #lastName",
                b.last_name,
            ],
            "email": [
                "input[name='email'], input[type='email'], #email",
                b.email,
            ],
            "phone": [
                "input[name='phone'], input[name='mobile'], input[type='tel'], #phone",
                b.phone,
            ],
            "id_card": [
                "input[name='idcard'], input[name='id_card'], input[name='citizen_id'], #idcard",
                b.id_card,
            ],
        }

        all_ok = True
        for field_name, (selector, value) in field_map.items():
            if not value:
                log.debug(f"Skipping empty field: {field_name}")
                continue
            try:
                el = await page.wait_for_selector(selector, timeout=5000)
                await el.triple_click()
                await el.type(value, delay=50)
                log.debug(f"Filled {field_name}")
            except Exception:
                log.warning(f"Could not fill {field_name} — selector: {selector}")
                all_ok = False

        return all_ok

    async def select_payment_method(self, page: Page, method: str = "") -> bool:
        log.info(f"Selecting payment method: {method or 'default'}")

        # If a specific method requested, try to find and click it
        if method:
            selectors = [
                f"input[value='{method}']",
                f"[data-payment='{method}']",
                f".payment-method:has-text('{method}')",
                f"label:has-text('{method}')",
            ]
            for sel in selectors:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        await el.click()
                        log.info(f"Selected payment: {method}")
                        return True
                except Exception:
                    continue

        # Fall back to first available payment option
        try:
            first = await page.query_selector(
                "input[name='payment']:not(:disabled), "
                ".payment-option:not(.disabled):first-of-type"
            )
            if first:
                await first.click()
                log.info("Selected first available payment method")
                return True
        except Exception as e:
            log.error(f"Could not select payment method: {e}")

        return False

    async def confirm_order(self, page: Page) -> bool:
        log.info("Confirming order...")
        selectors = [
            "button:has-text('ยืนยัน'), button:has-text('Confirm'), button:has-text('ชำระเงิน')",
            "input[type='submit'][value*='ยืนยัน']",
            ".btn-confirm, .btn-payment, #btn-confirm",
        ]
        for sel in selectors:
            try:
                btn = await page.wait_for_selector(sel, timeout=5000)
                await btn.click()
                log.info("Order confirm clicked")
                return True
            except Exception:
                continue

        log.error("Could not find confirm/payment button")
        return False

    async def wait_for_payment_complete(self, page: Page, timeout_ms: int = 120000) -> bool:
        log.info("Waiting for payment completion...")
        success_indicators = [
            ".booking-success, .order-success, .payment-complete",
            "h1:has-text('สำเร็จ'), h1:has-text('Success'), h2:has-text('Thank you')",
            "[class*='success']:has-text('บัตร'), [class*='success']:has-text('ticket')",
        ]
        try:
            await page.wait_for_selector(
                ", ".join(success_indicators),
                timeout=timeout_ms,
            )
            log.info("Payment successful!")
            return True
        except Exception:
            log.warning("Payment success indicator not found within timeout")
            return False

    async def screenshot(self, page: Page, name: str) -> None:
        try:
            path = self.settings.screenshot_dir / f"{name}.png"
            await page.screenshot(path=str(path), full_page=True)
            log.debug(f"Screenshot: {path}")
        except Exception:
            pass
