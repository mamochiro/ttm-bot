---
name: playwright
description: Playwright debugging and selector inspection for the TTM bot. Use when the user asks to inspect selectors, find correct CSS selectors on a TTM page, debug a broken booking step, run in debug mode, test a specific module, or update selectors after TTM changed their HTML. Also use for any task involving "selector not found", "element not found", or "step failed" errors.
---

# Playwright Debug & Selector Inspection — TTM Bot

## When to use this skill

- A booking step fails with "selector not found" or "element not found"
- TTM updated their website and selectors need refreshing
- User wants to test a specific module in isolation
- User wants to run with Playwright Inspector open

---

## 1. Run with Playwright Inspector

```bash
cd /Users/sarawutnawawisikul/github/ttm-bot
source venv/bin/activate
PWDEBUG=1 python main.py --verbose
```

This opens the Playwright Inspector alongside the browser. You can:
- Pause execution at any point
- Click "Pick locator" to highlight elements and get their selectors
- Step through the automation line by line

---

## 2. Find correct selectors for a broken step

### Step A — Identify which step failed

Check the latest log file:
```bash
ls -t logs/ | head -1 | xargs -I{} cat logs/{}
```
Or check the latest screenshot:
```bash
ls -t screenshots/ | head -5
```

### Step B — Open the target page manually

Run a minimal script to open the relevant page and pause:

```python
# debug_page.py  (run as: python debug_page.py)
import asyncio
from playwright.async_api import async_playwright

TARGET_URL = "PASTE_TTM_URL_HERE"

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(TARGET_URL)
        input("Browser open — inspect page, then press Enter to close")
        await browser.close()

asyncio.run(main())
```

### Step C — Inspect elements in browser DevTools

1. Right-click the element → **Inspect**
2. In DevTools Console, test selectors:
   ```js
   document.querySelector('.your-selector')          // single
   document.querySelectorAll('.your-selector').length // count
   ```
3. For Playwright-style locators:
   ```js
   // Check text content
   document.querySelector('button')?.innerText
   // Check data attributes
   document.querySelector('[data-zone]')?.dataset
   ```

### Step D — Update the selector in the right file

Refer to CLAUDE.md selector table to find the exact file/method, then edit with correct selector.

---

## 3. Selector patterns used in this project

| Pattern | Example | When TTM uses it |
|---|---|---|
| `data-*` attribute | `[data-zone='FLOOR']` | Dynamic zone/date maps |
| `:has-text()` | `button:has-text('ยืนยัน')` | Thai/English button text |
| Class chain | `.seat.available:not(.taken)` | Seat availability state |
| ID | `#btn-confirm` | Static form elements |
| `area[title*='ZONE']` | Image map zones | SVG/imagemap seating |

---

## 4. Test a single module in isolation

### Test login only

```python
# test_auth.py
import asyncio
from playwright.async_api import async_playwright
from config.settings import Settings
from modules.auth import AuthModule

async def main():
    settings = Settings()
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        ctx = await browser.new_context()
        page = await ctx.new_page()
        auth = AuthModule(settings, worker_id=0)
        ok = await auth.ensure_logged_in(page, ctx)
        print("Login:", "OK" if ok else "FAILED")
        input("Press Enter to close")
        await browser.close()

asyncio.run(main())
```

### Test seat selection only

```python
# test_seats.py
import asyncio
from playwright.async_api import async_playwright
from config.settings import Settings
from modules.auth import AuthModule
from modules.seat_selector import SeatSelectorModule

CONCERT_URL = "PASTE_TTM_CONCERT_URL_HERE"

async def main():
    settings = Settings()
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        ctx = await browser.new_context()
        page = await ctx.new_page()

        auth = AuthModule(settings, worker_id=0)
        await auth.ensure_logged_in(page, ctx)

        await page.goto(CONCERT_URL)
        selector = SeatSelectorModule(settings)
        print("Date:", await selector.select_date(page))
        print("Zone:", await selector.select_zone(page))
        await selector.set_ticket_count(page)
        print("Seats:", await selector.select_specific_seats(page))

        input("Press Enter to close")
        await browser.close()

asyncio.run(main())

```

---

## 5. Screenshot a specific page for debugging

```python
# screenshot_page.py
import asyncio
from playwright.async_api import async_playwright

URL = "PASTE_URL_HERE"

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(URL, wait_until="networkidle")
        await page.screenshot(path="screenshots/debug_inspect.png", full_page=True)
        print("Saved: screenshots/debug_inspect.png")
        await browser.close()

asyncio.run(main())
```

---

## 6. Common errors and fixes

| Error | Likely cause | Fix |
|---|---|---|
| `Timeout waiting for selector` | TTM changed HTML | Use Steps A–D above to find new selector |
| `strict mode violation` | Multiple elements matched | Make selector more specific (add parent, ID, or `:first-of-type`) |
| `Element is not visible` | Element exists but hidden | Add `:visible` or wait for network idle before querying |
| `Navigation timeout` | Slow page or queue | Increase `bot.timeout` in config |
| `Cookie load failed` | Corrupted cookie file | Delete `cookies_0.json` and re-login |
| `Captcha timeout` | Manual solve too slow | Increase `captcha.timeout` or switch to `mode: 2captcha` |

---

## 7. Queue page detection

If the bot isn't detecting the queue, open the queue page manually and run in console:

```js
// Try each selector to see which one matches the queue page
['.queue-page', '#queue-container', '.waiting-room', '.queue-position', '#queue-number']
  .forEach(s => console.log(s, !!document.querySelector(s)))
```

Then update `booking.py:151` `queue_selectors` list with the matching selector.
