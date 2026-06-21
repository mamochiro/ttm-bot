# TTM Concert Ticket Bot

Playwright-based automation bot for Thai Ticket Major concert ticket booking.

> **Note:** This tool is for personal use only. Using automation tools may violate Thai Ticket Major's Terms of Service. Use responsibly and at your own risk.

## Project Structure

```
ttm-bot/
├── config/
│   ├── __init__.py
│   └── settings.py          # Config loader (.env + YAML)
├── modules/
│   ├── auth.py              # Login & session/cookie management
│   ├── booking.py           # Main booking flow orchestrator
│   ├── seat_selector.py     # Date/zone/seat selection
│   └── payment.py           # Buyer info & payment handling
├── utils/
│   ├── logger.py            # Colored console + file logging
│   ├── proxy.py             # Proxy rotation
│   └── captcha.py           # Manual / 2captcha handler
├── screenshots/             # Auto-saved screenshots
├── logs/                    # Session log files
├── main.py                  # Entry point
├── requirements.txt
├── .env.example
└── config.yaml.example
```

## Installation

```bash
# 1. Clone and enter the project
git clone <repo> ttm-bot && cd ttm-bot

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install chromium

# 5. Copy and configure
cp .env.example .env
# Edit .env with your credentials and preferences
```

## Configuration

### Option A — `.env` file (quickest)

```bash
TTM_USERNAME=your_email@example.com
TTM_PASSWORD=your_password
CONCERT_URL=https://www.thaiticketmajor.com/concert/your-concert
NUM_TICKETS=2
PREFERRED_ZONES=FLOOR,VIP,A
HEADLESS=false
```

### Option B — `config.yaml` (full control)

```bash
cp config.yaml.example config.yaml
# Edit config.yaml
```

## Usage

```bash
# Basic run (uses .env)
python main.py

# With YAML config
python main.py -c config.yaml

# Override from CLI
python main.py --url https://www.thaiticketmajor.com/concert/foo --tickets 2 --zones FLOOR,VIP

# Run headless
python main.py --headless

# 3 parallel workers (useful for high-demand concerts)
python main.py --workers 3

# Verbose logging
python main.py --verbose
```

## Captcha Handling

| Mode | How it works |
|------|--------------|
| `manual` (default) | Bot pauses and waits up to 120s for you to solve the captcha in the open browser window |
| `2captcha` | Set `CAPTCHA_API_KEY` in `.env` — solved automatically via 2captcha.com API |

## Proxy Support

Create `proxy.txt` with one proxy per line:

```
http://user:pass@host:port
http://host:port
```

Then set `PROXY_LIST=true` in `.env` or `proxy.enabled: true` in `config.yaml`.

## Notifications

- **Sound alert**: Plays a system sound on booking success (macOS: `afplay`, Linux: `paplay`)
- **Webhook**: Set `WEBHOOK_URL` to receive a POST request on success/failure

## Debugging

All screenshots are saved to `screenshots/` with step names and timestamps.
Logs are saved to `logs/ttm_YYYYMMDD_HHMMSS.log`.

### Common issues

| Problem | Fix |
|---------|-----|
| Selectors not matching | TTM may have updated their HTML — inspect the page and update selectors in the relevant module |
| Login fails | Check credentials; try logging in manually first and saving cookies |
| Queue never ends | Increase `max_retries` and `check_interval` in config |
| Seats not found | Verify zone names match exactly what TTM shows; inspect `.seat` element classes |

## Selector Reference

The bot uses CSS selectors that may need updating if TTM changes their frontend. Key files:

- Login form: `modules/auth.py` — `TTM_LOGIN_URL` + input selectors
- Date/zone/seat: `modules/seat_selector.py`
- Checkout buttons: `modules/booking.py` → `_proceed_to_checkout`
- Buyer form fields: `modules/payment.py` → `fill_buyer_info`
