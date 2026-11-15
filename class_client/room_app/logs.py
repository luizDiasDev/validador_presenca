import logging
import sys
from logging.handlers import RotatingFileHandler

from .config import DEFAULT_CONFIG_PATH

LOG_PATH = DEFAULT_CONFIG_PATH.with_name("sala.log")


def configure_logging(path=LOG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    def log_uncaught(exc_type, exc_value, exc_traceback):
        logging.getLogger("adsum").critical("Erro não tratado", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = log_uncaught
