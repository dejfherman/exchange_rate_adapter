"""
All about connecting to remote API to fetch exchange rates and caching them in Redis.
"""

import httpx
import json
from datetime import date
import redis.asyncio as redis
from app.config import settings
from app.logger import AppLogger as log

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
FCA_CACHE_KEY = "fca_rates_EUR"

class ConversionDataException(Exception):
    pass


async def get_freecurrencyapi_rate(currency: str, rate_date: date) -> float:
    """
    Fetches the conversion rate of the supplied currency to EUR from FreecurrencyAPI and
    caches results in Redis based on global settings.

    Only accepts date as a param, since FCA stores exchange rates at 1-day granularity.
    """
    date_str = str(rate_date)
    redis_key = f"{FCA_CACHE_KEY}:{date_str}"

    # check cache
    async with redis_client.pipeline() as pipe:
        pipe.hget(redis_key, currency)
        pipe.exists(redis_key)
        cached_rate, hash_exists = await pipe.execute()

    if cached_rate is not None:
        return float(cached_rate)
    elif hash_exists:
        # rates for the day are cached, but the currency requested is not there
        raise ConversionDataException("Unsupported exchange rate conversion")

    # fetch a collection of rates from API
    url = f'{settings.EXCHANGE_API_URL}/historical'
    params = {
        "apikey": settings.EXCHANGE_API_KEY,
        "base_currency": "EUR",
        "date": date_str,
    }

    log.info(msg=f"Fetching rates from {url}. Payload: \n{params}", tag=__name__)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        log.info(
            msg=f"Received response from {response.request.method} {response.request.url}. "
                f"Status {response.status_code} Payload: \n{response.text[:512]}",
            tag=__name__
        )
        response.raise_for_status()
        data = response.json()

    # process response payload
    try:
        return_date, fca_rates = next(iter(data["data"].items()))
    except (KeyError, StopIteration):
        raise ConversionDataException(
            f'Unknown format in remote API response: expected {{"data": {{<date>: {{<currency>: <rate>}}}}}}, '
            f'got {json.dumps(data)}'
        )

    # cache result
    async with redis_client.pipeline() as pipeline:
        pipeline.hset(redis_key, mapping=fca_rates)
        pipeline.expire(redis_key, settings.CACHE_TTL)
        await pipeline.execute()

    try:
        return fca_rates[currency]
    except KeyError:
        raise ConversionDataException("Unsupported exchange rate conversion")
