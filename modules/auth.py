import json
import asyncio
from pathlib import Path
from typing import Optional
from playwright.async_api import Page, BrowserContext
from config.settings import Settings
from utils.logger import get_logger

log = get_logger(__name__)

TTM_BASE_URL = "https://www.thaiticketmajor.com"
TTM_LOGIN_URL = f"{TTM_BASE_URL}/member/login.php"


class AuthModule:
    def __init__(self, settings: Settings, worker_id: int = 0):
        self.settings = settings
        self.worker_id = worker_id
        self._logged_in = False

    async def ensure_logged_in(self, page: Page, context: BrowserContext) -> bool:
        if await self._load_cookies(context):
            if await self._verify_session(page):
                log.info("Restored existing session from cookies")
                self._logged_in = True
                return True
            log.info("Saved cookies expired, logging in fresh")

        return await self.login(page, context)

    async def login(self, page: Page, context: BrowserContext) -> bool:
        log.info(f"Logging in as {self.settings.credentials.username}")
        await page.goto(TTM_LOGIN_URL, wait_until="domcontentloaded")

        try:
            await page.wait_for_selector("#email, input[name='email'], input[type='email']", timeout=10000)
        except Exception:
            log.error("Login page did not load — selector not found")
            await self._screenshot(page, "login_page_missing")
            return False

        await page.fill("#email, input[name='email'], input[type='email']", self.settings.credentials.username)
        await page.fill("#password, input[name='password'], input[type='password']", self.settings.credentials.password)
        await page.click("button[type='submit'], input[type='submit'], .btn-login")

        try:
            await page.wait_for_url(lambda url: "login" not in url, timeout=15000)
        except Exception:
            error_el = await page.query_selector(".error-msg, .alert-danger, .login-error")
            if error_el:
                msg = await error_el.inner_text()
                log.error(f"Login failed: {msg.strip()}")
            else:
                log.error("Login failed: still on login page after submit")
            await self._screenshot(page, "login_failed")
            return False

        await self._save_cookies(context)
        self._logged_in = True
        log.info("Login successful")
        return True

    async def _verify_session(self, page: Page) -> bool:
        try:
            await page.goto(f"{TTM_BASE_URL}/member/", wait_until="domcontentloaded", timeout=15000)
            url = page.url
            return "login" not in url and "member" in url
        except Exception:
            return False

    async def _save_cookies(self, context: BrowserContext) -> None:
        cookies = await context.cookies()
        path = self.settings.cookies_file(self.worker_id)
        with open(path, "w") as f:
            json.dump(cookies, f, indent=2)
        log.debug(f"Saved {len(cookies)} cookies to {path}")

    async def _load_cookies(self, context: BrowserContext) -> bool:
        path = self.settings.cookies_file(self.worker_id)
        if not path.exists():
            return False
        try:
            with open(path) as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
            log.debug(f"Loaded {len(cookies)} cookies")
            return True
        except Exception as e:
            log.warning(f"Failed to load cookies: {e}")
            return False

    async def _screenshot(self, page: Page, name: str) -> None:
        try:
            path = self.settings.screenshot_dir / f"{name}.png"
            await page.screenshot(path=str(path))
            log.debug(f"Screenshot saved: {path}")
        except Exception:
            pass

    @property
    def is_logged_in(self) -> bool:
        return self._logged_in
