import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # формат
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # лог в файл
    file_handler = RotatingFileHandler(
        f"{LOG_DIR}/app.log",
        maxBytes=5_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # лог в консоль (docker)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
