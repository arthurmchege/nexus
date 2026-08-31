import logging
import sys


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("nexus")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger


logger: logging.Logger = setup_logging()
