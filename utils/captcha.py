import asyncio
import time
from typing import Optional
from utils.logger import get_logger

log = get_logger(__name__)


class CaptchaHandler:
    def __init__(self, mode: str = "manual", api_key: str = "", timeout: int = 120):
        self.mode = mode
        self.api_key = api_key
        self.timeout = timeout

        if mode == "2captcha" and not api_key:
            log.warning("2captcha mode set but no API key provided, falling back to manual")
            self.mode = "manual"

    async def solve(self, page, site_key: str = "", page_url: str = "") -> Optional[str]:
        if self.mode == "2captcha":
            return await self._solve_2captcha(site_key, page_url)
        return await self._solve_manual(page)

    async def _solve_manual(self, page) -> Optional[str]:
        log.warning("=" * 60)
        log.warning("CAPTCHA DETECTED — Please solve it in the browser window.")
        log.warning(f"You have {self.timeout} seconds.")
        log.warning("=" * 60)

        deadline = time.time() + self.timeout
        while time.time() < deadline:
            # Check if captcha is gone (page moved on)
            try:
                captcha_visible = await page.is_visible(
                    "iframe[src*='recaptcha'], .g-recaptcha, #captcha",
                    timeout=1000,
                )
                if not captcha_visible:
                    log.info("Captcha appears to be solved")
                    return "manual_solved"
            except Exception:
                return "manual_solved"
            await asyncio.sleep(2)

        log.error("Captcha timeout — manual solve not completed in time")
        return None

    async def _solve_2captcha(self, site_key: str, page_url: str) -> Optional[str]:
        try:
            import aiohttp

            log.info("Submitting captcha to 2captcha...")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://2captcha.com/in.php",
                    data={
                        "key": self.api_key,
                        "method": "userrecaptcha",
                        "googlekey": site_key,
                        "pageurl": page_url,
                        "json": 1,
                    },
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    result = await resp.json(content_type=None)

            if result.get("status") != 1:
                log.error(f"2captcha submit failed: {result}")
                return None

            task_id = result["request"]
            log.info(f"2captcha task submitted: {task_id}, polling for result...")

            async with aiohttp.ClientSession() as session:
                for _ in range(30):
                    await asyncio.sleep(5)
                    async with session.get(
                        "http://2captcha.com/res.php",
                        params={"key": self.api_key, "action": "get", "id": task_id, "json": 1},
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as poll_resp:
                        poll_result = await poll_resp.json(content_type=None)

                    if poll_result.get("status") == 1:
                        log.info("2captcha solved successfully")
                        return poll_result["request"]
                    if poll_result.get("request") != "CAPCHA_NOT_READY":
                        log.error(f"2captcha error: {poll_result}")
                        return None

            log.error("2captcha timed out")
            return None

        except Exception as e:
            log.error(f"2captcha error: {e}")
            return None

    async def inject_recaptcha_token(self, page, token: str) -> None:
        await page.evaluate(
            """(token) => {
                const el = document.getElementById('g-recaptcha-response');
                if (el) el.innerHTML = token;
                if (typeof ___grecaptcha_cfg !== 'undefined') {
                    Object.entries(___grecaptcha_cfg.clients).forEach(([k, v]) => {
                        if (v.callback) v.callback(token);
                    });
                }
            }""",
            token,
        )
