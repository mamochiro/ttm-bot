import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import colorlog
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False


def setup_logging(log_dir: Optional[Path] = None, level: int = logging.INFO) -> None:
    handlers = []

    if HAS_COLOR:
        console = colorlog.StreamHandler(sys.stdout)
        console.setFormatter(colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s [%(levelname)s]%(reset)s %(name)s - %(message)s",
            datefmt="%H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        ))
    else:
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%H:%M:%S",
        ))
    handlers.append(console)

    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"ttm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
        ))
        handlers.append(file_handler)

    logging.basicConfig(level=level, handlers=handlers)
    logging.getLogger("playwright").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
