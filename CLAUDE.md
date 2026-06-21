# TTM Concert Ticket Bot

Playwright-based async Python bot for automating concert ticket purchases on Thai Ticket Major (thaiticketmajor.com).

## Stack

- **Python 3.11+** with `asyncio`
- **Playwright** (async API) for browser automation
- **pydantic/dataclasses** for config, **pyyaml + python-dotenv** for settings

## Project Layout

```
config/settings.py      # Loads .env + config.yaml, validates required fields
modules/auth.py         # Login, cookie save/load per worker_id
modules/booking.py      # Orchestrator: auth → queue → date → zone → seat → checkout → payment
modules/seat_selector.py# Date / zone / seat selection (priority list + best-available fallback)
modules/payment.py      # Buyer info form fill, payment method, confirm, await success
utils/captcha.py        # Manual (waits for human) or 2captcha (async polling via aiohttp)
utils/proxy.py          # Round-robin proxy rotation with per-proxy failure tracking
utils/logger.py         # Colored console log + timestamped file log
main.py                 # Entry point — single or multi-worker via asyncio.gather
```

## Run

```bash
source venv/bin/activate
python main.py                          # uses .env
python main.py -c config.yaml           # YAML config
python main.py --url <URL> --tickets 2 --zones FLOOR,VIP
python main.py --workers 3 --headless
python main.py --verbose                # debug logging
```

## Debug with Playwright Inspector

```bash
PWDEBUG=1 python main.py               # opens Playwright Inspector
```

## Key Conventions

- All Playwright calls use **async API** (`playwright.async_api`). Never import sync version.
- `worker_id` flows through `AuthModule` → `cookies_{worker_id}.json` to avoid multi-worker race conditions.
- `BookingModule._screenshot(page, name, is_error=True/False)` respects `bot.screenshot_on_error` and `bot.screenshot_on_success` flags.
- `_handle_captcha()` is called at 3 points in the booking flow (post-login nav, post-queue, pre-confirm).
- CSS selectors are **placeholder guesses** — TTM may change their HTML. Use `/playwright` skill to inspect and update them.
- Retry logic uses exponential backoff: `retry_delay * 2^(retry_num - 1)`.

## Selector Files to Update After TTM HTML Changes

| What broke | File | Method |
|---|---|---|
| Login form | `modules/auth.py:35-43` | `login()` |
| Date picker | `modules/seat_selector.py:21` | `select_date()` |
| Zone map/list | `modules/seat_selector.py:63-68` | `select_zone()` |
| Seat grid | `modules/seat_selector.py:146-149` | `select_specific_seats()` |
| Checkout button | `modules/booking.py:213-217` | `_proceed_to_checkout()` |
| Buyer info fields | `modules/payment.py:18-37` | `fill_buyer_info()` |
| Confirm button | `modules/payment.py:94-97` | `confirm_order()` |
| Success indicator | `modules/payment.py:113-116` | `wait_for_payment_complete()` |

## Config

Required env vars: `TTM_USERNAME`, `TTM_PASSWORD`, and either `CONCERT_URL` or `CONCERT_NAME`.
See `.env.example` and `config.yaml.example` for all options.

## Screenshots & Logs

- `screenshots/` — auto-saved at key steps and on error
- `logs/ttm_YYYYMMDD_HHMMSS.log` — full session log
