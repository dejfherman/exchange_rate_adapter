"""
Global settings loaded from .env file
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    EXCHANGE_API_URL = os.getenv("FREECURRENCYAPI_URL")
    EXCHANGE_API_KEY = os.getenv("FREECURRENCYAPI_KEY")
    REDIS_URL = os.getenv("REDIS_URL")
    CACHE_TTL = os.getenv("CACHE_TTL_SECONDS")
    REQUESTS_WS_URL = os.getenv("REQUESTS_WS_URL")
    LOG_DEPTH = os.getenv("LOG_EXCEPTION_FRAMES_LIMIT")
    LOG_EXPIRATION_DAYS = os.getenv("LOG_EXPIRATION_DAYS")
    RETRY_MESSAGE_TTL = os.getenv("RETRY_MESSAGE_TTL")

settings = Settings()
