import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import List, Optional

load_dotenv()

BASE_DIR = Path(__file__).parent.parent


def _int_env(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


@dataclass
class CredentialsConfig:
    username: str = ""
    password: str = ""


@dataclass
class ConcertConfig:
    url: str = ""
    name: str = ""


@dataclass
class TicketConfig:
    num_tickets: int = 2
    preferred_dates: List[str] = field(default_factory=list)
    preferred_zones: List[str] = field(default_factory=list)
    preferred_seats: List[str] = field(default_factory=list)


@dataclass
class BuyerConfig:
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    id_card: str = ""


@dataclass
class BotConfig:
    headless: bool = False
    check_interval: int = 3
    max_retries: int = 5
    retry_delay: int = 2
    timeout: int = 30000
    screenshot_on_error: bool = True
    screenshot_on_success: bool = True


@dataclass
class ProxyConfig:
    enabled: bool = False
    file: str = "proxy.txt"
    rotate_on_error: bool = True


@dataclass
class CaptchaConfig:
    mode: str = "manual"
    api_key: str = ""
    timeout: int = 120


@dataclass
class NotificationConfig:
    webhook_url: str = ""
    sound: bool = True


class Settings:
    def __init__(self, config_path: Optional[str] = None):
        self.credentials = CredentialsConfig()
        self.concert = ConcertConfig()
        self.ticket = TicketConfig()
        self.buyer = BuyerConfig()
        self.bot = BotConfig()
        self.proxy = ProxyConfig()
        self.captcha = CaptchaConfig()
        self.notifications = NotificationConfig()
        self.workers: int = 1

        self._load_env()
        if config_path:
            self._load_yaml(config_path)

    def _load_env(self):
        self.credentials.username = os.getenv("TTM_USERNAME", "")
        self.credentials.password = os.getenv("TTM_PASSWORD", "")

        self.concert.url = os.getenv("CONCERT_URL", "")
        self.concert.name = os.getenv("CONCERT_NAME", "")

        self.ticket.num_tickets = _int_env("NUM_TICKETS", 2)
        dates_env = os.getenv("PREFERRED_DATES", "")
        if dates_env:
            self.ticket.preferred_dates = [d.strip() for d in dates_env.split(",")]
        zones_env = os.getenv("PREFERRED_ZONES", "")
        if zones_env:
            self.ticket.preferred_zones = [z.strip() for z in zones_env.split(",")]

        self.buyer.first_name = os.getenv("BUYER_FIRST_NAME", "")
        self.buyer.last_name = os.getenv("BUYER_LAST_NAME", "")
        self.buyer.email = os.getenv("BUYER_EMAIL", "")
        self.buyer.phone = os.getenv("BUYER_PHONE", "")
        self.buyer.id_card = os.getenv("BUYER_ID_CARD", "")

        self.bot.headless = os.getenv("HEADLESS", "false").lower() == "true"
        self.bot.check_interval = _int_env("CHECK_INTERVAL", 3)
        self.bot.max_retries = _int_env("MAX_RETRIES", 5)

        self.captcha.api_key = os.getenv("CAPTCHA_API_KEY", "")
        if self.captcha.api_key:
            self.captcha.mode = "2captcha"

        self.notifications.webhook_url = os.getenv("WEBHOOK_URL", "")
        sound_env = os.getenv("NOTIFICATION_SOUND", "true")
        self.notifications.sound = sound_env.lower() == "true"

        proxy_env = os.getenv("PROXY_LIST", "")
        if proxy_env:
            self.proxy.enabled = True

    def _load_yaml(self, config_path: str):
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        if not data:
            return

        if creds := data.get("credentials"):
            self.credentials.username = creds.get("username", self.credentials.username)
            self.credentials.password = creds.get("password", self.credentials.password)

        if concert := data.get("concert"):
            self.concert.url = concert.get("url", self.concert.url)
            self.concert.name = concert.get("name", self.concert.name)

        if ticket := data.get("ticket"):
            self.ticket.num_tickets = ticket.get("num_tickets", self.ticket.num_tickets)
            self.ticket.preferred_dates = ticket.get("preferred_dates", self.ticket.preferred_dates)
            self.ticket.preferred_zones = ticket.get("preferred_zones", self.ticket.preferred_zones)
            self.ticket.preferred_seats = ticket.get("preferred_seats", self.ticket.preferred_seats)

        if buyer := data.get("buyer"):
            self.buyer.first_name = buyer.get("first_name", self.buyer.first_name)
            self.buyer.last_name = buyer.get("last_name", self.buyer.last_name)
            self.buyer.email = buyer.get("email", self.buyer.email)
            self.buyer.phone = buyer.get("phone", self.buyer.phone)
            self.buyer.id_card = buyer.get("id_card", self.buyer.id_card)

        if bot := data.get("bot"):
            self.bot.headless = bot.get("headless", self.bot.headless)
            self.bot.check_interval = bot.get("check_interval", self.bot.check_interval)
            self.bot.max_retries = bot.get("max_retries", self.bot.max_retries)
            self.bot.retry_delay = bot.get("retry_delay", self.bot.retry_delay)
            self.bot.timeout = bot.get("timeout", self.bot.timeout)
            self.bot.screenshot_on_error = bot.get("screenshot_on_error", self.bot.screenshot_on_error)
            self.bot.screenshot_on_success = bot.get("screenshot_on_success", self.bot.screenshot_on_success)

        if proxy := data.get("proxy"):
            self.proxy.enabled = proxy.get("enabled", self.proxy.enabled)
            self.proxy.file = proxy.get("file", self.proxy.file)
            self.proxy.rotate_on_error = proxy.get("rotate_on_error", self.proxy.rotate_on_error)

        if captcha := data.get("captcha"):
            self.captcha.mode = captcha.get("mode", self.captcha.mode)
            self.captcha.api_key = captcha.get("api_key", self.captcha.api_key)
            self.captcha.timeout = captcha.get("timeout", self.captcha.timeout)

        if notif := data.get("notifications"):
            self.notifications.webhook_url = notif.get("webhook_url", self.notifications.webhook_url)
            self.notifications.sound = notif.get("sound", self.notifications.sound)

        self.workers = data.get("workers", self.workers)

    def validate(self):
        errors = []
        if not self.credentials.username:
            errors.append("TTM_USERNAME is required")
        if not self.credentials.password:
            errors.append("TTM_PASSWORD is required")
        if not self.concert.url and not self.concert.name:
            errors.append("Either CONCERT_URL or CONCERT_NAME is required")
        if self.ticket.num_tickets < 1:
            errors.append("NUM_TICKETS must be >= 1")
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

    @property
    def screenshot_dir(self) -> Path:
        d = BASE_DIR / "screenshots"
        d.mkdir(exist_ok=True)
        return d

    @property
    def log_dir(self) -> Path:
        d = BASE_DIR / "logs"
        d.mkdir(exist_ok=True)
        return d

    def cookies_file(self, worker_id: int = 0) -> Path:
        return BASE_DIR / f"cookies_{worker_id}.json"
