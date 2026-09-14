"""Logging configuration."""
import logging
import os
from pathlib import Path

LOG_DIR = Path(os.environ.get('ANDROID_PRIVATE', '.')) / 'data' / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logger(name: str, level=logging.DEBUG) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(level)

    fmt = logging.Formatter(
        '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )

    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    try:
        fh = logging.FileHandler(LOG_DIR / 'demontalk.log')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except IOError:
        pass

    return logger
