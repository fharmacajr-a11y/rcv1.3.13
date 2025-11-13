import logging
import os

_LEVEL = os.getenv("RC_LOG_LEVEL", "INFO").upper()
_LEVEL_VAL = getattr(logging, _LEVEL, logging.INFO)

logging.basicConfig(level=_LEVEL_VAL, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


def get_logger(name: str = __name__):
    return logging.getLogger(name)
