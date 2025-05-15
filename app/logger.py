"""
Custom logging for better formats and ease of use.
"""

import logging
import traceback
from logging.handlers import TimedRotatingFileHandler
from app.config import settings

DEFAULT_LOGGING_TAG = "exchange_rates_service"

class AppLogger:
    """Simple logger that puts everything into a single file and rotates the files daily.
    Logging methods allow to tag entries dynamically by using the tag parameter as logger name.
    """
    _configured = False

    @classmethod
    def setup(cls, log_file=f"{DEFAULT_LOGGING_TAG}.log", level=logging.INFO):
        if cls._configured:
            return
        
        handler = TimedRotatingFileHandler(
            log_file, when="midnight", backupCount=settings.LOG_EXPIRATION_DAYS, encoding="utf-8"
        )
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        )
        handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        root_logger.addHandler(handler)
        cls._configured = True

    @staticmethod
    def info(msg, tag=DEFAULT_LOGGING_TAG, *args, **kwargs):
        logging.getLogger(tag).info(msg, *args, **kwargs)

    @staticmethod
    def debug(msg, tag=DEFAULT_LOGGING_TAG, *args, **kwargs):
        logging.getLogger(tag).debug(msg, *args, **kwargs)

    @staticmethod
    def warning(msg, tag=DEFAULT_LOGGING_TAG, *args, **kwargs):
        logging.getLogger(tag).warning(msg, *args, **kwargs)

    @staticmethod
    def error(msg, tag=DEFAULT_LOGGING_TAG, *args, **kwargs):
        logging.getLogger(tag).error(msg, *args, **kwargs)

    @staticmethod
    def exception(exc=None, msg=None, tag=DEFAULT_LOGGING_TAG, depth=settings.LOG_DEPTH, *args, **kwargs):
        """Custom exception logging that takes into account the global stacktrace depth setting."""
        if exc is None:
            exc = Exception("Unknown exception (not provided)")

        tb = traceback.format_exc(limit=depth)
        # If there's no active exception, format_exc returns 'NoneType: None'
        if tb == 'NoneType: None\n':
            tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__, limit=depth))

        msg = f"{msg}: " if msg else ""
        logging.getLogger(tag).error("%s%s\n%s", msg, exc, tb, *args, **kwargs)
