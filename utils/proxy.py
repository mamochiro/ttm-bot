import random
from pathlib import Path
from typing import List, Optional
from utils.logger import get_logger

log = get_logger(__name__)


class ProxyManager:
    def __init__(self, proxy_file: str = "proxy.txt", proxies: Optional[List[str]] = None):
        self._proxies: List[str] = []
        self._current_index = 0
        self._failed: set = set()

        if proxies:
            self._proxies = [p.strip() for p in proxies if p.strip()]
        elif Path(proxy_file).exists():
            self._load_file(proxy_file)

        if self._proxies:
            log.info(f"Loaded {len(self._proxies)} proxies")

    def _load_file(self, path: str) -> None:
        with open(path) as f:
            self._proxies = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    def get_next(self) -> Optional[dict]:
        available = [p for p in self._proxies if p not in self._failed]
        if not available:
            if self._failed:
                log.warning("All proxies have failed, resetting failed list")
                self._failed.clear()
                available = list(self._proxies)
            else:
                return None

        proxy_str = available[self._current_index % len(available)]
        self._current_index = (self._current_index + 1) % len(available)
        return self._parse(proxy_str)

    def get_random(self) -> Optional[dict]:
        available = [p for p in self._proxies if p not in self._failed]
        if not available:
            return None
        return self._parse(random.choice(available))

    def mark_failed(self, proxy: dict) -> None:
        server = proxy.get("server", "")
        self._failed.add(server)
        log.warning(f"Proxy marked as failed: {server}")

    @staticmethod
    def _parse(proxy_str: str) -> dict:
        # Supports: http://user:pass@host:port or http://host:port
        result = {"server": proxy_str}
        if "@" in proxy_str:
            creds_part, host_part = proxy_str.rsplit("@", 1)
            scheme_creds = creds_part.split("//", 1)
            creds = scheme_creds[-1]
            username, password = creds.split(":", 1)
            result["username"] = username
            result["password"] = password
            scheme = scheme_creds[0].rstrip(":") if "//" in creds_part else "http"
            result["server"] = f"{scheme}://{host_part}"
        return result

    @property
    def has_proxies(self) -> bool:
        return len(self._proxies) > 0
